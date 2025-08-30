import os
from fastapi import HTTPException, APIRouter
from app.services.generate_embeddings import SmartDocumentProcessor

router = APIRouter()

UPLOAD_FOLDER = os.path.abspath(os.getenv("UPLOAD_FOLDER", "./uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

processor = SmartDocumentProcessor()

@router.post("/generate-embeddings")
async def generate_embeddings_route(data: EmbeddingInput):
    user_path = os.path.normpath(data.path).lstrip('/')
    safe_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, user_path))
    
    if not safe_path.startswith(UPLOAD_FOLDER):
        raise HTTPException(status_code=400, detail="Invalid path.")
    
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="File not found.")
    
    return await processor.ingest(source=safe_path, doc_id=data.id, filename=data.filename)