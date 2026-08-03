from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models.standard import StandardItem, StandardItemAlias, StandardCostVersion
from app.schemas.standard import (
    StandardItemCreate, StandardItemResponse,
    StandardItemAliasCreate, StandardItemAliasResponse,
    StandardCostVersionCreate, StandardCostVersionResponse,
)
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/standard-items", tags=["standard-items"])


@router.post("", response_model=StandardItemResponse)
async def create_standard_item(req: StandardItemCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = StandardItem(
        organization_id=current.organization_id,
        code=req.code, name=req.name, category=req.category, unit=req.unit,
        description=req.description, is_active=req.is_active, sort_order=req.sort_order,
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(item)
    await db.flush()
    db.add(AuditLog(
        organization_id=current.organization_id,
        user_id=current.user.id,
        action="CREATE",
        resource_type="standard_item",
        resource_id=str(item.id),
        detail={"code": item.code, "name": item.name},
    ))
    await db.commit()
    await db.refresh(item)
    return StandardItemResponse(
        id=str(item.id), code=item.code, name=item.name, category=item.category,
        unit=item.unit, description=item.description, is_active=item.is_active, sort_order=item.sort_order,
    )


@router.get("", response_model=list[StandardItemResponse])
async def list_standard_items(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StandardItem).where(StandardItem.organization_id == current.organization_id, StandardItem.deleted_at.is_(None))
        .offset((page - 1) * size).limit(size)
    )
    return [StandardItemResponse(
        id=str(i.id), code=i.code, name=i.name, category=i.category, unit=i.unit,
        description=i.description, is_active=i.is_active, sort_order=i.sort_order,
    ) for i in result.scalars().all()]


@router.get("/{item_id}", response_model=StandardItemResponse)
async def get_standard_item(item_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StandardItem).where(StandardItem.id == item_id, StandardItem.organization_id == current.organization_id, StandardItem.deleted_at.is_(None))
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="StandardItem not found")
    return StandardItemResponse(
        id=str(item.id), code=item.code, name=item.name, category=item.category, unit=item.unit,
        description=item.description, is_active=item.is_active, sort_order=item.sort_order,
    )


@router.put("/{item_id}", response_model=StandardItemResponse)
async def update_standard_item(item_id: str, req: StandardItemCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StandardItem).where(StandardItem.id == item_id, StandardItem.organization_id == current.organization_id, StandardItem.deleted_at.is_(None))
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="StandardItem not found")
    item.code = req.code
    item.name = req.name
    item.category = req.category
    item.unit = req.unit
    item.description = req.description
    item.is_active = req.is_active
    item.sort_order = req.sort_order
    item.updated_by = current.user.id
    db.add(AuditLog(
        organization_id=current.organization_id,
        user_id=current.user.id,
        action="UPDATE",
        resource_type="standard_item",
        resource_id=str(item.id),
        detail={"code": item.code, "name": item.name},
    ))
    await db.commit()
    await db.refresh(item)
    return StandardItemResponse(
        id=str(item.id), code=item.code, name=item.name, category=item.category, unit=item.unit,
        description=item.description, is_active=item.is_active, sort_order=item.sort_order,
    )


@router.post("/{item_id}/aliases", response_model=StandardItemAliasResponse)
async def add_alias(item_id: str, req: StandardItemAliasCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    alias = StandardItemAlias(
        organization_id=current.organization_id,
        standard_item_id=item_id,
        alias_text=req.alias_text, alias_source=req.alias_source, is_approved=req.is_approved,
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(alias)
    await db.commit()
    await db.refresh(alias)
    return StandardItemAliasResponse(
        id=str(alias.id), standard_item_id=str(alias.standard_item_id), alias_text=alias.alias_text,
        alias_source=alias.alias_source, is_approved=alias.is_approved,
        approved_by=str(alias.approved_by) if alias.approved_by else None, approved_at=alias.approved_at,
    )


@router.get("/{item_id}/aliases", response_model=list[StandardItemAliasResponse])
async def list_aliases(item_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StandardItemAlias).where(StandardItemAlias.standard_item_id == item_id, StandardItemAlias.organization_id == current.organization_id)
    )
    return [StandardItemAliasResponse(
        id=str(a.id), standard_item_id=str(a.standard_item_id), alias_text=a.alias_text,
        alias_source=a.alias_source, is_approved=a.is_approved,
        approved_by=str(a.approved_by) if a.approved_by else None, approved_at=a.approved_at,
    ) for a in result.scalars().all()]


@router.post("/{item_id}/cost-versions", response_model=StandardCostVersionResponse)
async def add_cost_version(item_id: str, req: StandardCostVersionCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    version = StandardCostVersion(
        organization_id=current.organization_id,
        standard_item_id=item_id,
        version_no=req.version_no, effective_from=req.effective_from, effective_to=req.effective_to,
        unit_cost=req.unit_cost, cost_basis=req.cost_basis, source=req.source, notes=req.notes, status=req.status,
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return StandardCostVersionResponse(
        id=str(version.id), standard_item_id=str(version.standard_item_id), version_no=version.version_no,
        effective_from=version.effective_from, effective_to=version.effective_to, unit_cost=version.unit_cost,
        cost_basis=version.cost_basis, source=version.source, notes=version.notes, status=version.status,
    )


@router.get("/{item_id}/cost-versions", response_model=list[StandardCostVersionResponse])
async def list_cost_versions(item_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StandardCostVersion).where(StandardCostVersion.standard_item_id == item_id, StandardCostVersion.organization_id == current.organization_id)
    )
    return [StandardCostVersionResponse(
        id=str(v.id), standard_item_id=str(v.standard_item_id), version_no=v.version_no,
        effective_from=v.effective_from, effective_to=v.effective_to, unit_cost=v.unit_cost,
        cost_basis=v.cost_basis, source=v.source, notes=v.notes, status=v.status,
    ) for v in result.scalars().all()]
