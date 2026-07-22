from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class CollectionCreate(BaseModel):
    project_id: str
    contract_id: str
    receipt_no: str
    receipt_date: date | None = None
    amount_received: Decimal
    payment_method: str = "BANK_TRANSFER"
    bank_reference: str | None = None
    notes: str | None = None
    status: str = "CONFIRMED"


class CollectionResponse(BaseModel):
    id: str
    project_id: str
    contract_id: str
    receipt_no: str
    receipt_date: date | None
    amount_received: Decimal
    payment_method: str
    bank_reference: str | None
    notes: str | None
    status: str


class CollectionAllocationCreate(BaseModel):
    invoice_id: str
    allocated_amount: Decimal


class CollectionAllocationResponse(BaseModel):
    id: str
    collection_id: str
    invoice_id: str
    allocated_amount: Decimal
