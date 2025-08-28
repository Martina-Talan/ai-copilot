from fastapi import APIRouter
from pydantic import BaseModel
from app.services.pdf_viewer import PDFProcessor, PDFProcessorConfig
import asyncio

router = APIRouter()

class PdfViewRequest(BaseModel):
    path: str
    id: str

@router.post("/view-pdf")
async def view_pdf_route(data: PdfViewRequest):
    processor = PDFProcessor(cfg=PDFProcessorConfig())
    return await asyncio.to_thread(processor.extract_pdf_pages, data.path, data.id)
