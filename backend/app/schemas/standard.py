import uuid
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class StandardItemCreate(BaseModel):
    code: str
    name: str
    category: str | None = None
    unit: str | None = None
    description: str | None = None
    is_active: bool = True
    sort_order: int = 0


class StandardItemResponse(BaseModel):
    id: str
    code: str
    name: str
    category: str | None
    unit: str | None
    description: str | None
    is_active: bool
    sort_order: int
    latest_unit_cost: Decimal | None = None


class StandardItemAliasCreate(BaseModel):
    alias_text: str
    alias_source: str = "MANUAL"
    is_approved: bool = False


class StandardItemAliasResponse(BaseModel):
    id: str
    standard_item_id: str
    alias_text: str
    alias_source: str
    is_approved: bool
    approved_by: str | None
    approved_at: date | None


class StandardCostVersionCreate(BaseModel):
    version_no: int
    effective_from: date | None = None
    effective_to: date | None = None
    unit_cost: Decimal = Decimal("0")
    cost_basis: str = "STANDARD"
    source: str | None = None
    notes: str | None = None
    status: str = "ACTIVE"


class StandardCostVersionResponse(BaseModel):
    id: str
    standard_item_id: str
    version_no: int
    effective_from: date | None
    effective_to: date | None
    unit_cost: Decimal
    cost_basis: str
    source: str | None
    notes: str | None
    status: str
