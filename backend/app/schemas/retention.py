from pydantic import BaseModel
from datetime import date
from decimal import Decimal


class RetentionEntryCreate(BaseModel):
    project_id: str
    contract_id: str
    payment_application_id: str | None = None
    contract_item_id: str | None = None
    entry_type: str
    amount: Decimal
    description: str | None = None
    reversal_of_id: str | None = None


class RetentionEntryResponse(BaseModel):
    id: str
    project_id: str
    contract_id: str
    payment_application_id: str | None
    contract_item_id: str | None
    entry_type: str
    amount: Decimal
    description: str | None
    reversal_of_id: str | None
    created_at: str | None = None


class RetentionBalanceResponse(BaseModel):
    contract_id: str
    contract_item_id: str | None
    balance: Decimal
