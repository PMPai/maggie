"""run_ocr task persists OCR text to documents.ocr_text; on failure sets FAILED + null text.

These tests invoke the REAL run_ocr task via apply().get() in eager mode with
get_ocr_adapter and get_file_path monkeypatched, so the COMPLETED+text and
FAILED+null branches in run_ocr._run() are exercised end-to-end.
"""
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.document import Document, StorageRoot
from app.services.ocr.protocol import OCRResult


async def _seed_document(db, *, original_name: str, sha256: str, ocr_status: str = "PENDING"):
    """Insert a Document + StorageRoot row in the test DB and return its id."""
    root = StorageRoot(
        code="TEST", base_path="/tmp/test",
        storage_type="LOCAL", is_active=True, read_only=False, health_status="HEALTHY",
        created_by=uuid.uuid4(), updated_by=uuid.uuid4(),
    )
    db.add(root)
    await db.flush()
    doc = Document(
        project_id=None, storage_root_id=root.id,
        original_name=original_name, stored_name=f"{sha256}.pdf",
        relative_path=f"test/{sha256}.pdf",
        document_type="CONTRACT", mime_type="application/pdf", file_extension="pdf",
        size_bytes=100, sha256=sha256, version_no=1, is_original=True, is_immutable=False,
        ocr_status=ocr_status, uploaded_at=datetime.utcnow(),
        created_by=uuid.uuid4(), updated_by=uuid.uuid4(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc.id


class _FakeOCRAdapter:
    def __init__(self, *, text: str | None = None, raise_exc: Exception | None = None):
        self._text = text
        self._raise_exc = raise_exc

    def is_available(self) -> bool:
        return True

    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult:
        if self._raise_exc is not None:
            raise self._raise_exc
        return OCRResult(text=self._text, confidence=0.92, pages=1, bbox_data=[])


def _run_ocr_task(document_id, monkeypatch, *, fake_adapter):
    import concurrent.futures
    from app.tasks.celery_app import celery_app
    from app.tasks.tasks import run_ocr

    tmp_path = Path(_make_tmp_file())

    # Task uses settings.DATABASE_URL (its own engine). Point it at the same
    # maggie_test DB the test `db` fixture uses so the task's commit is visible
    # to the fixture's session.
    from app.config import Settings
    test_settings = Settings(
        DATABASE_URL="postgresql+asyncpg://maggie:maggie@postgres:5432/maggie_test",
        OCR_PROVIDER="none",
    )
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)

    monkeypatch.setattr(
        "app.services.ocr.get_ocr_adapter",
        lambda settings: fake_adapter,
    )
    monkeypatch.setattr(
        "app.services.file_service.get_file_path",
        lambda doc, db: _async_return(tmp_path),
    )

    celery_app.conf.task_always_eager = True
    try:
        # run_ocr calls asyncio.run(...), which cannot run inside the async
        # test's running event loop. Run the eager task in a subthread that
        # has no event loop of its own.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(run_ocr.apply, args=(str(document_id),))
            return future.result().get()
    finally:
        celery_app.conf.task_always_eager = False


def _make_tmp_file() -> str:
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with __import__("os").fdopen(fd, "wb") as f:
        f.write(b"%PDF-1.4 fake")
    return path


async def _async_return(value):
    return value


@pytest.mark.asyncio
async def test_run_ocr_persists_text_to_document(db, monkeypatch):
    """run_ocr stores the adapter's text and sets ocr_status=COMPLETED."""
    did = await _seed_document(db, original_name="ok.pdf", sha256="abc123")

    fake = _FakeOCRAdapter(text="合約編號 CQ880A-11501")
    payload = _run_ocr_task(did, monkeypatch, fake_adapter=fake)

    assert payload["ocr_status"] == "COMPLETED"
    assert payload["text_length"] > 0

    # Task commits via its own engine on the same maggie_test DB; re-query fresh.
    result = await db.execute(select(Document).where(Document.id == did))
    refreshed = result.scalar_one()
    assert refreshed.ocr_status == "COMPLETED"
    assert refreshed.ocr_text == "合約編號 CQ880A-11501"


@pytest.mark.asyncio
async def test_run_ocr_sets_failed_on_error(db, monkeypatch):
    """On adapter failure, ocr_status=FAILED and ocr_text is null."""
    did = await _seed_document(db, original_name="bad.pdf", sha256="def456", ocr_status="RUNNING")

    fake = _FakeOCRAdapter(raise_exc=RuntimeError("adapter exploded"))
    payload = _run_ocr_task(did, monkeypatch, fake_adapter=fake)

    assert payload["ocr_status"] == "FAILED"

    result = await db.execute(select(Document).where(Document.id == did))
    refreshed = result.scalar_one()
    assert refreshed.ocr_status == "FAILED"
    assert refreshed.ocr_text is None
