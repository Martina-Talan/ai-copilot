from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.pdf_viewer import PDFProcessor, PDFProcessorConfig
from anyio import to_thread
import os

router = APIRouter()

UPLOAD_FOLDER = os.path.abspath(os.getenv("UPLOAD_FOLDER", "./uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class PdfViewRequest(BaseModel):
    path: str
    id: str

@router.post("/view-pdf")
async def view_pdf_route(data: PdfViewRequest):
    user_path = os.path.normpath(data.path).lstrip('/')
    safe_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, user_path))
    
    if not safe_path.startswith(UPLOAD_FOLDER):
        raise HTTPException(status_code=400, detail="Invalid path.")
    
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="File not found.")

    processor = PDFProcessor(cfg=PDFProcessorConfig())
    return await to_thread.run_sync(processor.extract_pdf_pages, safe_path, data.id)
