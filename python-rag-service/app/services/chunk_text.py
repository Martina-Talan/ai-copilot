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

COMPANY_RE = re.compile(
    r'\b[A-ZÄÖÜ][\wÄÖÜäöüß&.\- ]{1,60}\b(?:GmbH|AG|UG|KG|OHG|e\.K\.?|e\.V\.)\b', re.U)
STREET_RE = re.compile(
    r'\b[\wÄÖÜäöüß.\- ]{2,80}(?:straße|str\.|weg|platz|allee|ring|gasse)\b\s*\d+[a-zA-Z]?\b', re.I | re.U)
PLZ_CITY_RE = re.compile(
    r'\b\d{5}\b\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\- ]{2,}', re.U)

# =============================================================================
# Token Counter
# =============================================================================

try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(s: str) -> int:
        return len(_ENCODER.encode(s))
except Exception:
    _ENCODER = None

    def _count_tokens(s: str) -> int:
        return max(1, len(s) // 4)

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

# =============================================================================
# Main Class: TextSplitter
# =============================================================================

class TextSplitter:
    """
    Smart chunking engine supporting legal documents, semantic chunking,
    markdown heading parsing, and recursive fallback.
    """

    def __init__(
        self,
        embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
        legal_mode: bool = False,
        semantic_mode: bool = True,
        embeddings: Optional[OpenAIEmbeddings] = None,
        cfg: SplitConfig = SplitConfig(),
    ):
        self.legal_mode = legal_mode
        self.semantic_mode = semantic_mode
        self.cfg = cfg
        self.embeddings = embeddings or (OpenAIEmbeddings(model=embedding_model) if semantic_mode else None)
        logger.info("TextSplitter initialized legal=%s semantic=%s", legal_mode, semantic_mode)

    def _remove_boilerplate(self, text: str) -> str:
        # Zeilen mit ":" + nächste numerische Zeile zusammenführen
        text = re.sub(
            r'(?mi)^([^\n:]{2,}?:)\s*\n\s*(\d{3,})\s*$',
            r'\1 \2',
            text,
        )
        # Danach wie bisher aufräumen:
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

    def _wrap(self, content: str, document_id: str, page_number: Optional[int], heading: Optional[str], chunk_type: str) -> Document:
        """Wrap raw text into LangChain Document with metadata."""
        token_count = _count_tokens(content)
        return Document(
            page_content=content,
            metadata={
                "documentId": document_id,
                "pageNumber": page_number,
                "heading": heading,
                "chunkType": chunk_type,
                "tokenCount": token_count,
                "chunkId": _mk_id(document_id, page_number, heading, chunk_type, content[:160]),
            }
        )

    def _recursive_split(self, content: str) -> List[str]:
        """Split content using recursive character-based strategy."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.cfg.rec_chunk_size,
            chunk_overlap=self.cfg.rec_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
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
        except Exception:
            logger.exception("Semantic chunking failed, falling back to recursive")
            return self._recursive_split(content), False

    def _chunk_with_metadata(
        self, content: str, document_id: str, page_number: Optional[int], heading: Optional[str], chunk_type: str
    ) -> List[Document]:
        """Chunk content and wrap with metadata, filtering out tiny fragments."""

        if _count_tokens(content) <= self.cfg.max_tokens_single:
            return [self._wrap(content, document_id, page_number, heading, chunk_type)]

        if self.embeddings:
            parts, used_sem = self._semantic_split(content)
            final_type = "semantic" if used_sem else "recursive"
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.cfg.rec_chunk_size,
                chunk_overlap=self.cfg.rec_overlap
            )
            parts = [x.page_content for x in splitter.create_documents([content])]
            used_sem = False
            final_type = "recursive"

        meaningful_parts = [p for p in parts if _count_tokens(p) >= 3]

        return [
            self._wrap(p, document_id, page_number, heading, final_type)
            for p in meaningful_parts
        ]

    # --------------------------------------------------------------
    # Main methods
    # --------------------------------------------------------------

    def split_text(self, text: str, document_id: str, page_number: Optional[int] = None) -> List[Document]:
        """
        Public entry: clean, split and wrap text into structured Document chunks.

        Prioritizes:
        1. Legal splitting (if `§` present and legal_mode is on)
        2. Markdown-style headings
        3. Generic fallback

        Returns:
            List[Document]: Structured chunks with rich metadata.
        """
        text = self._remove_boilerplate(text)
        if not text.strip():
            return []

        if self.legal_mode and "§" in text:
            sections = [p.strip() for p in LEGAL_SPLIT_RE.split(text) if p.strip()]
            out: List[Document] = []
            for sec in sections:
                m = LEGAL_HEAD_RE.search(sec)
                heading = f"§{m.group(1)}" if m else "§"
                out.extend(self._chunk_with_metadata(sec, document_id, page_number, heading, "legal"))
            return out

        hs = self._split_by_headings(text)
        if len(hs) > 1:
            out: List[Document] = []
            for s in hs:
                body = "\n".join(s["content"]).strip()
                if not body:
                    continue
                out.extend(self._chunk_with_metadata(body, document_id, page_number, s["heading"], "hierarchical"))
            return out

        return self._chunk_with_metadata(text, document_id, page_number, None, "generic")

    def split_pdf_pages_combined(self, pages: List[Dict[str, Any]], document_id: str) -> List[Document]:
        """
        New method: combine multiple pages before chunking.

        Args:
            pages: List of {"text": ..., "pageNumber": ...} from PDFProcessor.
            document_id: ID of the document.

        Returns:
            List[Document]: Chunked and wrapped LangChain documents.
        """
        full_text = "\n".join(p["text"] for p in pages if p.get("text"))
        return self.split_text(text=full_text, document_id=document_id, page_number=None)
