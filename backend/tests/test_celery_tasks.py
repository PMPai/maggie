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
