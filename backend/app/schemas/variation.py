import uuid
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class VariationLineCreate(BaseModel):
    contract_item_id: str
    quantity_delta: Decimal = Decimal("0")
    unit_price_new: Decimal | None = None
    amount_delta: Decimal = Decimal("0")
    description: str | None = None


class VariationLineResponse(BaseModel):
    id: str
    variation_id: str
    contract_item_id: str
    quantity_delta: Decimal
    unit_price_new: Decimal | None
    amount_delta: Decimal
    description: str | None


class VariationCreate(BaseModel):
    project_id: str
    contract_id: str
    contract_item_id: str | None = None
    variation_no: str
    variation_type: str
    description: str | None = None
    reason: str | None = None
    amount_ex_tax: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    amount_inc_tax: Decimal = Decimal("0")
    quantity_delta: Decimal = Decimal("0")
    effective_date: date | None = None
    source_document_id: str | None = None


class VariationResponse(BaseModel):
    id: str
    project_id: str
    contract_id: str
    contract_item_id: str | None
    variation_no: str
    variation_type: str
    description: str | None
    reason: str | None
    amount_ex_tax: Decimal
    tax_amount: Decimal
    amount_inc_tax: Decimal
    quantity_delta: Decimal
    effective_date: date | None
    status: str
    approved_by: str | None
    approved_at: date | None
