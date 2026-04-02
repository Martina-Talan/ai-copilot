from fastapi import APIRouter
from pydantic import BaseModel
from app.services.generate_embeddings import SmartDocumentProcessor

router = APIRouter()

class EmbeddingInput(BaseModel):
    path: str
    filename: str
    id: str

processor = SmartDocumentProcessor()

@router.post("/generate-embeddings")
async def generate_embeddings_route(data: EmbeddingInput):
    return await processor.ingest(
        source=data.path,
        doc_id=data.id,
        filename=data.filename
    )
