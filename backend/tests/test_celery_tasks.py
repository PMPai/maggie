"""Celery app and task tests."""
import pytest
from app.tasks.celery_app import celery_app


def test_celery_app_exists():
    assert celery_app is not None
    assert celery_app.main == "maggie"


def test_celery_app_config():
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.task_track_started is True
    assert celery_app.conf.task_acks_late is True


def test_celery_app_broker_url():
    from app.config import get_settings
    settings = get_settings()
    assert settings.REDIS_URL in celery_app.conf.broker_url


def test_generate_document_task_registered():
    from app.tasks.tasks import generate_document
    assert generate_document.name == "tasks.generate_document"


def test_run_ocr_task_registered():
    from app.tasks.tasks import run_ocr
    assert run_ocr.name == "tasks.run_ocr"


def test_run_llm_match_task_registered():
    from app.tasks.tasks import run_llm_match
    assert run_llm_match.name == "tasks.run_llm_match"


def test_generate_document_task_eager_execution():
    """Test task runs in eager mode (synchronous, no Redis needed)."""
    from app.tasks.celery_app import celery_app
    celery_app.conf.task_always_eager = True
    try:
        from app.tasks.tasks import generate_document
        result = generate_document.apply(args=("00000000-0000-0000-0000-000000000000", "pdf")).get()
        assert isinstance(result, dict)
        assert "error" in result or "document_id" in result
    finally:
        celery_app.conf.task_always_eager = False


def test_run_ocr_task_eager_execution():
    from app.tasks.celery_app import celery_app
    celery_app.conf.task_always_eager = True
    try:
        from app.tasks.tasks import run_ocr
        result = run_ocr.apply(args=("00000000-0000-0000-0000-000000000000",)).get()
        assert isinstance(result, dict)
    finally:
        celery_app.conf.task_always_eager = False
