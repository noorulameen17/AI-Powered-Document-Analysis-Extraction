from __future__ import annotations

import base64

from ..utils.extract_text import extract_text
from ..utils.ai import summarize_text, extract_entities, analyze_sentiment


def analyze_document(payload: dict) -> dict:
    file_name = payload.get("fileName")
    file_type = (payload.get("fileType") or "").lower().strip()
    file_b64 = payload.get("fileBase64")

    try:
        raw_bytes = base64.b64decode(file_b64)
    except Exception:
        return {"status": "error", "fileName": file_name, "message": "Invalid Base64"}

    try:
        text = extract_text(raw_bytes, file_type=file_type, file_name=file_name)
        if not text.strip():
            return {
                "status": "error",
                "fileName": file_name,
                "message": "No text extracted",
            }

        summary = summarize_text(text)
        entities = extract_entities(text)
        sentiment = analyze_sentiment(text)

        return {
            "status": "success",
            "fileName": file_name,
            "summary": summary,
            "entities": entities,
            "sentiment": sentiment,
        }
    except Exception as e:
        return {"status": "error", "fileName": file_name, "message": str(e)}
