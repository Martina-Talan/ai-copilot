import fitz
from typing import List, Dict
from app.services.get_embeddings import get_embeddings
from app.services.chunk_text import split_text
from app.services.utils.ocr_fallback import extract_text_with_ocr


async def generate_embeddings(path: str, filename: str, doc_id: str):
    try:
        doc = fitz.open(path)
        docs = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()

            if not page_text:
                print(f"Using OCR for page {page_num + 1}")
                page_text = extract_text_with_ocr(page)

            chunks = split_text(page_text, doc_id)

            for chunk in chunks:
                metadata = {
                    "documentId": doc_id,
                    **chunk.metadata,
                    "filename": filename,
                    "pageNumber": page_num + 1
                }
                docs.append({
                    "pageContent": chunk.page_content,
                    "metadata": metadata
                })

        get_embeddings(
            [d["pageContent"] for d in docs],
            [d["metadata"] for d in docs]
        )

        return { "message": "Embeddings saved with page numbers" }

    except Exception as e:
        print("PDF processing failed:", e)
        return { "error": "Failed to extract PDF pages" }
