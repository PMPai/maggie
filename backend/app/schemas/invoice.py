from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class InvoiceCreate(BaseModel):
    project_id: str
    contract_id: str
    invoice_no: str
    invoice_type: str = "STANDARD"
    issue_date: date | None = None
    due_date: date | None = None
    amount_ex_tax: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    amount_inc_tax: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0.05")
    source: str = "MANUAL"
    notes: str | None = None


class InvoiceResponse(BaseModel):
    id: str
    project_id: str
    contract_id: str
    invoice_no: str
    invoice_type: str
    issue_date: date | None
    due_date: date | None
    amount_ex_tax: Decimal
    tax_amount: Decimal
    amount_inc_tax: Decimal
    tax_rate: Decimal
    status: str
    source: str
    notes: str | None


class InvoiceLinkCreate(BaseModel):
    payment_application_id: str
    linked_amount: Decimal


class InvoiceLinkResponse(BaseModel):
    id: str
    invoice_id: str
    payment_application_id: str
    linked_amount: Decimal
