import enum
import uuid
from datetime import datetime
from sqlalchemy import Enum, String, Boolean, ForeignKey, DateTime, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, AuditMixin


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    default_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="TWD")
    default_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Taipei")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")


class UserRoleEnum(enum.Enum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    CONTRACT_ADMIN = "CONTRACT_ADMIN"
    PROJECT_USER = "PROJECT_USER"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    COST_REVIEWER = "COST_REVIEWER"
    FINANCE_REVIEWER = "FINANCE_REVIEWER"
    FINANCE_USER = "FINANCE_USER"
    AUDITOR = "AUDITOR"
    VIEWER = "VIEWER"


class User(Base, TimestampMixin, AuditMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_users_org_email"),
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Enum(UserRoleEnum), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)


class UserRole(Base, TimestampMixin):
    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles"),
    )
