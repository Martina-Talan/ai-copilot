from uuid import uuid5, NAMESPACE_URL
import logging
import re
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable, Tuple, Union

from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings

logger = logging.getLogger(__name__)

# =============================================================================
# Regex Utilities
# =============================================================================

HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*([^\n#].*?)\s*$")
LEGAL_SPLIT_RE = re.compile(r"(?=§\s*\w+)")
LEGAL_HEAD_RE = re.compile(r"§\s*([\wIVXLC]+)")
SPACE_RE = re.compile(r"[ \t]+")
BLANKS_RE = re.compile(r"\n{3,}")
BOILERPLATE_WORDS_RE = re.compile(r"^(?:\s*(?:Confidential|Draft|\d+)\s*)$", re.IGNORECASE | re.MULTILINE)

# =============================================================================
# Token Counter
# =============================================================================

try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(s: str) -> int:
        return len(_ENCODER.encode(s))
except ImportError:
    _ENCODER = None

    def _count_tokens(s: str) -> int:
        words = len(s.split())
        chars = len(s)
        return max(1, int((words * 1.3) + (chars * 0.2)))

# =============================================================================
# Helpers
# =============================================================================

def _mk_id(*parts: Optional[Union[str, int]]) -> str:
    """Generate deterministic UUIDv5-based ID (16 hex chars)."""
    norm = [" ".join(str(p).split()) if p is not None else "" for p in parts]
    return uuid5(NAMESPACE_URL, "|".join(norm)).hex[:16]

# =============================================================================
# Configuration
# =============================================================================

@dataclass
class SplitConfig:
    """Settings for chunking behavior."""
    max_tokens_single: int = 512
    rec_chunk_size: int = 800
    rec_overlap: int = 100
    semantic_breakpoint: str = "percentile"
    semantic_threshold_amount: int = 95
    min_chars_per_chunk: int = 80
    max_chunks: Optional[int] = None
    rec_separators: tuple = ("\n\n", "\n", ". ", " ", "") 

# =============================================================================
# Main Class: TextSplitter
# =============================================================================

class TextSplitter:
    """
    Smart chunking engine supporting legal documents, semantic chunking,
    markdown heading parsing, and recursive fallback.
    """

    _embeddings_cache = {}

    def __init__(
        self,
        embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        legal_mode: bool = False,
        semantic_mode: bool = True,
        embeddings: Optional[OpenAIEmbeddings] = None,
        cfg: SplitConfig = SplitConfig(),
    ):
        self.legal_mode = legal_mode
        self.semantic_mode = semantic_mode
        self.cfg = cfg
        
        if embeddings:
            self.embeddings = embeddings
        elif semantic_mode:
            cache_key = embedding_model
            if cache_key not in self._embeddings_cache:
                logger.info(f"Creating new embeddings instance for {embedding_model}")
                self._embeddings_cache[cache_key] = OpenAIEmbeddings(model=embedding_model)
            self.embeddings = self._embeddings_cache[cache_key]
        else:
            self.embeddings = None
            
        logger.info("TextSplitter initialized legal=%s semantic=%s", legal_mode, semantic_mode)

    def _remove_boilerplate(self, text: str) -> str:
        """Remove boilerplate text and normalize whitespace."""
        if not text:
            return ""
            
        text = re.sub(
            r'(?mi)^([^\n:]{2,}?:)\s*\n\s*(\d{3,})\s*$',
            r'\1 \2',
            text,
        )
        text = BOILERPLATE_WORDS_RE.sub("", text)
        text = SPACE_RE.sub(" ", text)
        text = BLANKS_RE.sub("\n\n", text)
        lines = [ln.rstrip() for ln in text.split("\n")]
        return "\n".join([ln for ln in lines if ln.strip()])

    def _split_by_headings(self, text: str) -> List[Dict[str, Any]]:
        """Split text based on markdown headings."""
        sections, current = [], {"heading": "Introduction", "content": []}
        for line in text.split("\n"):
            m = HEADING_RE.match(line)
            if m:
                if current["content"]:
                    sections.append(current)
                current = {"heading": m.group(1), "content": []}
            else:
                current["content"].append(line)
        if current["content"]:
            sections.append(current)
        return sections

    def _wrap(
        self, 
        content: str, 
        document_id: str, 
        page_number: Optional[int], 
        heading: Optional[str], 
        chunk_type: str,         
        bbox: Optional[Dict[str, float]] = None,
    ) -> Document:
        """Wrap raw text into LangChain Document with metadata."""
        token_count = _count_tokens(content)
        meta: Dict[str, Any] = {
            "documentId": document_id,
            "pageNumber": page_number,
            "heading": heading,
            "chunkType": chunk_type,
            "tokenCount": token_count,
            "chunkId": _mk_id(document_id, page_number, heading, chunk_type, content[:160]),
        }
        if bbox:
            meta["bbox"] = {
                "x": float(bbox.get("x", 0.0)),
                "y": float(bbox.get("y", 0.0)),
                "width": float(bbox.get("width", 0.0)),
                "height": float(bbox.get("height", 0.0)),
                "page": int(bbox.get("page", page_number or 1)),
            }
        return Document(page_content=content, metadata=meta)

    def _recursive_split(self, content: str) -> List[str]:
        """Split content using recursive character-based strategy."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.cfg.rec_chunk_size,
            chunk_overlap=self.cfg.rec_overlap,
            separators=list(self.cfg.rec_separators),
        )
        docs = splitter.create_documents([content])
        return [d.page_content for d in docs]

    def _semantic_split(self, content: str) -> Tuple[List[str], bool]:
        """Try semantic chunking; fallback to recursive if it fails."""
        if not (self.semantic_mode and self.embeddings):
            return self._recursive_split(content), False

        try:
            sc = SemanticChunker(
                self.embeddings,
                breakpoint_threshold_type=self.cfg.semantic_breakpoint,
                breakpoint_threshold_amount=self.cfg.semantic_threshold_amount,
            )
            docs = sc.create_documents([content])
            return [d.page_content for d in docs], True
        except ImportError as e:
            logger.warning(f"SemanticChunker not available: {e}")
            return self._recursive_split(content), False
        except Exception as e:
            logger.error(f"Semantic chunking failed: {str(e)}")
            return self._recursive_split(content), False

    # =============================================================================
    # Span-Aware Chunking
    # =============================================================================

    @staticmethod
    def _union_bbox(spans: List[Dict[str, Any]], page_number: int) -> Optional[Dict[str, float]]:
        """Calculate union bounding box from multiple spans."""
        if not spans:
            return None

        valid_spans = [s for s in spans if s.get("bbox")]
        if not valid_spans:
            return None
            
        xs = [s["bbox"]["x"] for s in valid_spans]
        ys = [s["bbox"]["y"] for s in valid_spans]
        xe = [s["bbox"]["x"] + s["bbox"]["width"] for s in valid_spans]
        ye = [s["bbox"]["y"] + s["bbox"]["height"] for s in valid_spans]
        
        x = float(min(xs))
        y = float(min(ys))
        width = float(max(xe) - x)
        height = float(max(ye) - y)
        
        return {"x": x, "y": y, "width": width, "height": height, "page": page_number}

    def _chunk_by_spans(
        self,
        spans: List[Dict[str, Any]],
        document_id: str,
        page_number: int,
        heading: Optional[str] = None,
    ) -> List[Document]:
        chunks: List[Document] = []
        if not spans:
            return chunks

        cur_spans: List[Dict[str, Any]] = []
        cur_texts: List[str] = []
        cur_tokens = 0
        limit = self.cfg.rec_chunk_size
        min_chars = self.cfg.min_chars_per_chunk

        def flush():
            nonlocal cur_spans, cur_texts, cur_tokens
            if not cur_texts:
                return
            text = "\n".join(cur_texts).strip()
            if len(text) < min_chars:
                if chunks and chunks[-1].metadata.get("pageNumber") == page_number:
                    merged = chunks[-1].page_content + "\n" + text
                    if _count_tokens(merged) <= int(limit * 1.2):
                        chunks[-1].page_content = merged
                cur_spans, cur_texts, cur_tokens = [], [], 0
                return
            bbox = self._union_bbox(cur_spans, page_number)
            chunks.append(self._wrap(text, document_id, page_number, heading, "by_spans", bbox=bbox))
            cur_spans, cur_texts, cur_tokens = [], [], 0

        for s in spans:
            if not isinstance(s, dict):
                continue
            txt = (s.get("text") or "").strip()
            if not txt:
                continue
            t = _count_tokens(txt)

            if t > limit:
                flush()
                chunks.append(self._wrap(txt, document_id, page_number, heading, "by_spans", bbox=s.get("bbox")))
                continue

            if cur_tokens + t > limit:
                flush()

            cur_spans.append(s)
            cur_texts.append(txt)
            cur_tokens += t

        flush()
        return chunks

    # =============================================================================
    # Main Chunking Methods
    # =============================================================================

    def _chunk_with_metadata(
        self, 
        content: str, 
        document_id: str, 
        page_number: Optional[int], 
        heading: Optional[str], 
        chunk_type: str
    ) -> List[Document]:
        """Chunk content and wrap with metadata."""
        if _count_tokens(content) <= self.cfg.max_tokens_single:
            return [self._wrap(content, document_id, page_number, heading, chunk_type)]

        used_semantic = False
        parts: List[str]
        
        if self.semantic_mode and self.embeddings:
            parts, used_semantic = self._semantic_split(content)
            final_type = "semantic" if used_semantic else "recursive"
        else:
            parts = self._recursive_split(content)
            final_type = "recursive"

        meaningful_parts = [p for p in parts if _count_tokens(p) >= 3]

        return [
            self._wrap(p, document_id, page_number, heading, final_type)
            for p in meaningful_parts
        ]

    def split_text(
        self, 
        text: str, 
        document_id: str, 
        page_number: Optional[int] = None
    ) -> List[Document]:
        """
        Public entry: clean, split and wrap text into structured Document chunks.
        """
        cleaned_text = self._remove_boilerplate(text)
        if not cleaned_text.strip():
            return []

        # Legal document processing
        if self.legal_mode and "§" in cleaned_text:
            sections = [p.strip() for p in LEGAL_SPLIT_RE.split(cleaned_text) if p.strip()]
            chunks: List[Document] = []
            for section in sections:
                match = LEGAL_HEAD_RE.search(section)
                heading = f"§{match.group(1)}" if match else "§"
                chunks.extend(self._chunk_with_metadata(
                    section, document_id, page_number, heading, "legal"
                ))
            return chunks

        # Heading-based processing
        heading_sections = self._split_by_headings(cleaned_text)
        if len(heading_sections) > 1:
            chunks: List[Document] = []
            for section in heading_sections:
                body_text = "\n".join(section["content"]).strip()
                if body_text:
                    chunks.extend(self._chunk_with_metadata(
                        body_text, document_id, page_number, section["heading"], "hierarchical"
                    ))
            return chunks

        # Generic processing
        return self._chunk_with_metadata(cleaned_text, document_id, page_number, None, "generic")

    def split_pdf_pages_combined(
        self, 
        pages: List[Dict[str, Any]], 
        document_id: str
    ) -> List[Document]:
        """
        Combine multiple pages before chunking.
        """
        full_text = "\n".join(p.get("text", "") for p in pages if p.get("text"))
        return self.split_text(text=full_text, document_id=document_id, page_number=None)

    def split_pdf_pages_with_spans(
        self, 
        pages: List[Dict[str, Any]], 
        document_id: str
    ) -> List[Document]:
        """
        Chunk PDF pages using span-level geometry information.
        """
        all_chunks: List[Document] = []
        
        for page in pages:
            page_number = page.get("pageNumber")
            if page_number is None:
                continue
                
            try:
                page_number = int(page_number)
            except (TypeError, ValueError):
                continue
                
            spans = page.get("spans") or []
            if spans:
                page_chunks = self._chunk_by_spans(
                    spans, document_id, page_number, heading=None
                )
                all_chunks.extend(page_chunks)
            else:
                text = page.get("content") or page.get("text") or ""
                if text.strip():
                    page_chunks = self.split_text(text, document_id, page_number=page_number)
                    all_chunks.extend(page_chunks)

        if self.cfg.max_chunks and len(all_chunks) > self.cfg.max_chunks:
            return all_chunks[:self.cfg.max_chunks]
            
        return all_chunks