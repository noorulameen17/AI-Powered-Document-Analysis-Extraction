from __future__ import annotations

import io
import re
import logging

import pdfplumber
from docx import Document
from PIL import Image
import pytesseract

from ..core.config import settings


# Use root logger so messages show up in Docker/Celery logs even if module loggers aren't configured.
log = logging.getLogger()


def extract_text(file_bytes: bytes, file_type: str, file_name: str | None = None) -> str:
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    if file_type == "pdf":
        return _extract_pdf(file_bytes, file_name=file_name)
    if file_type == "docx":
        return _extract_docx(file_bytes)
    if file_type in {"image", "png", "jpg", "jpeg"}:
        return _extract_image(file_bytes)

    raise ValueError("Unsupported fileType. Use pdf, docx, or image")


def _looks_like_invoice_text(t: str) -> bool:
    tl = (t or "").lower()
    keys = ["invoice", "bill to", "ship to", "balance due", "subtotal", "total"]
    return sum(1 for k in keys if k in tl) >= 2


def _has_personish_name(t: str) -> bool:
    """Detect whether extracted text likely contains a receiver/person name.

    Important: PDFs/invoices contain many Title-Case bigrams that are *not* names
    (e.g. 'First Class', 'Balance Due'). Those must NOT disable OCR fallback.
    """

    if not t:
        return False

    # Collect all Title-Case bigrams.
    pairs = re.findall(r"\b([A-Z][a-z]{1,25})\s+([A-Z][a-z]{1,25})\b", t)
    if not pairs:
        return False

    bad_pairs = {
        "First Class",
        "Second Class",
        "Standard Class",
        "Ship Mode",
        "Ship To",
        "Bill To",
        "Balance Due",
        "Due Date",
        "Invoice Date",
        "Invoice Number",
        "Order Id",
        "Order Number",
        "Total Due",
        "Grand Total",
        "Sub Total",
        "Sales Tax",
    }

    # If any pair is not a known invoice phrase, treat it as a likely person-name signal.
    for a, b in pairs:
        cand = f"{a} {b}".strip()
        if cand in bad_pairs:
            continue
        # Also skip if it's obviously invoice-ish tokens.
        if re.search(r"(?i)\b(invoice|balance|total|subtotal|tax|ship|mode|due|date|order|amount|qty|quantity|rate)\b", cand):
            continue
        return True

    return False


def _ocr_pdf_first_page(pdf: pdfplumber.PDF) -> str:
    """OCR the first page of a PDF (best-effort)."""
    if not pdf.pages:
        return ""

    # Render at higher resolution to improve OCR quality.
    page = pdf.pages[0]
    pil_img = page.to_image(resolution=250).original.convert("RGB")
    # Keep config conservative/portable.
    return (pytesseract.image_to_string(pil_img) or "").strip()


def _extract_pdf(file_bytes: bytes, file_name: str | None = None) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # layout-preserving-ish text where possible
            page_text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            text_parts.append(page_text)

        extracted = "\n\n".join([t for t in text_parts if t]).strip()

        # --- decision debug (always log once per PDF) ---
        pairs = re.findall(r"\b([A-Z][a-z]{1,25})\s+([A-Z][a-z]{1,25})\b", extracted or "")
        sample_pairs = [f"{a} {b}" for a, b in pairs[:12]]
        prefix = f"file={file_name} " if file_name else ""
        looks_inv = _looks_like_invoice_text(extracted)

        # IMPORTANT: For invoices, generic title-case pairs are common ("First Class", "Rate Amount").
        # Only treat 'personish' as present if we can find a plausible name around Bill To / Ship To.
        personish_in_party_block = False
        try:
            party_blob = ""
            if extracted:
                for lab in ("Bill To", "Ship To", "Billed To", "Sold To", "Customer"):
                    for m in re.finditer(rf"(?i)\b{re.escape(lab)}\b\s*[:\-]?\s*", extracted):
                        party_blob += " " + extracted[m.end() : m.end() + 220]
            personish_in_party_block = _has_personish_name(party_blob)
        except Exception:
            personish_in_party_block = False

        has_personish_anywhere = _has_personish_name(extracted)
        # For invoice OCR decision, we only trust personish signals from the party block.
        has_personish_for_invoice = personish_in_party_block

        log.warning(
            "analyze_document debug %sPDF OCR decision extracted_len=%s looks_like_invoice=%s has_personish=%s has_personish_party=%s titlecase_pairs_sample=%s",
            prefix,
            len(extracted or ""),
            looks_inv,
            has_personish_anywhere,
            has_personish_for_invoice,
            sample_pairs,
        )

        # OCR fallback
        should_ocr = False
        if not extracted:
            should_ocr = True
        elif looks_inv:
            # Only block OCR if we see a plausible receiver name near Bill To / Ship To.
            if not has_personish_for_invoice:
                should_ocr = True

        if should_ocr:
            log.warning(
                "analyze_document debug %sPDF OCR fallback triggered extracted_len=%s looks_like_invoice=%s has_personish_party=%s",
                prefix,
                len(extracted or ""),
                looks_inv,
                has_personish_for_invoice,
            )
            try:
                ocr = _ocr_pdf_first_page(pdf)
                log.warning(
                    "analyze_document debug %sPDF OCR produced text_len=%s",
                    prefix,
                    len(ocr or ""),
                )
            except Exception as e:
                log.exception("analyze_document debug %sPDF OCR failed: %s", prefix, e)
                ocr = ""
            if ocr:
                if extracted:
                    return (extracted + "\n\n" + ocr).strip()
                return ocr

        return extracted


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
