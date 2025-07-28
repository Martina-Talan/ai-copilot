from fastapi import HTTPException
from app.services.vector_store import load_faiss_store
from app.services.open_ai import get_answer_from_openai
import re


async def handle_ask_question(question: str, document_id: str):
    if not question or not document_id:
        raise HTTPException(status_code=400, detail="Question and documentId are required.")

    try:
        vector_store = load_faiss_store(document_id)

        similar_chunks = vector_store.similarity_search(question, k=10)

        def extract_highlights(text: str, keywords: List[str]) -> List[str]:
            found = []
            for kw in keywords:
                if re.search(rf'\b{re.escape(kw)}\b', text, re.IGNORECASE):
                   found.append(kw)
            return found

        filtered = [c for c in similar_chunks if str(c.metadata.get("documentId")) == str(document_id)]

        if not filtered:
            raise HTTPException(status_code=404, detail="No relevant content found for this document.")

        top_chunks = filtered[:4]
        context = "\n\n---\n\n".join(c.page_content for c in top_chunks)
        answer = await get_answer_from_openai(context, question)

        question_keywords = question.split()

        sources = [
            {
                **chunk.metadata,
                "textMatch": chunk.page_content,
                "pageIndicator": f"Page {chunk.metadata.get('pageNumber')}",
                "confidence": 1,
                "highlights": extract_highlights(chunk.page_content, question_keywords)
            }
            for chunk in top_chunks
        ]


        return {
            "answer": answer,
            "sources": sources,
            "debug": {
                "chunksAnalyzed": len(similar_chunks),
                "chunksUsed": len(top_chunks)
            }
        }

    except Exception as e:
        print("Error in handle_ask_question:", e)
        raise HTTPException(status_code=500, detail=str(e))
