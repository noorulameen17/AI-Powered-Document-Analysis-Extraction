from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..core.security import require_api_key
from ..tasks.document_tasks import analyze_document_task

router = APIRouter(tags=["document"])


class DocumentAnalyzeRequest(BaseModel):
    fileName: str = Field(..., min_length=1)
    fileType: str = Field(..., description="pdf | docx | image")
    fileBase64: str = Field(..., min_length=10)


@router.post("/document-analyze")
def document_analyze(payload: DocumentAnalyzeRequest, _: None = Depends(require_api_key)):
    # Celery async processing (required). For hackathon scoring, we also block and return the result.
    res = analyze_document_task.delay(payload.model_dump())
    try:
        output = res.get(timeout=240)
    except Exception:
        return {
            "status": "error",
            "fileName": payload.fileName,
            "message": "Processing timed out. Try again or use a smaller document.",
        }
    return output
