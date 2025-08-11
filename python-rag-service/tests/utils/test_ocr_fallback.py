import io
import types
import builtins
from PIL import Image
import pytest

import app.services.utils.ocr_fallback as ocr_mod

class FakePixmap:
    def __init__(self, w=400, h=300, color=(255, 255, 255)):
        img = Image.new("RGB", (w, h), color)
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        self._bytes = bio.getvalue()
    def tobytes(self, fmt="png"):
        return self._bytes

class FakePage:
    def __init__(self, w=400, h=300):
        self._pm = FakePixmap(w, h)
    def get_pixmap(self, dpi=300):
        return self._pm

def test_basic_success(monkeypatch):
    monkeypatch.setattr(ocr_mod, "HAS_CV2", False, raising=False)
    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_osd", lambda img: "Rotate: 0\n")
    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_string", lambda img, lang, config: "Hallo Welt")

    page = FakePage()
    txt = ocr_mod.extract_text_with_ocr(page, lang="deu+eng", psm=6, oem=1, dpi=72)
    assert txt == "Hallo Welt"

def test_psm_fallback(monkeypatch):
    monkeypatch.setattr(ocr_mod, "HAS_CV2", False, raising=False)
    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_osd", lambda img: "Rotate: 0\n")

    calls = {"n": 0}
    def fail_once(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return "fallback ok"
    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_string", fail_once)

    page = FakePage()
    txt = ocr_mod.extract_text_with_ocr(page)
    assert txt == "fallback ok"

def test_all_fail_returns_empty(monkeypatch):
    monkeypatch.setattr(ocr_mod, "HAS_CV2", False, raising=False)
    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_osd", lambda img: "Rotate: 0\n")
    def always_fail(*args, **kwargs):
        raise RuntimeError("nope")
    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_string", always_fail)

    page = FakePage()
    assert ocr_mod.extract_text_with_ocr(page) == ""

def test_osd_rotation_applied(monkeypatch):
    monkeypatch.setattr(ocr_mod, "HAS_CV2", False, raising=False)
    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_osd", lambda img: "Orientation in degrees: 90\n")
    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_string", lambda img, lang, config: "rotated")
    page = FakePage()
    assert ocr_mod.extract_text_with_ocr(page) == "rotated"

def test_resize_when_too_large(monkeypatch):
    monkeypatch.setattr(ocr_mod, "HAS_CV2", False, raising=False)
    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_osd", lambda img: "Rotate: 0\n")

    seen_sizes = {}
    def spy_image_to_string(img, lang, config):
        seen_sizes["size"] = img.size
        return "ok"
    monkeypatch.setattr(ocr_mod.pytesseract, "image_to_string", spy_image_to_string)

    page = FakePage(w=6000, h=4000)
    txt = ocr_mod.extract_text_with_ocr(page, max_side=3000)
    assert txt == "ok"
    assert max(seen_sizes["size"]) == 3000
