import uuid
from datetime import date
from sqlalchemy import String, Text, Boolean, Integer, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, OrganizationMixin, AuditMixin, SoftDeleteMixin


class StandardItem(Base, TimestampMixin, OrganizationMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "standard_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_standard_items_org_code"),)


class StandardItemAlias(Base, TimestampMixin, OrganizationMixin, AuditMixin):
    __tablename__ = "standard_item_aliases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    standard_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("standard_items.id", ondelete="CASCADE"), nullable=False)
    alias_text: Mapped[str] = mapped_column(String(256), nullable=False)
    alias_source: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    __table_args__ = (UniqueConstraint("standard_item_id", "alias_text", name="uq_standard_item_aliases"),)


class StandardCostVersion(Base, TimestampMixin, OrganizationMixin, AuditMixin):
    __tablename__ = "standard_cost_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    standard_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("standard_items.id", ondelete="CASCADE"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    unit_cost: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    cost_basis: Mapped[str] = mapped_column(String(32), nullable=False, default="STANDARD")
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    __table_args__ = (UniqueConstraint("standard_item_id", "version_no", name="uq_standard_cost_versions"),)
