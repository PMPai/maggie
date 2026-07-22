import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_project_member
from app.models.matching_review import MatchingReview
from app.schemas.matching_review import MatchingReviewCreate, MatchingReviewResponse, MatchingReviewDecide

router = APIRouter(prefix="/api/mapping-reviews", tags=["matching-reviews"])


def _to_response(r: MatchingReview) -> MatchingReviewResponse:
    return MatchingReviewResponse(
        id=str(r.id), project_id=str(r.project_id),
        item_mapping_id=str(r.item_mapping_id) if r.item_mapping_id else None,
        contract_item_id=str(r.contract_item_id),
        review_type=r.review_type, candidate_mappings=r.candidate_mappings,
        reviewer_id=str(r.reviewer_id) if r.reviewer_id else None,
        decision=r.decision, notes=r.notes, status=r.status,
    )


async def _get_review(review_id: str, current: CurrentUser, db: AsyncSession) -> MatchingReview:
    result = await db.execute(
        select(MatchingReview).where(
            MatchingReview.id == uuid.UUID(review_id),
            MatchingReview.organization_id == current.organization_id,
        )
    )
    review = result.scalars().first()
    if not review:
        raise HTTPException(status_code=404, detail="MatchingReview not found")
    await require_project_member(review.project_id, current, db)
    return review


@router.post("", response_model=MatchingReviewResponse)
async def create_matching_review(req: MatchingReviewCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(req.project_id)
    await require_project_member(pid, current, db)
    review = MatchingReview(
        organization_id=current.organization_id, project_id=pid,
        item_mapping_id=uuid.UUID(req.item_mapping_id) if req.item_mapping_id else None,
        contract_item_id=uuid.UUID(req.contract_item_id),
        review_type=req.review_type, candidate_mappings=req.candidate_mappings,
        notes=req.notes, created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return _to_response(review)


@router.get("", response_model=list[MatchingReviewResponse])
async def list_matching_reviews(project_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(
        select(MatchingReview).where(
            MatchingReview.project_id == pid,
            MatchingReview.organization_id == current.organization_id,
        )
    )
    return [_to_response(r) for r in result.scalars().all()]


@router.get("/{review_id}", response_model=MatchingReviewResponse)
async def get_matching_review(review_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    review = await _get_review(review_id, current, db)
    return _to_response(review)


@router.post("/{review_id}/decide", response_model=MatchingReviewResponse)
async def decide_matching_review(review_id: str, req: MatchingReviewDecide, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    review = await _get_review(review_id, current, db)
    review.reviewer_id = current.user.id
    review.decision = req.decision
    review.notes = req.notes
    review.status = "DECIDED"
    review.updated_by = current.user.id
    await db.commit()
    await db.refresh(review)
    return _to_response(review)
