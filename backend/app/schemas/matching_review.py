from pydantic import BaseModel


class MatchingReviewCreate(BaseModel):
    project_id: str
    item_mapping_id: str | None = None
    contract_item_id: str
    review_type: str
    candidate_mappings: dict | None = None
    notes: str | None = None


class MatchingReviewResponse(BaseModel):
    id: str
    project_id: str
    item_mapping_id: str | None
    contract_item_id: str
    review_type: str
    candidate_mappings: dict | None
    reviewer_id: str | None
    decision: str | None
    notes: str | None
    status: str


class MatchingReviewDecide(BaseModel):
    decision: str
    notes: str | None = None
