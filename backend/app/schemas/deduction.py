import uuid
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class DeductionCreate(BaseModel):
    project_id: str
    contract_id: str
    payment_application_id: str | None = None
    deduction_no: str
    deduction_type: str
    description: str | None = None
    reason: str | None = None
    amount: Decimal
    tax_treatment: str = "TAXABLE"
    tax_amount: Decimal = Decimal("0")
    effective_date: date | None = None


class DeductionResponse(BaseModel):
    id: str
    project_id: str
    contract_id: str
    payment_application_id: str | None
    deduction_no: str
    deduction_type: str
    description: str | None
    reason: str | None
    amount: Decimal
    tax_treatment: str
    tax_amount: Decimal
    effective_date: date | None
    status: str
    approved_by: str | None
    approved_at: date | None
