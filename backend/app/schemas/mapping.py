from decimal import Decimal
from pydantic import BaseModel


class ItemMappingCreate(BaseModel):
    project_id: str
    contract_item_id: str
    standard_item_id: str
    mapping_type: str = "ONE_TO_ONE"
    match_method: str = "MANUAL"
    unit_compatibility: str = "SAME"
    conversion_factor: Decimal = Decimal("1")
    confidence: Decimal | None = None
    status: str = "SUGGESTED"
    llm_reasoning: str | None = None
    llm_output: dict | None = None


class ItemMappingResponse(BaseModel):
    id: str
    project_id: str
    contract_item_id: str
    standard_item_id: str
    mapping_type: str
    match_method: str
    unit_compatibility: str
    conversion_factor: Decimal
    confidence: Decimal | None
    status: str
    approved_by: str | None
    approved_at: str | None
    llm_reasoning: str | None
    llm_output: dict | None


class MappingComponentCreate(BaseModel):
    item_mapping_id: str
    contract_item_id: str
    standard_item_id: str
    component_ratio: Decimal = Decimal("1")


class MappingComponentResponse(BaseModel):
    id: str
    item_mapping_id: str
    contract_item_id: str
    standard_item_id: str
    component_ratio: Decimal
