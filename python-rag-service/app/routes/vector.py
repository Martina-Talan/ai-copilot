# routes/vector.py
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.services.generate_embeddings import generate_embeddings

router = APIRouter()

class EmbeddingInput(BaseModel):
    path: str
    filename: str
    id: str

@router.post("/generate-embeddings")
async def generate_embeddings_route(data: EmbeddingInput):
    return await generate_embeddings(data.path, data.filename, data.id)
