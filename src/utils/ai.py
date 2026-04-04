from __future__ import annotations

import re
from functools import lru_cache

import spacy
from transformers import pipeline

from ..core.config import settings


@lru_cache(maxsize=1)
def _sentiment():
    return pipeline("sentiment-analysis", model=settings.SENTIMENT_MODEL)


@lru_cache(maxsize=1)
def _nlp():
    return spacy.load(settings.SPACY_MODEL)


@lru_cache(maxsize=1)
def _summarizer():
    # Use a lightweight summarization model; cached so it loads once per process.
    return pipeline("summarization", model=settings.SUMMARIZATION_MODEL)


def summarize_text(text: str) -> str:
    """Summarize extracted text.

    Strategy:
    1) If the text looks like an invoice, generate a structured invoice summary.
       (Invoices mostly contain tables/labels; generic summarizers often just echo them.)
    2) Otherwise use the transformer summarizer.
    3) Fall back to a stable heuristic (lead sentences) if anything errors.
    """

    t = _clean(text)
    if not t:
        return ""

    # 1) Invoice-aware summary (best effort). If it returns a string, use it.
    inv = _summarize_invoice(t)
    if inv:
        return inv

    # 2) Generic AI summarizer with safe fallback.
    try:
        return _summarize_transformer(t)
    except Exception:
        return _summarize_lead_sentences(t)


def _looks_like_invoice(t: str) -> bool:
    tl = t.lower()
    keywords = [
        "invoice",
        "invoice number",
        "invoice #",
        "bill to",
        "total due",
        "due date",
        "subtotal",
        "tax",
    ]
    score = sum(1 for k in keywords if k in tl)
    return score >= 2


def _find_first(pattern: str, t: str, flags: int = 0) -> str | None:
    m = re.search(pattern, t, flags)
    if not m:
        return None
    # Prefer first capturing group if present; otherwise full match.
    if m.lastindex:
        return (m.group(1) or "").strip() or None
    return (m.group(0) or "").strip() or None


def _find_party_block(label: str, t: str) -> str | None:
    """Extract a short 'From:'/'To:' block from invoice-like text."""

    # Capture up to ~160 chars, stopping before the next well-known section label.
    # This is intentionally conservative to avoid pulling the entire invoice.
    pattern = rf"\b{re.escape(label)}\s*:\s*(.+?)(?=\b(?:to|from|invoice\s*date|due\s*date|total\s*due|subtotal|tax|total)\b|$)"
    block = _find_first(pattern, t, flags=re.IGNORECASE | re.DOTALL)
    if not block:
        return None

    block = _clean(block)
    block = re.sub(r"\s{2,}", " ", block).strip()
    # Trim very long blocks.
    if len(block) > 160:
        block = block[:160].rsplit(" ", 1)[0] + "…"
    return block or None


def _summarize_invoice(t: str) -> str | None:
    if not _looks_like_invoice(t):
        return None

    # Extract key fields (best-effort; invoices vary a lot).
    invoice_no = (
        _find_first(r"\binvoice\s*(?:number|no\.?|#)\s*[:\-]?\s*([A-Z0-9\-_/]+)", t, re.IGNORECASE)
        or _find_first(r"\bINV[- ]?(\d{3,})\b", t, re.IGNORECASE)
    )

    invoice_date = _find_first(r"\binvoice\s*date\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})", t, re.IGNORECASE)
    due_date = _find_first(r"\bdue\s*date\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})", t, re.IGNORECASE)

    # Prefer 'Total Due' if present, else 'Total'.
    total_due = _find_first(
        r"\btotal\s*due\s*[:\-]?\s*((?:₹|\$|€|£)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
        t,
        re.IGNORECASE,
    )
    if not total_due:
        total_due = _find_first(
            r"\btotal\s*[:\-]?\s*((?:₹|\$|€|£)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
            t,
            re.IGNORECASE,
        )

    from_party = _find_party_block("From", t)
    to_party = _find_party_block("To", t) or _find_party_block("Bill To", t)

    # If we couldn't get anything meaningful, fall back to generic summary.
    if not any([invoice_no, invoice_date, due_date, total_due, from_party, to_party]):
        return None

    # Build a human-readable summary.
    parts: list[str] = ["This document is an invoice"]

    if invoice_no:
        parts[0] += f" (#{invoice_no})"

    # Parties
    if from_party and to_party:
        parts.append(f"issued by {from_party} to {to_party}")
    elif from_party:
        parts.append(f"issued by {from_party}")
    elif to_party:
        parts.append(f"issued to {to_party}")

    # Dates
    if invoice_date:
        parts.append(f"dated {invoice_date}")
    if due_date:
        parts.append(f"with due date {due_date}")

    # Amount
    if total_due:
        parts.append(f"for a total due of {total_due}")

    summary = " ".join(parts).strip()
    # Ensure it ends neatly.
    if not summary.endswith("."):
        summary += "."
    return summary


def _summarize_lead_sentences(t: str) -> str:
    # Sentence split without NLTK (simple punctuation-based).
    sentences = re.split(r"(?<=[.!?])\s+", t)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 0]

    n = 4
    if len(t) > 5000:
        n = 6
    if len(t) > 15000:
        n = 8

    return " ".join(sentences[:n]).strip()


def _summarize_transformer(t: str) -> str:
    # Conservative chunk size to prevent token overflow.
    # (Tokenizers vary; chars is a safe approximate.)
    chunk_chars = 3000

    chunks: list[str] = []
    i = 0
    while i < len(t):
        chunk = t[i : i + chunk_chars].strip()
        if chunk:
            chunks.append(chunk)
        i += chunk_chars

    s = _summarizer()

    partials: list[str] = []
    for c in chunks[:8]:
        # Limit number of chunks summarized to keep runtime bounded.
        out = s(
            c,
            max_length=120,
            min_length=30,
            do_sample=False,
            truncation=True,
        )
        partials.append((out[0].get("summary_text") or "").strip())

    joined = " ".join([p for p in partials if p]).strip()
    if not joined:
        return ""

    # Optional second pass to compress multi-chunk summaries
    if len(partials) > 1 and len(joined) > 1200:
        out2 = s(
            joined[:6000],
            max_length=140,
            min_length=40,
            do_sample=False,
            truncation=True,
        )
        return (out2[0].get("summary_text") or joined).strip()

    return joined


def extract_entities(text: str) -> dict:
    nlp = _nlp()
    doc = nlp(text)

    names = set()
    dates = set()
    orgs = set()

    for ent in doc.ents:
        if ent.label_ in {"PERSON"}:
            names.add(ent.text.strip())
        elif ent.label_ in {"DATE"}:
            dates.add(ent.text.strip())
        elif ent.label_ in {"ORG"}:
            orgs.add(ent.text.strip())

    amounts = set(_extract_amounts(text))

    return {
        "names": sorted(names),
        "dates": sorted(dates),
        "organizations": sorted(orgs),
        "amounts": sorted(amounts),
    }


def analyze_sentiment(text: str) -> str:
    t = _clean(text)
    if not t:
        return "Neutral"

    # Invoices often contain words like "due", "late fee", "payment", which can skew
    # generic sentiment models toward Negative. For this demo, treat invoices as Neutral.
    if _looks_like_invoice(t):
        return "Neutral"

    snippet = t[:2500]
    out = _sentiment()(snippet, truncation=True)[0]
    label = (out.get("label") or "").upper()
    if "NEG" in label:
        return "Negative"
    if "POS" in label:
        return "Positive"
    return "Neutral"


# Currency-aware amounts (prefix symbol or suffix currency code)
_money_re = re.compile(
    r"(?:(?:₹|\$|€|£)\s?\(?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?|\(?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?\s?(?:INR|USD|EUR|GBP))"
)

# Plain numeric amounts commonly used in financial statements (no currency)
# Examples: 583,961 | 6858029 | (1,250,000) | 224600 | 144.50
_plain_amount_re = re.compile(
    r"\b\(?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?\b|\b\d{4,}(?:\.\d+)?\b"
)


def _extract_amounts(text: str) -> list[str]:
    t = _clean(text)
    if not t:
        return []

    # 1) currency-aware extraction
    hits: list[str] = [m.group(0).strip() for m in _money_re.finditer(t)]

    # 2) fallback: plain numeric amounts (balance sheets often omit currency symbols)
    hits.extend(m.group(0).strip() for m in _plain_amount_re.finditer(t))

    # Normalize whitespace and de-dup while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for x in hits:
        x = x.strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)

    # Keep response size reasonable (PDFs can contain hundreds of numbers)
    return out[:200]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
