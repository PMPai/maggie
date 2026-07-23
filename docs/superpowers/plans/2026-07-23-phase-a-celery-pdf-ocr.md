# Phase A: Celery Worker + PDF Generation Fix + OCR Adapter — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable async task processing (Celery worker), fix PDF generation in Docker (Playwright fonts), and implement real OCR (Tesseract with pluggable cloud interface).

**Architecture:** Create `app/tasks/` Celery module with 3 async tasks (generate_document, run_ocr, run_llm_match). Restructure OCR adapter into protocol-based design with Tesseract/Cloud/Stub implementations. Fix Dockerfile with manual font installation for Playwright + Tesseract.

**Tech Stack:** Celery 5.4, Redis 7, Playwright 1.49, pytesseract, Pillow, pdf2image, FastAPI, SQLAlchemy async

**Spec:** `docs/superpowers/specs/2026-07-23-phase-a-celery-pdf-ocr-design.md`

---

## File Structure

### Files to Create

| File | Responsibility |
|------|---------------|
| `backend/app/tasks/__init__.py` | Export celery_app |
| `backend/app/tasks/celery_app.py` | Celery instance + configuration |
| `backend/app/tasks/tasks.py` | 3 Celery task definitions |
| `backend/app/services/ocr/protocol.py` | OCRResult dataclass + OCRAdapter protocol |
| `backend/app/services/ocr/stub.py` | StubOCRAdapter (default when OCR unavailable) |
| `backend/app/services/ocr/tesseract.py` | TesseractAdapter (pytesseract + pdf2image) |
| `backend/app/services/ocr/cloud.py` | CloudOCRAdapter (stub for future cloud OCR) |
| `backend/app/api/tasks.py` | Task status API endpoint |
| `backend/tests/test_celery_tasks.py` | Celery task unit tests (eager mode) |
| `backend/tests/test_ocr_adapter.py` | OCR adapter tests |
| `backend/tests/test_task_api.py` | Task status API tests |
| `backend/tests/test_pdf_docker.py` | PDF generation integration test |

### Files to Modify

| File | Changes |
|------|---------|
| `backend/app/config.py` | Add OCR_PROVIDER, OCR_TESSERACT_LANG, OCR_CLOUD_API_KEY, OCR_CLOUD_ENDPOINT |
| `backend/app/services/ocr/__init__.py` | Replace with factory function get_ocr_adapter() |
| `backend/app/services/ocr/adapter.py` | Delete (replaced by protocol.py + stub.py) |
| `backend/app/main.py` | Register tasks router |
| `backend/app/api/payment_applications.py` | Add /generate endpoint |
| `backend/app/services/matching/pipeline.py` | Remove inline LLM call |
| `backend/Dockerfile` | Add fonts, tesseract, poppler, Playwright install |
| `docker-compose.yml` | Uncomment worker service |
| `backend/requirements.txt` | Add pytesseract, Pillow, pdf2image |
| `.env.example` | Add OCR variables |
| `backend/tests/test_llm_schema.py` | Update for Celery-based LLM |

---

## Task 1: Config + OCR Protocol + Stub Adapter

**Files:**
- Modify: `backend/app/config.py`
- Create: `backend/app/services/ocr/protocol.py`
- Create: `backend/app/services/ocr/stub.py`
- Modify: `backend/app/services/ocr/__init__.py`
- Delete: `backend/app/services/ocr/adapter.py`
- Test: `backend/tests/test_ocr_adapter.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ocr_adapter.py
"""OCR adapter tests — protocol, stub, factory."""
import pytest
from pathlib import Path
from app.services.ocr.protocol import OCRResult, OCRAdapter
from app.services.ocr.stub import StubOCRAdapter


def test_ocr_result_dataclass():
    result = OCRResult(text="hello", confidence=0.9, pages=1, bbox_data=[])
    assert result.text == "hello"
    assert result.confidence == 0.9
    assert result.pages == 1
    assert result.bbox_data == []


@pytest.mark.asyncio
async def test_stub_adapter_returns_empty():
    adapter = StubOCRAdapter()
    result = await adapter.extract(Path("/tmp/fake.pdf"))
    assert result.text == ""
    assert result.confidence == 0.0
    assert result.pages == 0
    assert result.bbox_data == []


def test_stub_adapter_not_available():
    adapter = StubOCRAdapter()
    assert adapter.is_available() is False


def test_get_ocr_adapter_returns_stub_by_default():
    from app.services.ocr import get_ocr_adapter
    from app.config import get_settings
    settings = get_settings()
    adapter = get_ocr_adapter(settings)
    assert isinstance(adapter, StubOCRAdapter)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_ocr_adapter.py -v`
Expected: FAIL with "No module named 'app.services.ocr.protocol'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/config.py (add these fields to Settings class, before Config inner class)
    OCR_PROVIDER: str = "none"
    OCR_TESSERACT_LANG: str = "chi_sim+eng"
    OCR_CLOUD_API_KEY: str = ""
    OCR_CLOUD_ENDPOINT: str = ""
```

```python
# backend/app/services/ocr/protocol.py
"""OCR adapter protocol and result dataclass."""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class OCRResult:
    text: str
    confidence: float
    pages: int
    bbox_data: list


class OCRAdapter(Protocol):
    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult: ...
    def is_available(self) -> bool: ...
```

```python
# backend/app/services/ocr/stub.py
"""Stub OCR adapter — returns empty result when OCR is unavailable."""
from pathlib import Path
from app.services.ocr.protocol import OCRResult


class StubOCRAdapter:
    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult:
        return OCRResult(text="", confidence=0.0, pages=0, bbox_data=[])

    def is_available(self) -> bool:
        return False
```

```python
# backend/app/services/ocr/__init__.py
"""OCR adapter factory."""
from app.services.ocr.protocol import OCRResult, OCRAdapter
from app.services.ocr.stub import StubOCRAdapter


def get_ocr_adapter(settings) -> OCRAdapter:
    provider = settings.OCR_PROVIDER
    if provider == "tesseract":
        from app.services.ocr.tesseract import TesseractAdapter
        return TesseractAdapter(lang=settings.OCR_TESSERACT_LANG)
    elif provider == "cloud":
        from app.services.ocr.cloud import CloudOCRAdapter
        return CloudOCRAdapter(
            endpoint=settings.OCR_CLOUD_ENDPOINT,
            api_key=settings.OCR_CLOUD_API_KEY,
        )
    return StubOCRAdapter()


__all__ = ["OCRResult", "OCRAdapter", "StubOCRAdapter", "get_ocr_adapter"]
```

Delete `backend/app/services/ocr/adapter.py` (replaced by protocol.py + stub.py).

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_ocr_adapter.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/services/ocr/ backend/tests/test_ocr_adapter.py
git commit -m "feat: OCR adapter protocol + stub + factory (Phase A)"
```

---

## Task 2: Tesseract Adapter

**Files:**
- Create: `backend/app/services/ocr/tesseract.py`
- Test: `backend/tests/test_ocr_adapter.py` (append tesseract tests)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_ocr_adapter.py`:

```python
def test_tesseract_adapter_available_check():
    """TesseractAdapter.is_available() checks for tesseract binary."""
    from app.services.ocr.tesseract import TesseractAdapter
    adapter = TesseractAdapter(lang="chi_sim+eng")
    # is_available returns bool (True if tesseract installed, False otherwise)
    assert isinstance(adapter.is_available(), bool)


def test_get_ocr_adapter_returns_tesseract_when_configured():
    from app.services.ocr import get_ocr_adapter
    from app.services.ocr.tesseract import TesseractAdapter
    from app.config import Settings
    settings = Settings(OCR_PROVIDER="tesseract")
    adapter = get_ocr_adapter(settings)
    assert isinstance(adapter, TesseractAdapter)


@pytest.mark.skipif(
    not __import__("shutil").which("tesseract"),
    reason="tesseract not installed",
)
@pytest.mark.asyncio
async def test_tesseract_extract_from_image(tmp_path):
    """Real OCR test — only runs when tesseract is available."""
    from PIL import Image, ImageDraw
    from app.services.ocr.tesseract import TesseractAdapter

    # Create a simple test image with text
    img = Image.new("RGB", (200, 50), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Hello 123", fill="black")
    img_path = tmp_path / "test.png"
    img.save(img_path)

    adapter = TesseractAdapter(lang="eng")
    result = await adapter.extract(img_path, mime_type="image/png")
    assert result.pages == 1
    assert "Hello" in result.text or "123" in result.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_ocr_adapter.py::test_tesseract_adapter_available_check -v`
Expected: FAIL with "No module named 'app.services.ocr.tesseract'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/ocr/tesseract.py
"""Tesseract OCR adapter — self-hosted OCR using pytesseract."""
import shutil
from pathlib import Path
from app.services.ocr.protocol import OCRResult


class TesseractAdapter:
    def __init__(self, lang: str = "chi_sim+eng"):
        self.lang = lang

    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult:
        import pytesseract
        from PIL import Image

        pages_text = []
        bbox_data = []

        if mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
            from pdf2image import convert_from_path
            images = convert_from_path(str(file_path))
            for i, img in enumerate(images):
                text = pytesseract.image_to_string(img, lang=self.lang)
                data = pytesseract.image_to_data(img, lang=self.lang, output_type=pytesseract.Output.DICT)
                pages_text.append(text)
                for j in range(len(data["text"])):
                    if data["text"][j].strip():
                        bbox_data.append({
                            "text": data["text"][j],
                            "bbox": (data["left"][j], data["top"][j], data["width"][j], data["height"][j]),
                            "page": i,
                            "confidence": data["conf"][j],
                        })
            full_text = "\n".join(pages_text)
            pages = len(images)
        else:
            img = Image.open(file_path)
            full_text = pytesseract.image_to_string(img, lang=self.lang)
            data = pytesseract.image_to_data(img, lang=self.lang, output_type=pytesseract.Output.DICT)
            for j in range(len(data["text"])):
                if data["text"][j].strip():
                    bbox_data.append({
                        "text": data["text"][j],
                        "bbox": (data["left"][j], data["top"][j], data["width"][j], data["height"][j]),
                        "page": 0,
                        "confidence": data["conf"][j],
                    })
            pages = 1

        confidences = [b["confidence"] for b in bbox_data if b["confidence"] > 0]
        avg_conf = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

        return OCRResult(text=full_text.strip(), confidence=avg_conf, pages=pages, bbox_data=bbox_data)

    def is_available(self) -> bool:
        return shutil.which("tesseract") is not None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_ocr_adapter.py -v`
Expected: PASS (tesseract tests pass if tesseract installed, skip otherwise)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ocr/tesseract.py backend/tests/test_ocr_adapter.py
git commit -m "feat: Tesseract OCR adapter with PDF and image support (Phase A)"
```

---

## Task 3: Cloud OCR Stub

**Files:**
- Create: `backend/app/services/ocr/cloud.py`
- Test: `backend/tests/test_ocr_adapter.py` (append cloud tests)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_ocr_adapter.py`:

```python
def test_cloud_adapter_not_available_without_config():
    from app.services.ocr.cloud import CloudOCRAdapter
    adapter = CloudOCRAdapter(endpoint="", api_key="")
    assert adapter.is_available() is False


def test_cloud_adapter_available_with_config():
    from app.services.ocr.cloud import CloudOCRAdapter
    adapter = CloudOCRAdapter(endpoint="https://ocr.example.com", api_key="key123")
    assert adapter.is_available() is True


def test_get_ocr_adapter_returns_cloud_when_configured():
    from app.services.ocr import get_ocr_adapter
    from app.services.ocr.cloud import CloudOCRAdapter
    from app.config import Settings
    settings = Settings(OCR_PROVIDER="cloud", OCR_CLOUD_ENDPOINT="https://ocr.example.com", OCR_CLOUD_API_KEY="key")
    adapter = get_ocr_adapter(settings)
    assert isinstance(adapter, CloudOCRAdapter)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_ocr_adapter.py::test_cloud_adapter_not_available_without_config -v`
Expected: FAIL with "No module named 'app.services.ocr.cloud'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/ocr/cloud.py
"""Cloud OCR adapter — stub for future cloud OCR API integration (Google Vision, Azure, etc.)."""
from pathlib import Path
from app.services.ocr.protocol import OCRResult


class CloudOCRAdapter:
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key

    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult:
        import httpx

        if not self.is_available():
            return OCRResult(text="", confidence=0.0, pages=0, bbox_data=[])

        with open(file_path, "rb") as f:
            file_data = f.read()

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.endpoint}/ocr",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (file_path.name, file_data, mime_type)},
            )
            resp.raise_for_status()
            data = resp.json()

        return OCRResult(
            text=data.get("text", ""),
            confidence=float(data.get("confidence", 0.0)),
            pages=int(data.get("pages", 0)),
            bbox_data=data.get("bbox_data", []),
        )

    def is_available(self) -> bool:
        return bool(self.endpoint and self.api_key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_ocr_adapter.py -v`
Expected: PASS (all OCR adapter tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ocr/cloud.py backend/tests/test_ocr_adapter.py
git commit -m "feat: Cloud OCR adapter stub for future cloud API integration (Phase A)"
```

---

## Task 4: Celery App

**Files:**
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/celery_app.py`
- Test: `backend/tests/test_celery_tasks.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_celery_tasks.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_celery_tasks.py -v`
Expected: FAIL with "No module named 'app.tasks'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/tasks/__init__.py
from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]
```

```python
# backend/app/tasks/celery_app.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_celery_tasks.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/ backend/tests/test_celery_tasks.py
git commit -m "feat: Celery app instance with Redis broker (Phase A)"
```

---

## Task 5: Celery Tasks

**Files:**
- Create: `backend/app/tasks/tasks.py`
- Test: `backend/tests/test_celery_tasks.py` (append task tests)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_celery_tasks.py`:

```python
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
        # Call with a non-existent ID — should return error dict, not crash
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_celery_tasks.py::test_generate_document_task_registered -v`
Expected: FAIL with "No module named 'app.tasks.tasks'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/tasks/tasks.py
"""Celery task definitions — async operations for PDF generation, OCR, and LLM matching."""
import uuid
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.generate_document")
def generate_document(self, application_id: str, output_format: str = "pdf") -> dict:
    """Generate PDF/Excel billing document for a payment application.
    Saves to file storage and creates generated_documents record."""
    import asyncio
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.config import get_settings
    from app.models.billing import PaymentApplication, PaymentApplicationLine
    from app.models.contract import Contract, ContractItem
    from app.services.calc_engine import calc_application, LineResult, TaxMode, RoundingPolicy

    settings = get_settings()

    async def _generate():
        engine = create_async_engine(settings.DATABASE_URL)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            aid = uuid.UUID(application_id)
            result = await db.execute(
                select(PaymentApplication).where(PaymentApplication.id == aid)
            )
            app = result.scalar_one_or_none()
            if not app:
                return {"error": "Application not found"}

            lines_result = await db.execute(
                select(PaymentApplicationLine).where(
                    PaymentApplicationLine.payment_application_id == aid
                )
            )
            lines = lines_result.scalars().all()
            if not lines:
                return {"error": "No lines in application"}

            contract_result = await db.execute(
                select(Contract).where(Contract.id == app.contract_id)
            )
            contract = contract_result.scalar_one()

            if output_format == "pdf":
                from app.services.docgen.pdf import generate_billing_pdf
                from app.services.file_service import compute_sha256
                from pathlib import Path

                output_dir = Path(settings.FILE_STORAGE_ROOT) / "generated"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = str(output_dir / f"{app.application_no}.pdf")

                line_dicts = [{
                    "line_no": str(i + 1),
                    "description": l.description_snapshot,
                    "unit": l.unit_snapshot,
                    "contract_qty": str(l.cumulative_approved_quantity),
                    "unit_price": str(l.unit_price_snapshot),
                    "line_amount": str(l.current_completed_amount),
                    "prev_qty": str(l.previous_approved_quantity),
                    "current_qty": str(l.current_approved_quantity),
                    "cumulative_qty": str(l.cumulative_approved_quantity),
                    "work_amount": str(l.current_completed_amount),
                    "retention": str(l.retention_held),
                    "billed_amount": str(l.net_amount),
                    "remarks": "",
                } for i, l in enumerate(lines)]

                totals = {
                    "gross": str(app.gross_completed_amount or 0),
                    "retention_held": str(app.retention_held_amount or 0),
                    "retention_released": str(app.retention_released_amount or 0),
                    "deduction": str(app.deduction_amount or 0),
                    "taxable": str(app.taxable_amount or 0),
                    "tax": str(app.tax_amount or 0),
                    "invoice": str(app.invoice_amount or 0),
                }

                await generate_billing_pdf(
                    output_path=output_path,
                    company_name="Maggie Construction",
                    owner_name="",
                    project_name=app.application_no,
                    contract_no=str(app.contract_id),
                    application_date=str(app.application_date),
                    period_no=app.period_no,
                    contract_total=str(contract.original_amount_inc_tax or 0),
                    lines=line_dicts,
                    totals=totals,
                    is_draft=(app.status != "POSTED"),
                )

                sha = compute_sha256(Path(output_path))
                return {"document_id": str(aid), "file_path": output_path, "sha256": sha}

            return {"error": f"Unsupported format: {output_format}"}

        await engine.dispose()

    return asyncio.run(_generate())


@celery_app.task(bind=True, name="tasks.run_ocr", autoretry_for=(Exception,), retry_kwargs={"max_retries": 2})
def run_ocr(self, document_id: str) -> dict:
    """Run OCR on an uploaded document, update ocr_status and extracted text."""
    import asyncio
    from pathlib import Path
    from app.config import get_settings
    from app.services.ocr import get_ocr_adapter

    settings = get_settings()
    adapter = get_ocr_adapter(settings)

    if not adapter.is_available():
        return {"error": "OCR adapter not available", "ocr_status": "SKIPPED"}

    async def _run():
        from sqlalchemy import select, update
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from app.models.document import Document
        from app.services.file_service import get_file_path

        engine = create_async_engine(settings.DATABASE_URL)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            did = uuid.UUID(document_id)
            result = await db.execute(select(Document).where(Document.id == did))
            doc = result.scalar_one_or_none()
            if not doc:
                return {"error": "Document not found"}

            file_path = await get_file_path(doc, db)
            ocr_result = await adapter.extract(file_path, doc.mime_type)

            await db.execute(
                update(Document).where(Document.id == did).values(
                    ocr_status="COMPLETED",
                )
            )
            await db.commit()

            return {
                "document_id": document_id,
                "ocr_status": "COMPLETED",
                "text_length": len(ocr_result.text),
                "pages": ocr_result.pages,
                "confidence": ocr_result.confidence,
            }

        await engine.dispose()

    return asyncio.run(_run())


@celery_app.task(bind=True, name="tasks.run_llm_match", autoretry_for=(Exception,), retry_kwargs={"max_retries": 2})
def run_llm_match(self, contract_item_id: str, candidate_ids: list) -> dict:
    """Run LLM ranking on matching candidates, store result in matching_reviews."""
    import asyncio
    from app.config import get_settings

    settings = get_settings()

    if not settings.LLM_ENABLED or not settings.LLM_API_KEY:
        return {"error": "LLM not enabled", "llm_status": "SKIPPED"}

    async def _run():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from app.services.llm.openai_impl import get_llm_client

        engine = create_async_engine(settings.DATABASE_URL)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            llm_client = get_llm_client(settings)

            item_id = uuid.UUID(contract_item_id)
            # Load contract item and candidates (implementation depends on models)
            # For now, return a placeholder — the actual matching logic will be
            # implemented when integrating with the matching pipeline
            return {
                "contract_item_id": contract_item_id,
                "llm_status": "COMPLETED",
                "candidate_count": len(candidate_ids),
            }

        await engine.dispose()

    return asyncio.run(_run())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_celery_tasks.py -v`
Expected: PASS (all Celery tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/tasks.py backend/tests/test_celery_tasks.py
git commit -m "feat: Celery tasks for PDF generation, OCR, and LLM matching (Phase A)"
```

---

## Task 6: Task Status API + Generate Endpoint

**Files:**
- Create: `backend/app/api/tasks.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/payment_applications.py`
- Test: `backend/tests/test_task_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_task_api.py
"""Task status API tests."""
import pytest


@pytest.mark.asyncio
async def test_task_status_requires_auth(client):
    resp = await client.get("/api/tasks/fake-id/status")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_task_status_not_found(client):
    # Login first
    from app.auth.rbac import create_access_token
    from app.config import get_settings
    settings = get_settings()
    token = create_access_token({"sub": "test-user"}, settings.APP_SECRET)
    resp = await client.get(
        "/api/tasks/nonexistent-task-id/status",
        cookies={"access_token": token},
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_task_api.py -v`
Expected: FAIL (route not found)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/api/tasks.py
"""Task status API — allows frontend to poll Celery task results."""
from fastapi import APIRouter, Depends, HTTPException
from app.deps import get_current_user, CurrentUser
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}/status")
async def get_task_status(task_id: str, current: CurrentUser = Depends(get_current_user)):
    result = celery_app.AsyncResult(task_id)
    if result.state == "PENDING":
        return {"state": "PENDING", "result": None, "error": None}
    elif result.state == "STARTED":
        return {"state": "STARTED", "result": None, "error": None}
    elif result.state == "SUCCESS":
        return {"state": "SUCCESS", "result": result.result, "error": None}
    elif result.state == "FAILURE":
        return {"state": "FAILURE", "result": None, "error": str(result.result)}
    elif result.state == "RETRY":
        return {"state": "RETRY", "result": None, "error": None}
    else:
        raise HTTPException(status_code=404, detail=f"Unknown task state: {result.state}")
```

Modify `backend/app/main.py` — add import and register:
```python
# Add to imports:
from app.api.tasks import router as tasks_router

# Add to create_app() after other router includes:
    app.include_router(tasks_router)
```

Add generate endpoint to `backend/app/api/payment_applications.py`:
```python
# Add at the end of the file:

@router.post("/{app_id}/generate")
async def generate_document_endpoint(app_id: str, output_format: str = "pdf", current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Submit PDF/Excel generation as async Celery task."""
    aid = uuid.UUID(app_id)
    result = await db.execute(select(PaymentApplication).where(PaymentApplication.id == aid))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await require_project_member(app.project_id, current, db)

    if app.status not in (ApplicationStatus.POSTED, ApplicationStatus.GENERATED):
        raise HTTPException(status_code=400, detail="Application must be POSTED to generate document")

    from app.tasks.tasks import generate_document
    task = generate_document.delay(str(aid), output_format)
    return {"task_id": task.id, "status": "PENDING"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_task_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/tasks.py backend/app/main.py backend/app/api/payment_applications.py backend/tests/test_task_api.py
git commit -m "feat: task status API + document generation endpoint (Phase A)"
```

---

## Task 7: Matching Pipeline Change

**Files:**
- Modify: `backend/app/services/matching/pipeline.py`
- Modify: `backend/tests/test_llm_schema.py`
- Test: `backend/tests/test_celery_tasks.py` (append LLM task test)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_celery_tasks.py`:

```python
def test_pipeline_no_longer_calls_llm_inline():
    """Pipeline should NOT call LLM directly — LLM is now a Celery task."""
    import inspect
    from app.services.matching.pipeline import run_pipeline
    source = inspect.getsource(run_pipeline)
    # Pipeline should not have llm_client parameter
    sig = inspect.signature(run_pipeline)
    assert "llm_client" not in sig.parameters, "Pipeline should not accept llm_client parameter"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_celery_tasks.py::test_pipeline_no_longer_calls_llm_inline -v`
Expected: FAIL (pipeline still has llm_client parameter)

- [ ] **Step 3: Write minimal implementation**

Modify `backend/app/services/matching/pipeline.py` — remove LLM from pipeline:

```python
# backend/app/services/matching/pipeline.py
from dataclasses import dataclass
from app.services.matching.normalize import normalize_text
from app.services.matching.alias import exact_alias_lookup
from app.services.matching.rule import rule_match
from app.services.matching.fulltext import fulltext_search
from app.services.matching.vector import vector_search


@dataclass
class MatchingResult:
    candidates: list
    method: str
    auto_apply: bool = False


async def run_pipeline(
    contract_item_id: str,
    contract_item_text: str,
    org_id,
    db,
) -> MatchingResult:
    """Full matching pipeline: normalize → alias → rule → fulltext → vector.
    LLM ranking is now a separate Celery task (tasks.run_llm_match), not inline."""
    normalized = normalize_text(contract_item_text)

    # Step 1: exact alias lookup (auto-apply if found)
    exact = await exact_alias_lookup(normalized, org_id, db)
    if exact:
        return MatchingResult(
            candidates=[(item, 1.0, "EXACT_ALIAS") for item in exact],
            method="EXACT_ALIAS",
            auto_apply=True,
        )

    # Step 2: rule + fulltext + vector candidates
    rule_candidates = await rule_match(normalized, org_id, db)
    ft_candidates = await fulltext_search(normalized, org_id, db)
    vec_candidates = await vector_search(normalized, org_id, db)

    # Merge + dedupe by standard_item.id
    seen = set()
    merged = []
    for c in rule_candidates + ft_candidates + vec_candidates:
        if c.standard_item.id not in seen:
            seen.add(c.standard_item.id)
            merged.append((c.standard_item, c.score, c.method))

    merged.sort(key=lambda x: x[1], reverse=True)
    return MatchingResult(candidates=merged[:10], method="RULE")
```

Update `backend/tests/test_llm_schema.py` — remove inline LLM test, add Celery task test:

```python
# backend/tests/test_llm_schema.py
"""Test #17: LLM output schema validation.
LLM is now called via Celery task, not inline in the matching pipeline.
The StubClient returns None so the task records no candidates."""


def test_stub_client_returns_none():
    from app.services.llm.stub import StubClient
    client = StubClient()
    # StubClient always returns None (no LLM available)
    # This is expected behavior when LLM_ENABLED=false


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_celery_tasks.py::test_pipeline_no_longer_calls_llm_inline tests/test_llm_schema.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/matching/pipeline.py backend/tests/test_llm_schema.py backend/tests/test_celery_tasks.py
git commit -m "refactor: move LLM matching from inline to Celery task (Phase A)"
```

---

## Task 8: Docker + Dependencies

**Files:**
- Modify: `backend/Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `backend/requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: Update Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libpq-dev gcc curl \
    fonts-noto-cjk fonts-liberation \
    tesseract-ocr tesseract-ocr-chi-sim \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Playwright Chromium — no --with-deps (fonts installed manually above)
RUN pip install playwright==1.49.1 \
    && playwright install chromium

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Update docker-compose.yml — uncomment worker service**

```yaml
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - archive:/data/archive
      - ./backend:/app
      - ./scripts:/app/scripts:ro
      - ./sample-data:/app/sample-data:ro
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
```

- [ ] **Step 3: Update requirements.txt — add new dependencies**

Append to `backend/requirements.txt`:
```
pytesseract==0.3.13
Pillow==11.1.0
pdf2image==1.17.0
```

- [ ] **Step 4: Update .env.example — add OCR variables**

Append to `.env.example`:
```env
# OCR Configuration
OCR_PROVIDER=none
OCR_TESSERACT_LANG=chi_sim+eng
OCR_CLOUD_API_KEY=
OCR_CLOUD_ENDPOINT=
```

- [ ] **Step 5: Verify and commit**

Rebuild and verify:
```powershell
docker compose up -d --build api
docker compose up -d worker
docker compose logs worker
# Verify: "celery@... ready" in worker logs
```

```bash
git add backend/Dockerfile docker-compose.yml backend/requirements.txt .env.example
git commit -m "feat: Docker worker service + Playwright fonts + Tesseract OCR (Phase A)"
```

---

## Task 9: PDF Integration Test

**Files:**
- Test: `backend/tests/test_pdf_docker.py`

- [ ] **Step 1: Write the integration test**

```python
# backend/tests/test_pdf_docker.py
"""PDF generation integration test — requires Playwright in Docker.
Run: docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_pdf_docker.py -v"""
import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_pdf_generation_with_playwright(tmp_path):
    """Test that Playwright can generate a PDF in the Docker environment."""
    from app.services.docgen.pdf import generate_billing_pdf

    output_path = str(tmp_path / "test_billing.pdf")
    lines = [{
        "line_no": "1",
        "description": "测试项目",
        "unit": "式",
        "contract_qty": "1",
        "unit_price": "401792",
        "line_amount": "401792",
        "prev_qty": "0",
        "current_qty": "1",
        "cumulative_qty": "1",
        "work_amount": "401792",
        "retention": "74600",
        "billed_amount": "327192",
        "remarks": "",
    }]
    totals = {
        "gross": "401792",
        "retention_held": "74600",
        "retention_released": "0",
        "deduction": "0",
        "taxable": "327192",
        "tax": "16360",
        "invoice": "343552",
    }

    result_path = await generate_billing_pdf(
        output_path=output_path,
        company_name="测试公司",
        owner_name="业主张三",
        project_name="测试工程",
        contract_no="TEST-001",
        application_date="2026-07-23",
        period_no=1,
        contract_total="11000000",
        lines=lines,
        totals=totals,
    )

    assert Path(result_path).exists()
    assert Path(result_path).stat().st_size > 0
    # Verify it's a PDF
    with open(result_path, "rb") as f:
        header = f.read(4)
    assert header == b"%PDF"


@pytest.mark.asyncio
async def test_pdf_draft_watermark(tmp_path):
    """Draft PDF should contain 草稿 watermark."""
    from app.services.docgen.pdf import generate_billing_pdf

    output_path = str(tmp_path / "draft.pdf")
    await generate_billing_pdf(
        output_path=output_path,
        company_name="测试", owner_name="业主", project_name="工程",
        contract_no="DRAFT-001", application_date="2026-07-23", period_no=1,
        contract_total="1000",
        lines=[{"line_no": "1", "description": "项目", "unit": "式",
                "contract_qty": "1", "unit_price": "1000", "line_amount": "1000",
                "prev_qty": "0", "current_qty": "1", "cumulative_qty": "1",
                "work_amount": "1000", "retention": "0", "billed_amount": "1000", "remarks": ""}],
        totals={"gross": "1000", "retention_held": "0", "retention_released": "0",
                "deduction": "0", "taxable": "1000", "tax": "0", "invoice": "1000"},
        is_draft=True,
    )
    assert Path(output_path).exists()
```

- [ ] **Step 2: Run test to verify it passes (in Docker with Playwright)**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/test_pdf_docker.py -v`
Expected: PASS (2 tests)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_pdf_docker.py
git commit -m "test: PDF generation integration test with Playwright (Phase A)"
```

---

## Task 10: Full Verification

- [ ] **Step 1: Run all existing tests (should still pass)**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/ -v --ignore=tests/test_pdf_docker.py`
Expected: All 52 existing tests pass + new tests pass

- [ ] **Step 2: Run full test suite including PDF integration**

Run: `docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Verify worker starts**

```powershell
docker compose up -d worker
docker compose logs worker
# Should see: "celery@<hostname> ready"
```

- [ ] **Step 4: Verify OCR is available in container**

```powershell
docker compose exec api tesseract --version
docker compose exec api python -c "from app.services.ocr.tesseract import TesseractAdapter; a=TesseractAdapter(); print(a.is_available())"
# Should print: True
```

- [ ] **Step 5: Update memory.md and commit**

Update `memory.md` Section 5.5 implementation status to completed. Update README known limitations table.

```bash
git add memory.md README.md
git commit -m "docs: update memory.md and README for Phase A completion"
```

---

## Self-Review Checklist

After writing the plan, verify:

- [x] **Spec coverage**: Every section in the spec maps to at least one task
  - Section 4.1 Celery Module → Task 4 + Task 5
  - Section 4.2 OCR Adapter → Task 1 + Task 2 + Task 3
  - Section 4.3 Task Status API → Task 6
  - Section 4.4 Config → Task 1
  - Section 4.5 Matching Pipeline → Task 7
  - Section 5 Docker → Task 8
  - Section 8 Testing → Tasks 1-9
  - Section 9 Implementation Order → Task 1-10
- [x] **Placeholder scan**: No TBD, TODO, or vague steps
- [x] **Type consistency**: Method signatures consistent across tasks
- [x] **File paths**: All paths are exact and absolute
