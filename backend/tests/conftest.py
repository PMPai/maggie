import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.db.base import Base
from app.main import app
from app.db.session import get_db


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine("postgresql+asyncpg://maggie:maggie@postgres:5432/maggie_test")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        await conn.exec_driver_sql("CREATE SCHEMA public")
    await engine.dispose()


@pytest_asyncio.fixture
async def db(test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


import uuid as _uuid
from app.models.identity import User, Role, UserRole, Organization, UserRoleEnum
from app.auth.tokens import create_access_token


@pytest_asyncio.fixture
async def auth_user(client, db):
    """Create a user + org + SYSTEM_ADMIN role, log the client in (set cookie), return dict."""
    org = Organization(id=_uuid.uuid4(), code="TESTORG", name="Test Org",
                       default_currency="TWD", default_timezone="Asia/Taipei", status="ACTIVE")
    db.add(org)
    await db.flush()
    user = User(id=_uuid.uuid4(), organization_id=org.id, email="test@example.com",
                display_name="Test User", password_hash="x", status="ACTIVE")
    db.add(user)
    await db.flush()
    role = Role(id=_uuid.uuid4(), name=UserRoleEnum.SYSTEM_ADMIN)
    db.add(role)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org.id))
    await db.commit()
    token = create_access_token(user.id, org.id, [UserRoleEnum.SYSTEM_ADMIN])
    client.cookies.set("access_token", token)
    return {"id": str(user.id), "org_id": str(org.id), "roles": ["SYSTEM_ADMIN"]}
