# Phase A: Celery Worker + PDF Generation Fix + OCR Adapter

**Date**: 2026-07-23  
**Status**: Design approved, ready for implementation plan  
**Scope**: A1 (Celery) + A2 (PDF fix) + A3 (OCR) — all three together

---

## 1. Problem Statement

The Maggie system has completed Phase 1-3 with 52 passing tests, but three critical backend gaps remain:

1. **Celery Worker** — `celery==5.4.0` is in requirements.txt but no `app/tasks/` module exists. The worker service in docker-compose.yml is commented out. Async tasks (PDF generation, OCR, LLM matching) cannot run.

2. **PDF Generation** — `pdf.py` uses Playwright headless Chromium to render Jinja2 HTML templates to A4 PDF. Playwright install is commented out in the Dockerfile because `--with-deps` tries to install `ttf-unifont`/`ttf-ubuntu-font-family` which are no longer available in Debian 12. PDF generation fails at runtime in Docker.

3. **OCR** — `ocr/adapter.py` is a stub that returns empty results (`text=""`, `confidence=0.0`, `is_available()=False`). Historical file import with OCR extraction is non-functional.

## 2. Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| PDF approach | Fix Playwright + manual fonts | Keeps Chromium rendering quality; `pdf.py` code unchanged; honors spec's "headless Chromium" |
| OCR approach | Tesseract default + pluggable cloud | Self-hosted, free, supports Chinese (`chi_sim`), privacy-safe; cloud via config |
| Celery scope | Pragmatic: PDF + OCR + LLM as Celery tasks, file hash stays synchronous | File hash is fast (<1s for 100MB); adding it to Celery introduces "hash pending" state for near-zero benefit |
| Task feedback | Polling (not WebSocket/SSE) | Simpler; tasks complete in 3-30s; polling with exponential backoff (1s→5s cap) |

## 3. Architecture

```
Frontend (Next.js) ──▶ FastAPI (API) ──▶ PostgreSQL
                           │
                           │ submit task (.delay)
                           ▼
                    Redis (broker + backend) ◀──▶ Celery Worker
                                                  │
                                       ┌──────────┼──────────┐
                                       ▼          ▼          ▼
                                 Playwright   Tesseract   LLM API
                                 (PDF gen)    (OCR)       (httpx)
```

### 3.1 Three Async Task Flows

**PDF/Excel Generation**:
1. `POST /payment-applications/{id}/generate` — API validates application is POSTED, submits `generate_document.delay(app_id, format)`, returns `{task_id, status: "PENDING"}`
2. Worker loads application + lines, calls `calc_engine`, renders HTML template, Playwright generates PDF, saves to `/data/archive`, creates `generated_documents` record
3. Frontend polls `GET /tasks/{task_id}/status` until SUCCESS, then previews/downloads via `/documents/{doc_id}/preview`

**OCR Extraction**:
1. File uploaded via `POST /documents/upload` — if file is image/PDF and `OCR_PROVIDER != "none"`, API submits `run_ocr.delay(document_id)`
2. Worker calls `OCRAdapter.extract(file_path, mime_type)`, updates `documents.ocr_status` and stores extracted text
3. Frontend polls document status

**LLM Matching**:
1. User triggers matching — pipeline runs `normalize → alias → rule → fulltext → vector`, returns candidates immediately
2. If `LLM_ENABLED=true` and candidates exist, API submits `run_llm_match.delay(item_id, candidate_ids)`
3. Worker calls `llm_client.rank_candidates(text, candidates)`, stores result in `matching_reviews`
4. Frontend shows candidates immediately, displays "LLM 排序中" indicator, polls for enriched results

## 4. Component Design

### 4.1 Celery Module

```
backend/app/tasks/
├── __init__.py          # exports celery_app
├── celery_app.py        # Celery instance + configuration
└── tasks.py             # 3 task definitions
```

**`celery_app.py`**:
```python
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

**`tasks.py`** — 3 tasks:
```python
@celery_app.task(bind=True, name="tasks.generate_document")
def generate_document(self, application_id: str, output_format: str = "pdf") -> dict:
    """Generate PDF/Excel via docgen, save to file storage, create generated_documents record.
    No retry — requires user confirmation to regenerate."""

@celery_app.task(bind=True, name="tasks.run_ocr", autoretry_for=(Exception,))
def run_ocr(self, document_id: str) -> dict:
    """Run OCR via OCRAdapter.extract(), update documents.ocr_status and extracted text.
    Auto-retry on transient failures."""

@celery_app.task(bind=True, name="tasks.run_llm_match", autoretry_for=(Exception,))
def run_llm_match(self, contract_item_id: str, candidate_ids: list[str]) -> dict:
    """Call LLM rank_candidates, store result in matching_reviews.
    Auto-retry on transient failures."""
```

Each task uses `bind=True` to access `self.request.id` (task_id). Returns dict with result summary.

### 4.2 OCR Adapter Redesign

```
backend/app/services/ocr/
├── __init__.py           # get_ocr_adapter() factory
├── protocol.py           # OCRAdapter protocol + OCRResult dataclass
├── tesseract.py          # TesseractAdapter (pytesseract + Pillow + pdf2image)
├── cloud.py              # CloudOCRAdapter stub (for future Google Vision/Azure)
└── stub.py               # StubOCRAdapter (default when OCR unavailable)
```

**`protocol.py`**:
```python
from typing import Protocol
from dataclasses import dataclass

@dataclass
class OCRResult:
    text: str
    confidence: float
    pages: int
    bbox_data: list  # list of {text, bbox, page} dicts

class OCRAdapter(Protocol):
    async def extract(self, file_path: Path, mime_type: str = "application/pdf") -> OCRResult: ...
    def is_available(self) -> bool: ...
```

**`tesseract.py`**:
- Uses `pytesseract.image_to_string()` + `pytesseract.image_to_data()` for bbox
- PDF files: `pdf2image.convert_from_path()` to split into page images, OCR each page
- `is_available()`: checks `shutil.which("tesseract")` exists

**Factory** (`__init__.py`):
```python
def get_ocr_adapter(settings) -> OCRAdapter:
    provider = settings.OCR_PROVIDER
    if provider == "tesseract":
        from app.services.ocr.tesseract import TesseractAdapter
        return TesseractAdapter(lang=settings.OCR_TESSERACT_LANG)
    elif provider == "cloud":
        from app.services.ocr.cloud import CloudOCRAdapter
        return CloudOCRAdapter(endpoint=settings.OCR_CLOUD_ENDPOINT, api_key=settings.OCR_CLOUD_API_KEY)
    from app.services.ocr.stub import StubOCRAdapter
    return StubOCRAdapter()
```

### 4.3 Task Status API

New file `backend/app/api/tasks.py`:
```python
@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str, user: User = Depends(get_current_user)):
    """Return task state, result, and error info.
    Maps Celery states: PENDING → STARTED → SUCCESS/FAILURE/RETRY.
    Only authenticated users can query (prevents task ID enumeration)."""
```

Register in `main.py`.

### 4.4 Config Changes

`backend/app/config.py` — add to `Settings`:
```python
OCR_PROVIDER: str = "none"        # "tesseract" | "cloud" | "none"
OCR_TESSERACT_LANG: str = "chi_sim+eng"
OCR_CLOUD_API_KEY: str = ""
OCR_CLOUD_ENDPOINT: str = ""
```

### 4.5 Matching Pipeline Change

`backend/app/services/matching/pipeline.py` — after returning non-LLM candidates, if LLM is enabled and candidates exist, submit Celery task instead of calling LLM inline:

```python
# Current: LLM called inline with 30s timeout + fallback
# New: pipeline returns candidates without LLM ranking
#      caller (API layer) submits run_llm_match.delay() if LLM enabled
```

The pipeline's `llm_client` parameter is removed; LLM is now a Celery task, not inline.

## 5. Docker & Dependency Changes

### 5.1 Dockerfile

```dockerfile
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

### 5.2 docker-compose.yml

Uncomment and configure worker service:
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

### 5.3 requirements.txt — New Dependencies

```
pytesseract==0.3.13
Pillow==11.1.0
pdf2image==1.17.0
```

Note: `pdf2image` requires `poppler-utils` system package. Add to Dockerfile apt-get:
```
poppler-utils
```

### 5.4 .env.example — New Variables

```env
# OCR Configuration
OCR_PROVIDER=none
OCR_TESSERACT_LANG=chi_sim+eng
OCR_CLOUD_API_KEY=
OCR_CLOUD_ENDPOINT=
```

## 6. Error Handling & Graceful Degradation

| Scenario | Handling |
|----------|----------|
| Playwright startup failure | Task → FAILURE, error records cause, frontend shows "PDF 生成失败，可重试" |
| OCR file corrupted/unsupported | Task → FAILURE, `documents.ocr_status = "FAILED"`, upload still succeeds |
| LLM API timeout/unreachable | Task → FAILURE, `matching_reviews` records failure, non-LLM candidates still usable |
| Worker crash | `acks_late=True` → task returns to PENDING, auto-retried on worker restart |
| Task timeout (>5min) | `task_time_limit=300` force-terminates, marks FAILURE |
| LLM_ENABLED=false | Pipeline skips LLM step, no Celery task submitted |
| OCR_PROVIDER=none | No OCR task submitted, `ocr_status` stays "SKIPPED" |
| Playwright not installed | API pre-check returns 503 with clear error, no task submitted |

### API Layer Pre-checks

`POST /generate` checks before submitting task:
- Application status is POSTED or GENERATED
- Playwright is importable (quick check)
- If unavailable → 503 + error message (no point submitting a task that will fail)

### Idempotency

- **PDF**: Check for existing `is_final=True` generated_documents record with same parameters. If found, return existing document_id.
- **OCR**: Check `documents.ocr_status` — if already COMPLETED, skip.
- **LLM**: Check `matching_reviews` for unreviewed LLM result for this contract_item.

## 7. Frontend Integration

### Polling Strategy

```typescript
async function pollTask(taskId: string): Promise<TaskResult> {
  let delay = 1000;
  while (true) {
    const res = await api.get(`/tasks/${taskId}/status`);
    if (res.state === 'SUCCESS' || res.state === 'FAILURE') return res;
    await sleep(delay);
    delay = Math.min(delay * 1.5, 5000);
  }
}
```

- PDF: typically 3-5s
- OCR: 10-30s depending on page count
- LLM: 5-15s
- Polling interval caps at 5s

### UI Indicators

- PDF generation: "生成中..." spinner on generate button
- OCR: status badge on document (SKIPPED/PENDING/PROCESSING/COMPLETED/FAILED)
- LLM: "LLM 排序中..." badge on matching candidates panel

## 8. Testing Strategy

### New Test Files

```
backend/tests/
├── test_celery_tasks.py      # Celery task unit tests (eager mode)
├── test_ocr_adapter.py       # OCR adapter tests
├── test_task_api.py          # Task status API tests
└── test_pdf_docker.py        # PDF generation integration test (Docker only)
```

### Test Details

**`test_celery_tasks.py`** — Uses `celery_app.conf.task_always_eager = True`:
- `test_generate_document_task_creates_pdf` — verify generated_documents record + file exists
- `test_run_ocr_task_updates_document` — verify documents.ocr_status updated
- `test_run_llm_match_task_stores_result` — verify matching_reviews record created
- `test_task_failure_on_playwright_error` — task marked FAILURE when Playwright unavailable

**`test_ocr_adapter.py`**:
- `test_stub_adapter_returns_empty` — StubOCRAdapter returns empty, is_available=False
- `test_tesseract_adapter_available` — TesseractAdapter.is_available() checks binary
- `test_tesseract_extract_chinese_text` — Chinese OCR with test image fixture (skip if tesseract not installed)
- `test_get_ocr_adapter_factory` — factory returns correct adapter type per OCR_PROVIDER

**`test_task_api.py`**:
- `test_task_status_requires_auth` — 401 without auth
- `test_task_status_returns_state` — returns PENDING/STARTED/SUCCESS
- `test_task_status_not_found` — 404 for invalid task_id

**`test_pdf_docker.py`**:
- `test_pdf_generation_end_to_end` — full flow: POSTED → submit → poll → SUCCESS → file exists → PDF totals match DB

### Test Execution

```powershell
# Local tests (excluding Docker integration)
docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/ -v --ignore=tests/test_pdf_docker.py

# Full tests (including PDF integration, requires Playwright in Docker)
docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/ -v

# Worker verification
docker compose up -d worker
docker compose logs worker
```

### Existing Tests

All 52 existing tests must continue to pass. The matching pipeline change (removing inline LLM) requires updating `test_llm_schema.py` to test the Celery task instead of inline call.

## 9. Implementation Order

1. **Config** — Add OCR settings to `config.py` + `.env.example`
2. **OCR adapter** — Create protocol, stub, tesseract, cloud, factory
3. **Celery app** — Create `app/tasks/celery_app.py`
4. **Celery tasks** — Create `app/tasks/tasks.py` with 3 tasks
5. **Task status API** — Create `app/api/tasks.py`, register in `main.py`
6. **Matching pipeline** — Remove inline LLM, API submits Celery task
7. **Dockerfile** — Add fonts, tesseract, poppler, Playwright
8. **docker-compose.yml** — Uncomment worker service
9. **requirements.txt** — Add pytesseract, Pillow, pdf2image
10. **Tests** — Write all new test files
11. **Update existing tests** — Fix `test_llm_schema.py` for Celery-based LLM
12. **Verify** — Run all tests, verify worker starts, verify PDF generation in Docker

## 10. Out of Scope

- Frontend UI changes (Phase B)
- E2E tests with Playwright browser (Phase C)
- Cloud OCR actual implementation (stub only, real cloud adapter is future work)
- Multiple Celery queues (single queue sufficient for current scale)
- WebSocket/SSE for real-time task updates (polling is sufficient)
- File hash as Celery task (stays synchronous — fast enough)
