import uuid
from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class ContractCreate(BaseModel):
    project_id: str
    external_contract_no: str
    contract_name: str
    customer_company_id: str | None = None
    contractor_company_id: str | None = None
    signed_date: date | None = None
    effective_date: date | None = None
    currency: str = "TWD"
    tax_mode: str = "EXCLUSIVE"
    tax_rate: Decimal = Decimal("0.05")
    rounding_policy: str = "ROUND_HALF_UP"
    rounding_granularity: Decimal = Decimal("1")


class ContractResponse(BaseModel):
    id: str
    project_id: str
    external_contract_no: str
    contract_name: str
    currency: str
    tax_mode: str
    tax_rate: Decimal
    original_amount_ex_tax: Decimal
    original_tax_amount: Decimal
    original_amount_inc_tax: Decimal
    status: str
    active_version_id: str | None


class ContractVersionCreate(BaseModel):
    version_type: str
    effective_date: date | None = None
    amount_ex_tax: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    amount_inc_tax: Decimal = Decimal("0")
    change_reason: str | None = None


class ContractVersionResponse(BaseModel):
    id: str
    contract_id: str
    version_no: int
    version_type: str
    amount_ex_tax: Decimal
    tax_amount: Decimal
    amount_inc_tax: Decimal
    status: str
    change_reason: str | None
    source_document_id: str | None = None


class ContractVersionPatch(BaseModel):
    external_contract_no: str | None = None
    contract_name: str | None = None
    signed_date: date | None = None
    effective_date: date | None = None
    currency: str | None = None
    tax_mode: str | None = None
    tax_rate: Decimal | None = None
    original_amount_ex_tax: Decimal | None = None
    original_tax_amount: Decimal | None = None
    original_amount_inc_tax: Decimal | None = None
    amount_ex_tax: Decimal | None = None
    tax_amount: Decimal | None = None
    amount_inc_tax: Decimal | None = None
    change_reason: str | None = None
    status: str | None = None


class ContractItemPatch(BaseModel):
    line_no: str | None = None
    source_description: str | None = None
    unit: str | None = None
    contract_quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_amount: Decimal | None = None
    calculation_method: str | None = None
    tax_category: str | None = None
    retention_applicable: bool | None = None
    expected_payment_date: date | None = None
    actual_payment_date: date | None = None


class ContractItemCreate(BaseModel):
    parent_item_id: str | None = None
    line_no: str
    item_code: str | None = None
    source_description: str
    normalized_description: str | None = None
    unit: str | None = None
    contract_quantity: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    line_amount: Decimal = Decimal("0")
    calculation_method: str = "QUANTITY"
    tax_category: str = "STANDARD"
    retention_applicable: bool = True
    is_heading: bool = False
    is_billable: bool = True
    sort_order: int = 0


class ContractItemResponse(BaseModel):
    id: str
    contract_version_id: str
    parent_item_id: str | None
    line_no: str
    item_code: str | None
    source_description: str
    unit: str | None
    contract_quantity: Decimal
    unit_price: Decimal
    line_amount: Decimal
    calculation_method: str
    is_heading: bool
    is_billable: bool
    retention_applicable: bool
    sort_order: int


class PaymentRuleCreate(BaseModel):
    contract_item_id: str | None = None
    rule_type: str
    rule_name: str
    rate: Decimal
    calculation_base: str = "CURRENT_PERIOD"
    condition_code: str | None = None
    condition_description: str | None = None
    release_sequence: int | None = None


class PaymentRuleResponse(BaseModel):
    id: str
    contract_version_id: str
    contract_item_id: str | None
    rule_type: str
    rule_name: str
    rate: Decimal
    calculation_base: str
    is_active: bool
