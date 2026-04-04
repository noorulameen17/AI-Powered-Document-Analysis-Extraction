from celery import Celery

from ..core.config import settings

celery_app = Celery(
    "document_analysis",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Ensure tasks are registered when the worker starts
celery_app.autodiscover_tasks(["src.tasks"], force=True)
