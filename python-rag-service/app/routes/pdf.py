from fastapi import APIRouter
from pydantic import BaseModel
from app.services.pdf_viewer import PDFProcessor


router = APIRouter()

class PdfViewRequest(BaseModel):
    path: str

@router.post("/view-pdf")
async def view_pdf_route(data: PdfViewRequest):
    return extract_pdf_pages(data.path)
