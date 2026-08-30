import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Text, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin


class Company(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    company_type: Mapped[str] = mapped_column(String(32), nullable=False)  # OWNER, MAIN_CONTRACTOR, SUBCONTRACTOR, SUPPLIER, SELF
    tax_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")

    __table_args__ = (
        UniqueConstraint("code", name="uq_companies_code"),
    )


class Project(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internal_project_code: Mapped[str] = mapped_column(String(32), nullable=False)
    project_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="TWD")
    default_tax_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0.05"))
    special_fund_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("internal_project_code", name="uq_projects_code"),
    )


class ProjectParty(Base, TimestampMixin, AuditMixin):
    __tablename__ = "project_parties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    role_in_project: Mapped[str] = mapped_column(String(32), nullable=False)  # OWNER, MAIN_CONTRACTOR, etc.
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
