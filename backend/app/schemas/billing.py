from datetime import date
from decimal import Decimal
from pydantic import BaseModel, UUID4


class ApplicationLineCreate(BaseModel):
    contract_item_id: str
    current_claimed_quantity: Decimal
    current_approved_quantity: Decimal
    user_explanation: str | None = None
    direct_amount: Decimal | None = None


class ApplicationCreate(BaseModel):
    project_id: str
    contract_id: str
    application_no: str
    period_no: int
    period_start: date
    period_end: date
    application_date: date


class ApplicationLineResponse(BaseModel):
    id: str
    contract_item_id: str
    description_snapshot: str
    unit_snapshot: str | None
    unit_price_snapshot: Decimal
    previous_approved_quantity: Decimal
    current_claimed_quantity: Decimal
    current_approved_quantity: Decimal
    cumulative_approved_quantity: Decimal
    current_completed_amount: Decimal
    retention_held: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    net_amount: Decimal
    validation_status: str


class ApplicationResponse(BaseModel):
    id: UUID4
    project_id: UUID4
    contract_id: UUID4
    application_no: str
    period_no: int
    status: str
    created_by: UUID4 | None = None
    gross_completed_amount: Decimal
    retention_held_amount: Decimal
    retention_released_amount: Decimal
    deduction_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    invoice_amount: Decimal


class PostRequest(BaseModel):
    action_id: str  # idempotency key


class PreviewLineInput(BaseModel):
    contract_item_id: str
    current_claimed_quantity: Decimal
    current_approved_quantity: Decimal | None = None
    direct_amount: Decimal | None = None


class PreviewRequest(BaseModel):
    contract_id: str
    lines: list[PreviewLineInput]
