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


# --- invoice helpers ---

def _line_value(label: str, t: str) -> str | None:
    """Fetch a value after a label like 'Bill To:' from invoice-ish text."""
    return _find_first(rf"\b{re.escape(label)}\b\s*[:\-]?\s*([^\n\r]+)", t, re.IGNORECASE)


def _is_bad_invoice_name(s: str) -> bool:
    s2 = _clean(s).lower()
    # Common shipping/service terms that look like Title Case names
    bad = [
        "ship mode",
        "first class",
        "standard",
        "priority",
        "ground",
        "express",
        "overnight",
        "two day",
        "next day",
    ]
    return any(b in s2 for b in bad)


def _first_personish(s: str) -> str | None:
    """Conservative 2-word person name extractor for invoices."""
    s = _clean(s)
    if not s:
        return None

    # strip common labels
    s = re.sub(
        r"\b(bill\s*to|billed\s*to|ship\s*to|sold\s*to|to|from|invoice|date|due\s*date|ship\s*mode|shipping|method)\b\s*[:\-]?\s*",
        " ",
        s,
        flags=re.IGNORECASE,
    )

    m = re.search(r"\b([A-Z][a-z]{1,25})\s+([A-Z][a-z]{1,25})\b", s)
    if not m:
        return None

    name = f"{m.group(1)} {m.group(2)}".strip()
    if _is_bad_invoice_name(name):
        return None

    if re.search(r"(?i)\b(ship\s*mode|quantity|qty|rate|amount|total|balance|invoice|class)\b", name):
        return None

    return name or None


def _label_window_value(label: str, raw_text: str, max_window: int = 180) -> str | None:
    """Extract nearby text for a label even when line breaks/layout are lost.

    Looks for occurrences like 'Bill To'/'Ship To' then returns a short window:
    - Prefer immediate right-side text on the same line.
    - Also consider a small left-side window (some PDFs put value before label).

    This is intentionally heuristic; caller should validate via _first_personish().
    """

    if not raw_text:
        return None

    # Keep raw newlines but also handle cases where the extractor collapses them.
    t = raw_text

    for m in re.finditer(rf"(?i)\b{re.escape(label)}\b\s*[:\-]?\s*", t):
        start = m.end()
        right = t[start : start + max_window]
        if right:
            # Stop at next major label-ish marker to avoid swallowing whole invoice
            right = re.split(
                r"(?i)\b(?:ship\s*to|bill\s*to|invoice\s*(?:number|no\.|#)?|invoice\s*date|due\s*date|date|subtotal|tax|total|balance\s*due|amount|qty|quantity)\b",
                right,
                maxsplit=1,
            )[0]
            right = right.strip()
            if right:
                return right

        # Sometimes the value appears just before the label in messy text; try a small left window.
        left_start = max(0, m.start() - max_window)
        left = t[left_start : m.start()].strip()
        if left:
            left = left.splitlines()[-1].strip() if "\n" in left or "\r" in left else left
            left = left[-max_window:].strip()
            if left:
                return left

    return None


def _is_likely_code(s: str) -> bool:
    """Heuristic: detect SKU/order/invoice-like codes (not human-friendly item descriptions)."""
    s = _clean(s)
    if not s:
        return False
    # Many dashes/underscores + lots of digits
    digits = sum(ch.isdigit() for ch in s)
    letters = sum(ch.isalpha() for ch in s)
    seps = sum(ch in "-_" for ch in s)
    if len(s) >= 10 and digits >= 6 and seps >= 2:
        return True
    # Looks like ALLCAPS+digits code
    if re.fullmatch(r"[A-Z0-9][A-Z0-9\-_]{8,}", s):
        return True
    # No spaces and heavy digits
    if " " not in s and digits >= max(5, letters):
        return True
    return False


def _extract_invoice_quantity(raw_text: str) -> str | None:
    """Extract numeric quantity near a Quantity/Qty label."""
    for lab in ("Quantity", "Qty"):
        v = _label_neighbor_value(lab, raw_text)
        if not v:
            continue
        m = re.search(r"\b(\d{1,5})\b", v)
        if m:
            return m.group(1)
    return None


def _extract_invoice_item(t: str) -> str | None:
    """Try to extract a short item/description from invoices."""

    # Priority 1: explicit label neighbor extraction
    for lab in ("Item", "Description", "Product", "Service"):
        v = _label_neighbor_value(lab, t)
        if not v:
            continue
        vv = _clean(v).strip(" -:")
        if not vv:
            continue
        if re.fullmatch(r"(?i)(quantity|qty|rate|amount|subtotal|tax|total)", vv):
            continue
        if re.search(r"(?i)\b(thanks\s+for\s+your\s+business)\b", vv):
            continue
        # Avoid codes as item names
        if _is_likely_code(vv):
            continue
        return vv[:120]

    # Priority 2: common table-ish pattern after Description/Item header
    m = re.search(
        r"\b(?:Description|Item)\b\s+(.+?)(?=\b(?:Qty|Quantity|Rate|Amount|Subtotal|Tax|Total|Balance\s*Due)\b)",
        t,
        re.IGNORECASE,
    )
    if m:
        item = _clean(m.group(1)).strip(" -:")
        if item and len(item) >= 6 and not re.fullmatch(r"(?i)(quantity|qty|rate|amount)", item):
            if not re.search(r"(?i)\b(thanks\s+for\s+your\s+business)\b", item) and not _is_likely_code(item):
                return item[:120]

    # Greedy fallback: avoid obvious headers/labels and code-like strings
    candidates = re.findall(r"\b([A-Z][A-Za-z0-9,'\- ]{12,})\b", t)
    for c in candidates[:120]:
        c2 = _clean(c)
        if _is_likely_code(c2):
            continue
        if re.fullmatch(r"(?i)(quantity|qty|rate|amount|subtotal|tax|total|balance\s*due)", c2):
            continue
        if re.search(
            r"(?i)\b(invoice|bill\s*to|ship\s*to|ship\s*mode|subtotal|discount|shipping|tax|total|balance\s*due|quantity|qty|rate|amount|terms|thanks\s+for\s+your\s+business|first\s+class)\b",
            c2,
        ):
            continue
        return c2[:120]

    return None


def _extract_invoice_entities(t: str) -> dict:
    """Invoice entity extraction: avoid spaCy table/header noise."""

    names: set[str] = set()

    # Use both: (1) line-based in cleaned text and (2) neighbor/window search in raw text.
    # Many PDFs include punctuation in labels (e.g., 'Bill To:'), so check variants.
    bill_to = (
        _line_value("Bill To", t)
        or _line_value("Bill To:", t)
        or _line_value("BILL TO", t)
        or _line_value("BILL TO:", t)
    )
    ship_to = (
        _line_value("Ship To", t)
        or _line_value("Ship To:", t)
        or _line_value("SHIP TO", t)
        or _line_value("SHIP TO:", t)
    )

    for line in (bill_to, ship_to):
        if line:
            n = _first_personish(line)
            if n and not _is_bad_invoice_name(n) and n.lower() not in {"ship to", "bill to"}:
                names.add(n)
                break

    # Fallback: if PDF text preserved newlines, pull the value right/below the label
    if not names:
        for lab in ("Bill To", "Bill To:", "Ship To", "Ship To:", "Billed To", "Sold To", "Customer"):
            neigh = _label_neighbor_value(lab, t)
            if not neigh:
                continue
            n = _first_personish(neigh)
            if n and not _is_bad_invoice_name(n) and n.lower() not in {"ship to", "bill to"}:
                names.add(n)
                break

    # Stronger fallback: window around label (handles collapsed/inline PDF text)
    if not names:
        for lab in ("Bill To", "Bill To:", "Ship To", "Ship To:", "Billed To", "Sold To", "Customer"):
            w = _label_window_value(lab, t)
            if not w:
                continue
            n = _first_personish(w)
            if n and not _is_bad_invoice_name(n) and n.lower() not in {"ship to", "bill to"}:
                names.add(n)
                break

    # Fallback patterns remain, but still filter bad names
    if not names:
        for pat in [
            r"\b(?:customer|client|attn\.?|attention)\s*[:\-]?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\b",
            r"\bbill\s*to\b\s*:??\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\b",
            r"\bship\s*to\b\s*:??\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\b",
        ]:
            n2 = _find_first(pat, t, re.IGNORECASE)
            if n2:
                cand = _first_personish(n2) or n2
                if cand and not _is_bad_invoice_name(cand) and cand.lower() not in {"ship to", "bill to"}:
                    names.add(cand)
                    break

    # Dates
    dates: set[str] = set()
    for lab in ("Invoice Date", "Date", "Due Date"):
        line = _line_value(lab, t)
        if not line:
            continue
        d = _find_first(r"\b([A-Za-z]{3,9}\s+\d{1,2}(?:,)?\s+\d{4})\b", line, re.IGNORECASE)
        if d:
            dates.add(d.replace(",", "").strip())

    # Organizations
    orgs: set[str] = set()
    v = _line_value("From", t) or _line_value("Seller", t)
    if v and len(v.split()) <= 8:
        orgs.add(v.strip())

    amounts = set(_extract_amounts(t, invoice_mode=True))

    names = {n for n in names if not _is_bad_invoice_name(n) and n.lower() not in {"ship to", "bill to"}}

    return {
        "names": sorted(names),
        "dates": sorted(dates),
        "organizations": sorted(orgs),
        "amounts": sorted(amounts),
    }


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
    if _looks_like_invoice(t):
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

    invoice_no = (
        _find_first(r"\binvoice\s*(?:number|no\.?|#)\s*[:\-]?\s*([A-Z0-9\-_/]+)", t, re.IGNORECASE)
        or _find_first(r"\bINV[- ]?(\d{3,})\b", t, re.IGNORECASE)
        or _find_first(r"\b#\s*(\d{3,})\b", t, re.IGNORECASE)
    )

    # Dates: accept with/without comma
    invoice_date = _find_first(
        r"\b(?:invoice\s*date|date)\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{1,2}(?:,)?\s+\d{4})",
        t,
        re.IGNORECASE,
    )
    due_date = _find_first(
        r"\bdue\s*date\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{1,2}(?:,)?\s+\d{4})",
        t,
        re.IGNORECASE,
    )

    total_due = (
        _find_first(
            r"\bbalance\s*due\s*[:\-]?\s*((?:₹|\$|€|£)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
            t,
            re.IGNORECASE,
        )
        or _find_first(
            r"\btotal\s*due\s*[:\-]?\s*((?:₹|\$|€|£)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
            t,
            re.IGNORECASE,
        )
        or _find_first(
            r"\btotal\s*[:\-]?\s*((?:₹|\$|€|£)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
            t,
            re.IGNORECASE,
        )
    )

    # Receiver name
    receiver = None
    bt = _line_value("Bill To", t) or _find_party_block("Bill To", t) or _label_neighbor_value("Bill To", t) or _label_window_value("Bill To", t)
    st = _line_value("Ship To", t) or _find_party_block("Ship To", t) or _label_neighbor_value("Ship To", t) or _label_window_value("Ship To", t)
    for cand in (bt, st):
        if cand:
            receiver = _first_personish(cand)
            if receiver:
                break

    # Item/description + quantity
    item = _extract_invoice_item(t)
    qty = _extract_invoice_quantity(t)

    # Require at least something meaningful beyond boilerplate
    if not any([invoice_no, invoice_date, due_date, total_due, receiver, item, qty]):
        return None

    parts: list[str] = ["This document is an invoice"]
    if invoice_no:
        parts[0] += f" (#{invoice_no})"

    if receiver:
        parts.append(f"issued to {receiver}")

    if invoice_date:
        parts.append(f"dated {invoice_date.replace(',', '').strip()}")
    if due_date:
        parts.append(f"with due date {due_date.replace(',', '').strip()}")

    if item:
        if qty:
            parts.append(f"including item: {item} (qty {qty})")
        else:
            parts.append(f"including item: {item}")

    if total_due:
        parts.append(f"with a balance due of {total_due}")

    summary = " ".join(parts).strip()
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
    # Keep a raw copy (with newlines) because invoice parsing relies on line layout.
    raw = text or ""
    t = _clean(raw)
    if not t:
        return {"names": [], "dates": [], "organizations": [], "amounts": []}

    # Invoice path: use RAW text so _label_neighbor_value(splitlines) and other
    # label-based heuristics can work.
    if _looks_like_invoice(t):
        return _extract_invoice_entities(raw)

    nlp = _nlp()
    doc = nlp(text)

    names = set()
    dates = set()
    orgs = set()

    for ent in doc.ents:
        if ent.label_ in {"PERSON"}:
            v = ent.text.strip()
            # filter obvious headers
            if re.fullmatch(r"(?i)(skills|projects|frameworks|experience|education)", v):
                continue
            names.add(v)
        elif ent.label_ in {"DATE"}:
            dates.add(ent.text.strip())
        elif ent.label_ in {"ORG"}:
            v = ent.text.strip()
            if "@" in v:
                continue
            orgs.add(v)

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
    r"\b\(?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?|\b\d{4,}(?:\.\d+)?\b"
)


def _extract_amounts(text: str, invoice_mode: bool = False) -> list[str]:
    t = _clean(text)
    if not t:
        return []

    # 1) currency-aware extraction (preferred)
    hits: list[str] = [m.group(0).strip() for m in _money_re.finditer(t)]

    # Invoices: STRICT currency amounts only (avoid dates/IDs)
    if invoice_mode:
        seen: set[str] = set()
        out: list[str] = []
        for x in hits:
            x = x.strip()
            if not x or x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out[:200]

    # 2) fallback: plain numeric amounts (non-invoice)
    # Tighten: skip obvious years and date-like tokens.
    for m in _plain_amount_re.finditer(t):
        v = m.group(0).strip()
        if not v:
            continue

        # Skip years
        if re.fullmatch(r"(?:19\d{2}|20\d{2})", v):
            continue

        # Skip common date patterns like 03/31/2012 or 2012-03-31
        if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", v):
            continue
        if re.search(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b", v):
            continue

        hits.append(v)

    # Normalize whitespace and de-dup while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for x in hits:
        x = x.strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)

    return out[:200]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _label_neighbor_value(label: str, raw_text: str) -> str | None:
    """Extract text near a label from the ORIGINAL raw text.

    Heuristics:
    - Prefer value to the right on the same line:  'Bill To: Aaron Hawkins'
    - Else, take the next non-empty line (below):
        Bill To:
        Aaron Hawkins

    This requires raw_text with line breaks (so don't use _clean()).
    """

    if not raw_text:
        return None

    lines = raw_text.splitlines()
    # Allow optional trailing punctuation after label (common in invoices: 'Bill To:' / 'Bill To -')
    lab_re = re.compile(rf"^\s*{re.escape(label)}\s*[:\-]?\s*(.*)$", re.IGNORECASE)

    for i, line in enumerate(lines):
        m = lab_re.search(line)
        if not m:
            continue

        right = (m.group(1) or "").strip()
        if right:
            return right

        # look below
        for j in range(i + 1, min(i + 6, len(lines))):
            nxt = lines[j].strip()
            if not nxt:
                continue
            # stop if we hit another label-like line
            if re.match(r"(?i)^(bill\s*to|ship\s*to|invoice|date|due\s*date|subtotal|tax|total|balance\s*due)\b", nxt):
                break
            return nxt

    return None
