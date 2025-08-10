from dataclasses import dataclass
import hashlib, re, tiktoken
from typing import Optional, List, Dict, Any
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
import logging

logger = logging.getLogger(__name__)

HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*([^\n#].*?)\s*$")
LEGAL_SPLIT_RE = re.compile(r"(?=§\s*\w+)")
LEGAL_HEAD_RE = re.compile(r"§\s*([\wIVXLC]+)")
SPACE_RE = re.compile(r"[ \t]+")
BLANKS_RE = re.compile(r"\n{3,}")

def _mk_id(*parts) -> str:
    return hashlib.sha1("|".join("" if p is None else str(p) for p in parts).encode()).hexdigest()[:16]

@dataclass
class SplitConfig:
    max_tokens_single: int = 512
    rec_chunk_size: int = 800
    rec_overlap: int = 100
    semantic_breakpoint: str = "percentile"

class AdvancedTextSplitter:
    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        legal_mode: bool = False,
        semantic_mode: bool = True,
        embeddings: Optional[OpenAIEmbeddings] = None,
        cfg: SplitConfig = SplitConfig(),
    ):
        self.legal_mode = legal_mode
        self.semantic_mode = semantic_mode
        self.cfg = cfg
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.embeddings = embeddings or (OpenAIEmbeddings(model=embedding_model) if semantic_mode else None)
        logger.info("AdvancedTextSplitter initialized legal=%s semantic=%s", legal_mode, semantic_mode)

    def _remove_boilerplate(self, text: str) -> str:
        text = SPACE_RE.sub(" ", text)
        text = BLANKS_RE.sub("\n\n", text)
        lines = [ln.rstrip() for ln in text.split("\n")]
        lines = [ln for ln in lines if ln.strip() != ""]
        return "\n".join(lines)

    def _split_by_headings(self, text: str) -> List[Dict[str, Any]]:
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
        tokens = self.encoder.encode(content)
        return Document(
            page_content=content,
            metadata={
                "documentId": document_id,
                "pageNumber": page_number,
                "heading": heading,
                "chunkType": chunk_type,
                "tokenCount": len(tokens),
                "chunkId": _mk_id(document_id, page_number, heading, chunk_type, content[:80]),
            }
        )

    def _chunk_with_metadata(self, content: str, document_id: str, page_number: Optional[int], heading: Optional[str], chunk_type: str) -> List[Document]:
        if len(self.encoder.encode(content)) <= self.cfg.max_tokens_single:
            return [self._wrap(content, document_id, page_number, heading, chunk_type)]

        if self.semantic_mode and self.embeddings is not None:
            try:
                sc = SemanticChunker(self.embeddings, breakpoint_threshold_type=self.cfg.semantic_breakpoint)
                docs = sc.create_documents([content])
                return [self._wrap(d.page_content, document_id, page_number, heading, "semantic") for d in docs]
            except Exception:
                logger.exception("Semantic chunking failed; falling back to recursive")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.cfg.rec_chunk_size,
            chunk_overlap=self.cfg.rec_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        docs = splitter.create_documents([content])
        return [self._wrap(d.page_content, document_id, page_number, heading, "recursive") for d in docs]

    def split_text(self, text: str, document_id: str, page_number: Optional[int] = None) -> List[Document]:
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
                body = "\n".join(s["content"])
                out.extend(self._chunk_with_metadata(body, document_id, page_number, s["heading"], "hierarchical"))
            return out

        return self._chunk_with_metadata(text, document_id, page_number, None, "generic")
