import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_project_member
from app.models.mapping import ItemMapping, MappingStatus
from app.schemas.mapping import ItemMappingCreate, ItemMappingResponse
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/item-mappings", tags=["item-mappings"])


def _v(val):
    return val.value if hasattr(val, "value") else val


def _to_response(m: ItemMapping) -> ItemMappingResponse:
    return ItemMappingResponse(
        id=str(m.id), project_id=str(m.project_id),
        contract_item_id=str(m.contract_item_id), standard_item_id=str(m.standard_item_id),
        mapping_type=_v(m.mapping_type), match_method=_v(m.match_method),
        unit_compatibility=_v(m.unit_compatibility), conversion_factor=m.conversion_factor,
        confidence=m.confidence, status=_v(m.status),
        approved_by=str(m.approved_by) if m.approved_by else None,
        approved_at=str(m.approved_at) if m.approved_at else None,
        llm_reasoning=m.llm_reasoning, llm_output=m.llm_output,
    )


async def _get_mapping(mapping_id: str, current: CurrentUser, db: AsyncSession) -> ItemMapping:
    result = await db.execute(
        select(ItemMapping).where(
            ItemMapping.id == uuid.UUID(mapping_id),
            ItemMapping.organization_id == current.organization_id,
            ItemMapping.deleted_at.is_(None),
        )
    )
    mapping = result.scalars().first()
    if not mapping:
        raise HTTPException(status_code=404, detail="ItemMapping not found")
    await require_project_member(mapping.project_id, current, db)
    return mapping


@router.post("", response_model=ItemMappingResponse)
async def create_item_mapping(req: ItemMappingCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(req.project_id)
    await require_project_member(pid, current, db)
    mapping = ItemMapping(
        organization_id=current.organization_id, project_id=pid,
        contract_item_id=uuid.UUID(req.contract_item_id),
        standard_item_id=uuid.UUID(req.standard_item_id),
        mapping_type=req.mapping_type, match_method=req.match_method,
        unit_compatibility=req.unit_compatibility, conversion_factor=req.conversion_factor,
        confidence=req.confidence, status=req.status,
        llm_reasoning=req.llm_reasoning, llm_output=req.llm_output,
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return _to_response(mapping)


@router.get("", response_model=list[ItemMappingResponse])
async def list_item_mappings(project_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(
        select(ItemMapping).where(
            ItemMapping.project_id == pid,
            ItemMapping.organization_id == current.organization_id,
            ItemMapping.deleted_at.is_(None),
        )
    )
    return [_to_response(m) for m in result.scalars().all()]


@router.get("/{mapping_id}", response_model=ItemMappingResponse)
async def get_item_mapping(mapping_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mapping = await _get_mapping(mapping_id, current, db)
    return _to_response(mapping)


@router.post("/{mapping_id}/approve", response_model=ItemMappingResponse)
async def approve_item_mapping(mapping_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mapping = await _get_mapping(mapping_id, current, db)
    mapping.status = MappingStatus.APPROVED
    mapping.approved_by = current.user.id
    mapping.updated_by = current.user.id
    db.add(AuditLog(
        organization_id=current.organization_id,
        user_id=current.user.id,
        action="APPROVE",
        resource_type="item_mapping",
        resource_id=str(mapping.id),
    ))
    await db.commit()
    await db.refresh(mapping)
    return _to_response(mapping)


@router.post("/{mapping_id}/reject", response_model=ItemMappingResponse)
async def reject_item_mapping(mapping_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mapping = await _get_mapping(mapping_id, current, db)
    mapping.status = MappingStatus.REJECTED
    mapping.updated_by = current.user.id
    db.add(AuditLog(
        organization_id=current.organization_id,
        user_id=current.user.id,
        action="REJECT",
        resource_type="item_mapping",
        resource_id=str(mapping.id),
    ))
    await db.commit()
    await db.refresh(mapping)
    return _to_response(mapping)
