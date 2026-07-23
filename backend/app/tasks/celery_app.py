"""Celery application instance and configuration."""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "maggie",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone=settings.DEFAULT_TIMEZONE,
    task_track_started=True,
    task_time_limit=300,
    task_acks_late=True,
    task_retries=2,
    retry_backoff=True,
    retry_backoff_max=60,
)
