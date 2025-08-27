import io
import os
import logging
from typing import Optional, Dict, Any

import pytesseract
from PIL import Image, ImageOps, ImageFilter
import fitz

logger = logging.getLogger(__name__)

# --------------------------------------------------------------
# Optional CV2 Support
# --------------------------------------------------------------

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False
    logger.info("OpenCV not available; falling back to PIL for OCR preprocessing")

# --------------------------------------------------------------
# Rotate image if misaligned
# --------------------------------------------------------------

def _rotate_pil(img: Image.Image, angle_deg: float) -> Image.Image:
    """Rotate the image by the given angle (counterclockwise).

    Args:
        img: PIL image to rotate.
        angle_deg: Angle in degrees.

    Returns:
        Rotated image with white background fill.
    """
    return img.rotate(-angle_deg, expand=True, fillcolor="white")

# --------------------------------------------------------------
# Detect skew and rotate accordingly
# --------------------------------------------------------------

def _deskew_pil(img: Image.Image) -> Image.Image:
    """Deskew image using Tesseract's orientation detection.

    Args:
        img: PIL image.

    Returns:
        Deskewed image if orientation was detected; original otherwise.
    """
    try:
        osd = pytesseract.image_to_osd(img)
        for line in osd.splitlines():
            if "Orientation in degrees" in line or "Rotate" in line:
                angle = int(line.split(":")[-1].strip())
                if angle % 360 != 0:
                    logger.info("Rotating image by %d degrees", angle)
                    return _rotate_pil(img, angle)
    except Exception as e:
        logger.warning("Deskew failed: %s", e)
    return img

# --------------------------------------------------------------
# Preprocessing using PIL
# --------------------------------------------------------------

def _preprocess_pil(img: Image.Image) -> Image.Image:
    """Apply grayscale and noise reduction using PIL.

    Args:
        img: PIL image.

    Returns:
        Preprocessed image.
    """
    img = ImageOps.grayscale(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=3))
    img = ImageOps.autocontrast(img)
    return img


# --------------------------------------------------------------
# Preprocessing using OpenCV
# --------------------------------------------------------------

def _preprocess_cv2(img: Image.Image) -> Image.Image:
    """Apply OpenCV-based adaptive thresholding and filtering.

    Args:
        img: PIL image.

    Returns:
        PIL image after OpenCV preprocessing.
    """
    arr = np.array(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) if arr.ndim == 3 else arr
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 21, 10)
    kernel = np.ones((2, 2), np.uint8)
    thr = cv2.morphologyEx(thr, cv2.MORPH_OPEN, kernel, iterations=1)
    return Image.fromarray(thr)


# --------------------------------------------------------------
# Extract text from a PDF page using OCR
# --------------------------------------------------------------

def extract_text_with_ocr(
    page: fitz.Page,
    lang: str = "deu+eng",
    psm: int = 6,
    oem: int = 1,
    dpi: int = 300,
    max_side: int = 3000
) -> str:
    """Extract text from a PDF page using OCR.

    Args:
        page: A PyMuPDF page object.
        lang: Tesseract language codes (e.g. "eng", "deu+eng").
        psm: Page segmentation mode.
        oem: OCR engine mode.
        dpi: Dots per inch (resolution).
        max_side: Maximum side length for scaling.

    Returns:
        OCR-extracted text.
    """
    try:
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception as e:
        logger.error("Failed to render PDF page to image: %s", e)
        return ""

    # Resize if too large
    w, h = img.size
    m = max(w, h)
    if m > max_side:
        scale = max_side / float(m)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Deskew and preprocess
    img = _deskew_pil(img)
    img = _preprocess_cv2(img) if HAS_CV2 else _preprocess_pil(img)

    # OCR
    config = f"--oem {oem} --psm {psm}"
    try:
        text = pytesseract.image_to_string(img, lang=lang, config=config)
        return (text or "").strip()
    except Exception as e:
        logger.warning("OCR primary config failed: %s", e)
        try:
            fallback_config = f"--oem {oem} --psm 11"
            text = pytesseract.image_to_string(img, lang=lang, config=fallback_config)
            return (text or "").strip()
        except Exception as e:
            logger.error("OCR fallback failed: %s", e)
            return ""
