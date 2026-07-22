from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class FinancialAdjustmentCreate(BaseModel):
    project_id: str
    adjustment_no: str
    adjustment_type: str
    invoice_id: str | None = None
    collection_id: str | None = None
    amount: Decimal
    description: str | None = None
    reason: str | None = None


class FinancialAdjustmentResponse(BaseModel):
    id: str
    project_id: str
    adjustment_no: str
    adjustment_type: str
    invoice_id: str | None
    collection_id: str | None
    amount: Decimal
    description: str | None
    reason: str | None
    status: str
    approved_by: str | None
    approved_at: date | None
