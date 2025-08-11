import io
import math
import pytesseract
from PIL import Image, ImageOps, ImageFilter
import fitz

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False


def _rotate_pil(img: Image.Image, angle_deg: float) -> Image.Image:
    """Rotate keeping full content (expand=True) and fill background white."""
    return img.rotate(-angle_deg, expand=True, fillcolor="white")


def _deskew_pil(img: Image.Image) -> Image.Image:
    """Quick deskew using Tesseract OSD if available."""
    try:
        osd = pytesseract.image_to_osd(img)
        for line in osd.splitlines():
            if "Orientation in degrees" in line or "Rotate" in line:
                angle = int(line.split(":")[-1].strip())
                if angle % 360 != 0:
                    return _rotate_pil(img, angle)
        return img
    except Exception:
        return img


def _preprocess_pil(img: Image.Image) -> Image.Image:
    """Lightweight preprocessing with PIL (if OpenCV not present)."""

    img = ImageOps.grayscale(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=3))
    img = ImageOps.autocontrast(img)
    return img


def _preprocess_cv2(img: Image.Image) -> Image.Image:
    """Stronger preprocessing with OpenCV if available."""
    arr = np.array(img)
    if arr.ndim == 3:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    else:
        gray = arr

    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    thr = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        21, 10
    )

    kernel = np.ones((2, 2), np.uint8)
    thr = cv2.morphologyEx(thr, cv2.MORPH_OPEN, kernel, iterations=1)

    return Image.fromarray(thr)


def extract_text_with_ocr(page: fitz.Page,
                          lang: str = "deu+eng",
                          psm: int = 6,
                          oem: int = 1,
                          dpi: int = 300,
                          max_side: int = 3000) -> str:
    """
    OCR with optional OpenCV preprocessing, orientation detection, and sane defaults.
    - lang: Tesseract languages (install 'deu' and 'eng' data if not present)
    - psm: Page segmentation mode (6 = uniform block of text; try 4 for multi-column)
    - oem: OCR engine mode (1 = LSTM only; 3 = default)
    - dpi: render DPI for page rasterization
    - max_side: downscale very large renderings to cap memory/latency
    """

    pix = page.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    w, h = img.size
    m = max(w, h)
    if m > max_side:
        scale = max_side / float(m)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    img = _deskew_pil(img)

    if HAS_CV2:
        img = _preprocess_cv2(img)
    else:
        img = _preprocess_pil(img)

    config = f"--oem {oem} --psm {psm}"
    try:
        text = pytesseract.image_to_string(img, lang=lang, config=config)
        return (text or "").strip()
    except Exception:
        try:
            fallback = f"--oem {oem} --psm 11"
            text = pytesseract.image_to_string(img, lang=lang, config=fallback)
            return (text or "").strip()
        except Exception:
            return ""

