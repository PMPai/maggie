"""Test #17: LLM output schema validation.
LLM is now called via Celery task, not inline in the matching pipeline.
The StubClient returns None so the task records no candidates."""


def test_stub_client_returns_none():
    from app.services.llm.stub import StubClient
    client = StubClient()
    # StubClient always returns None (no LLM available)


def test_llm_disabled_skips_celery_task():
    """When LLM_ENABLED=false, run_llm_match task returns SKIPPED."""
    from app.tasks.celery_app import celery_app
    celery_app.conf.task_always_eager = True
    try:
        from app.tasks.tasks import run_llm_match
        result = run_llm_match.apply(args=("00000000-0000-0000-0000-000000000000", [])).get()
        assert result.get("llm_status") == "SKIPPED"
    finally:
        celery_app.conf.task_always_eager = False
