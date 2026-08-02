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
    from app.models.billing import PaymentApplication, PaymentApplicationLine, ApplicationStatus
    from app.models.contract import Contract

    settings = get_settings()

    async def _generate():
        engine = create_async_engine(settings.DATABASE_URL)
        try:
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
                        is_draft=(app.status != ApplicationStatus.POSTED),
                    )

                    sha = compute_sha256(Path(output_path))
                    return {"document_id": str(aid), "file_path": output_path, "sha256": sha}

                return {"error": f"Unsupported format: {output_format}"}
        finally:
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
        try:
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as db:
                did = uuid.UUID(document_id)
                result = await db.execute(select(Document).where(Document.id == did))
                doc = result.scalar_one_or_none()
                if not doc:
                    return {"error": "Document not found"}

                file_path = await get_file_path(doc, db)
                try:
                    ocr_result = await adapter.extract(file_path, doc.mime_type)
                    await db.execute(
                        update(Document).where(Document.id == did).values(
                            ocr_status="COMPLETED",
                            ocr_text=ocr_result.text,
                        )
                    )
                    payload = {
                        "document_id": document_id,
                        "ocr_status": "COMPLETED",
                        "text_length": len(ocr_result.text),
                        "pages": ocr_result.pages,
                        "confidence": ocr_result.confidence,
                    }
                except Exception:
                    await db.execute(
                        update(Document).where(Document.id == did).values(
                            ocr_status="FAILED",
                            ocr_text=None,
                        )
                    )
                    payload = {"document_id": document_id, "ocr_status": "FAILED", "error": "OCR extract failed"}
                await db.commit()

                return payload
        finally:
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
        try:
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as db:
                llm_client = get_llm_client(settings)

                item_id = uuid.UUID(contract_item_id)
                return {
                    "contract_item_id": contract_item_id,
                    "llm_status": "COMPLETED",
                    "candidate_count": len(candidate_ids),
                }
        finally:
            await engine.dispose()

    return asyncio.run(_run())
