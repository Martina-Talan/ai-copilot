from typing import List
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tiktoken import encoding_for_model


def split_text(text: str, document_id: str) -> List[Document]:
    clean_text = text.strip()
    if not clean_text:
        print("Received empty or blank text.")
        return []

    encoder = encoding_for_model("text-embedding-ada-002")

    if "§" in clean_text:
        sections = [s.strip() for s in clean_text.split("§") if s.strip()]
        docs = []

        for i, section in enumerate(sections):
            content = f"§{section}"
            tokens = encoder.encode(content)
            if 0 < len(tokens) <= 8192:
                docs.append(Document(
                    page_content=content,
                    metadata={
                        "section": f"§{i + 1}",
                        "documentId": str(document_id),
                        "chunkType": "section"
                    }
                ))
            else:
                print(f"Skipping chunk §{i + 1} with {len(tokens)} tokens")

        return docs

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )

    try:
        split_docs = splitter.create_documents([clean_text])
        final_docs = []

        for i, doc in enumerate(split_docs):
            final_docs.append(Document(
                page_content=doc.page_content,
                metadata={
                    "section": f"chunk-{i + 1}",
                    "documentId": str(document_id),
                    "chunkType": "recursive"
                }
            ))

        return final_docs

    except Exception as e:
        print("Recursive splitter failed:", e)
        return [Document(
            page_content=clean_text,
            metadata={
                "section": "full-text",
                "documentId": str(document_id),
                "chunkType": "full"
            }
        )]
