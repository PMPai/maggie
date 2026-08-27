import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.identity import User, UserRole, Role
from app.auth.password import verify_password, hash_password
from app.auth.tokens import create_access_token, create_refresh_token, decode_token
from app.auth.cookies import set_auth_cookies, clear_auth_cookies
from app.auth.csrf import generate_csrf_token, verify_csrf
from app.auth.rbac import get_current_user, CurrentUser
from app.config import get_settings
from app.schemas.auth import LoginRequest, UserResponse, ChangePasswordRequest
from app.models.approval import AuditLog

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login")
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email, User.status == "ACTIVE"))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    role_result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
    )
    roles = [r[0] for r in role_result.all()]

    access = create_access_token(user.id, user.organization_id, roles)
    refresh = create_refresh_token(user.id)
    csrf = generate_csrf_token()
    set_auth_cookies(response, access, refresh, csrf)

    await db.execute(update(User).where(User.id == user.id).values(last_login_at=datetime.now(timezone.utc)))
    db.add(AuditLog(
        organization_id=user.organization_id,
        user_id=user.id,
        action="LOGIN",
        resource_type="user",
        resource_id=str(user.id),
        detail={"email": user.email},
    ))
    await db.commit()

    return UserResponse(id=str(user.id), email=user.email, display_name=user.display_name, organization_id=str(user.organization_id), roles=roles)


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "logged out"}


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    payload = decode_token(refresh_token, max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id, User.status == "ACTIVE"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    role_result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
    )
    roles = [r[0] for r in role_result.all()]

    access = create_access_token(user.id, user.organization_id, roles)
    csrf = generate_csrf_token()
    response.set_cookie("access_token", access, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, httponly=True, secure=(settings.APP_ENV == "production"), samesite="lax")
    response.set_cookie("csrf_token", csrf, max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, httponly=False, secure=(settings.APP_ENV == "production"), samesite="lax")
    return {"message": "refreshed"}


@router.get("/me", response_model=UserResponse)
async def me(current: CurrentUser = Depends(get_current_user)):
    role_result_str = [r.value if hasattr(r, "value") else r for r in current.roles]
    return UserResponse(id=str(current.user.id), email=current.user.email, display_name=current.user.display_name, organization_id=str(current.organization_id), roles=role_result_str)


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current.user.password_hash or not verify_password(req.old_password, current.user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password incorrect")
    await db.execute(update(User).where(User.id == current.user.id).values(password_hash=hash_password(req.new_password)))
    db.add(AuditLog(
        organization_id=current.organization_id,
        user_id=current.user.id,
        action="CHANGE_PASSWORD",
        resource_type="user",
        resource_id=str(current.user.id),
    ))
    await db.commit()
    return {"message": "password changed"}


@router.get("/roles")
async def list_roles(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Role).order_by(Role.name))
    return [{"id": str(r.id), "name": r.name.value} for r in result.scalars().all()]
