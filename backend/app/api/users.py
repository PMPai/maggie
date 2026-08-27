import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.password import hash_password
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_admin
from app.models.identity import User, Role, UserGroup, Group, GroupRole
from app.schemas.user import (
    UserCreate, UserUpdate, UserGroupUpdate, ResetPasswordRequest,
    UserResponse, GroupInfo,
)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.organization_id == current.organization_id,
        ).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    responses = []
    for u in users:
        ug_result = await db.execute(
            select(Group).join(UserGroup, UserGroup.group_id == Group.id)
            .where(UserGroup.user_id == u.id, Group.status == "ACTIVE")
        )
        groups = [GroupInfo(id=g.id, name=g.name, category=g.category.value) for g in ug_result.scalars().all()]

        gr_result = await db.execute(
            select(Role.name).join(GroupRole, GroupRole.role_id == Role.id)
            .join(Group, Group.id == GroupRole.group_id)
            .join(UserGroup, UserGroup.group_id == Group.id)
            .where(UserGroup.user_id == u.id, Group.status == "ACTIVE")
        )
        roles = list(set(r[0].value for r in gr_result.all()))

        responses.append(UserResponse(
            id=u.id, email=u.email, display_name=u.display_name,
            department=u.department, status=u.status,
            roles=roles, groups=groups,
            last_login_at=u.last_login_at, created_at=u.created_at,
        ))
    return responses


@router.post("", response_model=UserResponse)
async def create_user(
    req: UserCreate,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(User).where(
            User.organization_id == current.organization_id,
            User.email == req.email,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists in this organization")

    user = User(
        organization_id=current.organization_id,
        email=req.email, display_name=req.display_name,
        department=req.department,
        password_hash=hash_password(req.password) if req.password else None,
        created_by=current.user.id, updated_by=current.user.id,
    )
    db.add(user)
    await db.flush()

    for gid in req.group_ids:
        db.add(UserGroup(user_id=user.id, group_id=gid, organization_id=current.organization_id))
    await db.commit()
    await db.refresh(user)

    groups = []
    group_ids = req.group_ids if req.group_ids else []
    if group_ids:
        gr_result = await db.execute(
            select(Group).where(Group.id.in_(group_ids))
        )
        groups = [GroupInfo(id=g.id, name=g.name, category=g.category.value) for g in gr_result.scalars().all()]

    return UserResponse(
        id=user.id, email=user.email, display_name=user.display_name,
        department=user.department, status=user.status,
        roles=[], groups=groups,
        last_login_at=None, created_at=user.created_at,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(User).where(
            User.id == uid,
            User.organization_id == current.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ug_result = await db.execute(
        select(Group).join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == uid, Group.status == "ACTIVE")
    )
    groups = [GroupInfo(id=g.id, name=g.name, category=g.category.value) for g in ug_result.scalars().all()]

    gr_result = await db.execute(
        select(Role.name).join(GroupRole, GroupRole.role_id == Role.id)
        .join(Group, Group.id == GroupRole.group_id)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == uid, Group.status == "ACTIVE")
    )
    roles = list(set(r[0].value for r in gr_result.all()))

    return UserResponse(
        id=user.id, email=user.email, display_name=user.display_name,
        department=user.department, status=user.status,
        roles=roles, groups=groups,
        last_login_at=user.last_login_at, created_at=user.created_at,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, req: UserUpdate,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(User).where(
            User.id == uid,
            User.organization_id == current.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if uid == current.user.id and req.status is not None and req.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    if req.display_name is not None:
        user.display_name = req.display_name
    if req.department is not None:
        user.department = req.department
    if req.status is not None:
        user.status = req.status
    user.updated_by = current.user.id

    db.add(user)
    await db.commit()
    await db.refresh(user)

    ug_result = await db.execute(
        select(Group).join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == uid, Group.status == "ACTIVE")
    )
    groups = [GroupInfo(id=g.id, name=g.name, category=g.category.value) for g in ug_result.scalars().all()]

    gr_result = await db.execute(
        select(Role.name).join(GroupRole, GroupRole.role_id == Role.id)
        .join(Group, Group.id == GroupRole.group_id)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == uid, Group.status == "ACTIVE")
    )
    roles = list(set(r[0].value for r in gr_result.all()))

    return UserResponse(
        id=user.id, email=user.email, display_name=user.display_name,
        department=user.department, status=user.status,
        roles=roles, groups=groups,
        last_login_at=user.last_login_at, created_at=user.created_at,
    )


@router.put("/{user_id}/groups", response_model=UserResponse)
async def update_user_groups(
    user_id: str, req: UserGroupUpdate,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(User).where(
            User.id == uid,
            User.organization_id == current.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if uid == current.user.id:
        current_admin_groups = await db.execute(
            select(Group).join(UserGroup, UserGroup.group_id == Group.id)
            .where(UserGroup.user_id == uid, Group.category == "ADMIN").with_entities(Group.id)
        )
        current_admin_group_ids = {r[0] for r in current_admin_groups.all()}
        new_admin_in_set = set(req.group_ids) & current_admin_group_ids
        if not new_admin_in_set:
            raise HTTPException(status_code=400, detail="Cannot remove yourself from all admin groups")

    existing = (await db.execute(select(UserGroup).where(UserGroup.user_id == uid))).scalars().all()
    for ug in existing:
        await db.delete(ug)

    for gid in req.group_ids:
        db.add(UserGroup(user_id=uid, group_id=gid, organization_id=current.organization_id))

    await db.commit()

    ug_result = await db.execute(
        select(Group).join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == uid, Group.status == "ACTIVE")
    )
    groups = [GroupInfo(id=g.id, name=g.name, category=g.category.value) for g in ug_result.scalars().all()]

    gr_result = await db.execute(
        select(Role.name).join(GroupRole, GroupRole.role_id == Role.id)
        .join(Group, Group.id == GroupRole.group_id)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == uid, Group.status == "ACTIVE")
    )
    roles = list(set(r[0].value for r in gr_result.all()))

    return UserResponse(
        id=user.id, email=user.email, display_name=user.display_name,
        department=user.department, status=user.status,
        roles=roles, groups=groups,
        last_login_at=user.last_login_at, created_at=user.created_at,
    )


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: str, req: ResetPasswordRequest,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(User).where(
            User.id == uid,
            User.organization_id == current.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(req.new_password)
    user.updated_by = current.user.id
    db.add(user)
    await db.commit()
    return {"detail": "Password reset successfully"}