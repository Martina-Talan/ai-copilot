import pytesseract
from PIL import Image
import fitz
import io

def extract_text_with_ocr(page) -> str:
    pix = page.get_pixmap(dpi=300)
    img_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_bytes))
    return pytesseract.image_to_string(img).strip()
