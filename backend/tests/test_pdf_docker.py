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
