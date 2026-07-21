import os
from pathlib import Path
from decimal import Decimal
from jinja2 import Template
from playwright.async_api import async_playwright

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent.parent / "templates"


async def generate_billing_pdf(
    output_path: str,
    company_name: str,
    owner_name: str,
    project_name: str,
    contract_no: str,
    application_date: str,
    period_no: int,
    contract_total: str,
    lines: list[dict],
    totals: dict,
    is_draft: bool = False,
) -> str:
    """Generate A4 printable PDF billing document via Playwright headless Chromium."""
    template_path = TEMPLATES_DIR / "billing" / "default.html"
    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    template = Template(template_str)
    html = template.render(
        company_name=company_name, owner_name=owner_name, project_name=project_name,
        contract_no=contract_no, application_date=application_date, period_no=period_no,
        contract_total=contract_total, lines=lines, totals=totals,
    )

    if is_draft:
        html = html.replace("<body>", '<body><div style="position:fixed;top:40px;right:30px;font-size:36pt;color:rgba(255,0,0,0.15);transform:rotate(-30deg);font-weight:bold;z-index:9999;">草稿 DRAFT</div>')

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        await page.pdf(path=output_path, format="A4", print_background=True, margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"})
        await browser.close()

    return output_path
