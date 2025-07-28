import os
from typing import List, Dict
from langchain_community.vectorstores import FAISS 
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document


def save_to_faiss(texts: List[str], metadatas: List[Dict], dir: str = "faiss_index") -> None:
    if len(texts) != len(metadatas):
        raise ValueError("texts and metadatas must have the same length")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise EnvironmentError("OPENAI_API_KEY not set")

    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

    docs = [
        Document(
            page_content=texts[i],
            metadata={**metadatas[i], "documentId": str(metadatas[i].get("documentId"))}
        )
        for i in range(len(texts))
    ]

    vector_store = FAISS.from_documents(docs, embeddings)

    document_id = metadatas[0].get("documentId")
    if not document_id:
        raise ValueError("Document ID is missing in metadata")

    target_dir = os.path.join(dir, f"doc_{document_id}")
    os.makedirs(target_dir, exist_ok=True)

    vector_store.save_local(target_dir)
    print(f"FAISS store saved to {target_dir}")


def load_faiss_store(document_id: str, base_dir: str = "faiss_index") -> FAISS:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise EnvironmentError("OPENAI_API_KEY not set")

    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    dir_path = os.path.join(base_dir, f"doc_{document_id}")

    return FAISS.load_local(
        dir_path,
        embeddings,
        allow_dangerous_deserialization=True
    )
