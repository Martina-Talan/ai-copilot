from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.pdf_viewer import PDFProcessor, PDFProcessorConfig
import os

router = APIRouter()

class PdfViewRequest(BaseModel):
    path: str
    id: str

@router.post("/view-pdf")
async def view_pdf_route(data: PdfViewRequest):
    if not os.path.exists(data.path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    try:
        processor = PDFProcessor(cfg=PDFProcessorConfig())
        result = processor.extract_pdf_pages(data.path, data.id)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")