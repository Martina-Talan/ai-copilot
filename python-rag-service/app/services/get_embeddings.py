import os
import json
import pathlib
from typing import List, Dict
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from app.services.vector_store import save_to_faiss


def get_embeddings(chunks: List[str], metadata_list: List[Dict]) -> List[List[float]]:
    unique_ids = set(m.get("documentId") for m in metadata_list)
    if len(unique_ids) > 1:
        raise ValueError("Chunks from multiple documents detected. Please call get_embeddings() with only one document at a time.")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set in environment variables.")

    embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
    )
    embedded = embeddings.embed_documents(chunks)

    save_to_faiss(chunks, metadata_list)

    docs = [
        {
            "pageContent": chunk,
            "metadata": metadata_list[i]
        }
        for i, chunk in enumerate(chunks)
    ]

    pathlib.Path("./vector-data").mkdir(parents=True, exist_ok=True)
    with open("./vector-data/chunks.json", "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)

    return embedded
