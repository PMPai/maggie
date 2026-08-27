import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_admin
from app.models.identity import Group, GroupRole, UserGroup, User, Role, GroupCategory, UserRoleEnum
from app.schemas.user import GroupCreate, GroupUpdate, GroupMemberAdd, GroupResponse, GroupDetailResponse, GroupRoleInfo, GroupMemberInfo

router = APIRouter(prefix="/api/groups", tags=["groups"])


def _group_to_response(g, member_count: int = 0) -> GroupResponse:
    return GroupResponse(
        id=g.id, name=g.name, category=g.category.value, description=g.description,
        status=g.status, is_default=g.is_default, created_at=g.created_at,
        roles=[], member_count=member_count,
    )


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Group).where(Group.organization_id == current.organization_id).order_by(Group.created_at)
    )
    groups = result.scalars().all()

    responses = []
    for g in groups:
        roles_result = await db.execute(
            select(Role).join(GroupRole, GroupRole.role_id == Role.id).where(GroupRole.group_id == g.id)
        )
        roles = [GroupRoleInfo(id=r.id, name=r.name.value) for r in roles_result.scalars().all()]

        count_result = await db.execute(
            select(func.count(UserGroup.id)).where(UserGroup.group_id == g.id)
        )
        member_count = count_result.scalar() or 0

        responses.append(GroupResponse(
            id=g.id, name=g.name, category=g.category.value, description=g.description,
            status=g.status, is_default=g.is_default, created_at=g.created_at,
            roles=roles, member_count=member_count,
        ))
    return responses


@router.post("", response_model=GroupResponse)
async def create_group(
    req: GroupCreate,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        category = GroupCategory(req.category.upper())
    except ValueError:
        category_options = [c.value for c in GroupCategory]
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {category_options}")

    group = Group(
        organization_id=current.organization_id,
        name=req.name, category=category,
        description=req.description, is_default=False,
    )
    db.add(group)
    await db.flush()

    if req.role_ids:
        for rid in req.role_ids:
            db.add(GroupRole(group_id=group.id, role_id=rid))
        await db.flush()

    await db.commit()
    await db.refresh(group)

    roles_result = await db.execute(
        select(Role).join(GroupRole, GroupRole.role_id == Role.id).where(GroupRole.group_id == group.id)
    )
    roles = [GroupRoleInfo(id=r.id, name=r.name.value) for r in roles_result.scalars().all()]

    return GroupResponse(
        id=group.id, name=group.name, category=group.category.value,
        description=group.description, status=group.status, is_default=False,
        roles=roles, member_count=0, created_at=group.created_at,
    )


@router.get("/{group_id}", response_model=GroupDetailResponse)
async def get_group(
    group_id: str,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    gid = uuid.UUID(group_id)
    result = await db.execute(
        select(Group).where(Group.id == gid, Group.organization_id == current.organization_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    roles_result = await db.execute(
        select(Role).join(GroupRole, GroupRole.role_id == Role.id).where(GroupRole.group_id == gid)
    )
    roles = [GroupRoleInfo(id=r.id, name=r.name.value) for r in roles_result.scalars().all()]

    count_result = await db.execute(select(func.count(UserGroup.id)).where(UserGroup.group_id == gid))
    member_count = count_result.scalar() or 0

    members_result = await db.execute(
        select(User, UserGroup.created_at).join(UserGroup, UserGroup.user_id == User.id).where(UserGroup.group_id == gid)
    )
    members = [
        GroupMemberInfo(id=u.id, display_name=u.display_name, email=u.email, department=u.department, joined_at=ca)
        for u, ca in members_result.all()
    ]

    return GroupDetailResponse(
        id=group.id, name=group.name, category=group.category.value,
        description=group.description, status=group.status, is_default=group.is_default,
        roles=roles, member_count=member_count, members=members, created_at=group.created_at,
    )


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str, req: GroupUpdate,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    gid = uuid.UUID(group_id)
    result = await db.execute(
        select(Group).where(Group.id == gid, Group.organization_id == current.organization_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if req.name is not None:
        group.name = req.name
    if req.category is not None:
        try:
            group.category = GroupCategory(req.category.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category")
    if req.description is not None:
        group.description = req.description
    if req.status is not None:
        if group.is_default and req.status == "INACTIVE":
            raise HTTPException(status_code=400, detail="Cannot deactivate default groups")
        group.status = req.status
    if req.role_ids is not None:
        await db.execute(
            select(GroupRole).where(GroupRole.group_id == gid)
        )
        existing = (await db.execute(select(GroupRole).where(GroupRole.group_id == gid))).scalars().all()
        for er in existing:
            await db.delete(er)
        for rid in req.role_ids:
            db.add(GroupRole(group_id=gid, role_id=rid))

    await db.commit()
    await db.refresh(group)

    roles_result = await db.execute(
        select(Role).join(GroupRole, GroupRole.role_id == Role.id).where(GroupRole.group_id == gid)
    )
    roles = [GroupRoleInfo(id=r.id, name=r.name.value) for r in roles_result.scalars().all()]
    count_result = await db.execute(select(func.count(UserGroup.id)).where(UserGroup.group_id == gid))
    member_count = count_result.scalar() or 0

    return GroupResponse(
        id=group.id, name=group.name, category=group.category.value,
        description=group.description, status=group.status, is_default=group.is_default,
        roles=roles, member_count=member_count, created_at=group.created_at,
    )


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    gid = uuid.UUID(group_id)
    result = await db.execute(
        select(Group).where(Group.id == gid, Group.organization_id == current.organization_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default groups")

    await db.execute(select(UserGroup).where(UserGroup.group_id == gid))
    members = (await db.execute(select(UserGroup).where(UserGroup.group_id == gid))).scalars().all()
    for m in members:
        await db.delete(m)
    await db.execute(select(GroupRole).where(GroupRole.group_id == gid))
    existing_roles = (await db.execute(select(GroupRole).where(GroupRole.group_id == gid))).scalars().all()
    for er in existing_roles:
        await db.delete(er)
    await db.delete(group)
    await db.commit()
    return {"detail": "Group deleted"}


@router.post("/{group_id}/members")
async def add_group_members(
    group_id: str, req: GroupMemberAdd,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    gid = uuid.UUID(group_id)
    result = await db.execute(
        select(Group).where(Group.id == gid, Group.organization_id == current.organization_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    added = 0
    for uid in req.user_ids:
        existing = await db.execute(
            select(UserGroup).where(UserGroup.group_id == gid, UserGroup.user_id == uid)
        )
        if existing.scalar_one_or_none():
            continue
        db.add(UserGroup(
            user_id=uid, group_id=gid, organization_id=current.organization_id,
        ))
        added += 1

    await db.commit()
    return {"detail": f"Added {added} member(s)"}


@router.delete("/{group_id}/members/{user_id}")
async def remove_group_member(
    group_id: str, user_id: str,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    gid = uuid.UUID(group_id)
    result = await db.execute(
        select(Group).where(Group.id == gid, Group.organization_id == current.organization_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    uid = uuid.UUID(user_id)
    if uid == current.user.id and GroupCategory.ADMIN in [group.category]:
        admin_groups = await db.execute(
            select(Group).join(UserGroup, UserGroup.group_id == Group.id)
            .where(UserGroup.user_id == uid, Group.category == GroupCategory.ADMIN, Group.status == "ACTIVE")
        )
        if len(admin_groups.scalars().all()) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove yourself from the last admin group")

    result = await db.execute(
        select(UserGroup).where(UserGroup.group_id == gid, UserGroup.user_id == uid)
    )
    ug = result.scalar_one_or_none()
    if not ug:
        raise HTTPException(status_code=404, detail="Member not found in group")
    await db.delete(ug)
    await db.commit()
    return {"detail": "Member removed"}