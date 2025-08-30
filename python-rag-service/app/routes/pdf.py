from fastapi import APIRouter
from pydantic import BaseModel
from app.services.pdf_viewer import PDFProcessor, PDFProcessorConfig
from anyio import to_thread

router = APIRouter()

class PdfViewRequest(BaseModel):
    path: str
    id: str

@router.post("/view-pdf")
async def view_pdf_route(data: PdfViewRequest):
    processor = PDFProcessor(cfg=PDFProcessorConfig())
    return await to_thread.run_sync(processor.extract_pdf_pages, data.path, data.id)
