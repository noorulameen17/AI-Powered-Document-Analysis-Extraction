from __future__ import annotations

import logging

from .celery_app import celery_app
from ..services.document_service import analyze_document
from ..utils.extract_text import extract_text
from ..utils.ai import _extract_amounts

logger = logging.getLogger("celery.worker")


@celery_app.task(name="analyze_document")
def analyze_document_task(payload: dict) -> dict:
    """Celery entrypoint.

    Includes lightweight debug logs to help diagnose entity/amount extraction.
    """

    try:
        file_name = payload.get("fileName")
        file_type = (payload.get("fileType") or "").lower().strip()
        file_b64 = payload.get("fileBase64")

        # Try to decode + extract text for debug visibility.
        # (If this fails we still fall back to the normal analyze_document error path.)
        import base64

        raw_bytes = base64.b64decode(file_b64 or "")
        text = extract_text(raw_bytes, file_type=file_type, file_name=file_name)
        sample_amounts = _extract_amounts(text)

        # Use WARNING so it shows up even if the worker loglevel is INFO/ERROR.
        logger.warning(
            "analyze_document debug file=%s type=%s text_len=%s amounts=%s sample=%s",
            file_name,
            file_type,
            len(text or ""),
            len(sample_amounts),
            sample_amounts[:20],
        )
    except Exception as e:
        logger.warning("analyze_document debug skipped: %s", e)

    return analyze_document(payload)
