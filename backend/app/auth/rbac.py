import uuid
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.identity import User, UserRole, Role, UserGroup, Group, GroupRole, UserRoleEnum, GroupCategory
from app.auth.tokens import decode_token
from app.auth.role_categories import roles_to_categories, has_category, is_admin
from app.config import get_settings

settings = get_settings()


class CurrentUser:
    def __init__(self, user: User, roles: list[UserRoleEnum], organization_id: uuid.UUID):
        self.user = user
        self.roles = roles
        self.categories = roles_to_categories(roles)
        self.organization_id = organization_id

    def has_category(self, *cats: GroupCategory) -> bool:
        return any(c in self.categories for c in cats)

    def is_admin(self) -> bool:
        return GroupCategory.ADMIN in self.categories


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> CurrentUser:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(
        select(User).where(User.id == user_id, User.status == "ACTIVE")
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    role_result = await db.execute(
        select(Role.name).join(GroupRole, GroupRole.role_id == Role.id)
        .join(Group, Group.id == GroupRole.group_id)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == user_id, Group.status == "ACTIVE")
    )
    group_roles = [r[0] for r in role_result.all()]

    if not group_roles:
        role_result = await db.execute(
            select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
        )
        group_roles = [r[0] for r in role_result.all()]

    return CurrentUser(user=user, roles=group_roles, organization_id=user.organization_id)


def require_role(*allowed_roles: UserRoleEnum):
    async def checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(r in allowed_roles for r in current.roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current
    return checker


def require_category(*allowed_cats: GroupCategory):
    async def checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current.has_category(*allowed_cats):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current
    return checker


def require_admin(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current.is_admin():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current


async def require_project_member(project_id: uuid.UUID, current: CurrentUser, db: AsyncSession) -> CurrentUser:
    from app.models.project import ProjectMember
    if current.is_admin():
        return current
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current.user.id,
            ProjectMember.status == "ACTIVE",
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a project member")
    return current