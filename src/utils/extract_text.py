from __future__ import annotations

import io

import pdfplumber
from docx import Document
from PIL import Image
import pytesseract

from ..core.config import settings


def extract_text(file_bytes: bytes, file_type: str, file_name: str | None = None) -> str:
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    if file_type == "pdf":
        return _extract_pdf(file_bytes)
    if file_type == "docx":
        return _extract_docx(file_bytes)
    if file_type in {"image", "png", "jpg", "jpeg"}:
        return _extract_image(file_bytes)

    raise ValueError("Unsupported fileType. Use pdf, docx, or image")


def _extract_pdf(file_bytes: bytes) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # layout-preserving-ish text where possible
            page_text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            text_parts.append(page_text)
    return "\n\n".join([t for t in text_parts if t])


def _extract_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    parts: list[str] = []
    for p in doc.paragraphs:
        if p.text.strip():
            parts.append(p.text)
    return "\n".join(parts)


def _extract_image(file_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    # Basic configuration; can be tuned
    return pytesseract.image_to_string(img)
