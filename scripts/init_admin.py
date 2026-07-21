"""Create initial admin user. Run: python scripts/init_admin.py"""
import asyncio
import uuid
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.identity import Organization, User, Role, UserRole, UserRoleEnum
from app.auth.password import hash_password


async def init_admin(email: str = "admin@maggie.local", password: str = "admin123", org_code: str = "MAGGIE", org_name: str = "Maggie Construction"):
    async with async_session_factory() as db:
        # Create org
        result = await db.execute(select(Organization).where(Organization.code == org_code))
        org = result.scalar_one_or_none()
        if not org:
            org = Organization(code=org_code, name=org_name, default_currency="TWD", default_timezone="Asia/Taipei")
            db.add(org)
            await db.flush()

        # Create admin user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(organization_id=org.id, email=email, display_name="系统管理员", password_hash=hash_password(password), status="ACTIVE")
            db.add(user)
            await db.flush()

        # Assign SYSTEM_ADMIN role
        result = await db.execute(select(Role).where(Role.name == UserRoleEnum.SYSTEM_ADMIN))
        role = result.scalar_one()
        result = await db.execute(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id))
        if not result.scalar_one_or_none():
            db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org.id))
        await db.commit()
        print(f"Admin created: {email} / {password}")


if __name__ == "__main__":
    asyncio.run(init_admin())
