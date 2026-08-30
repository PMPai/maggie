import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Enum, String, Text, Integer, Boolean, Numeric, Date, ForeignKey, DateTime, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin,  AuditMixin, SoftDeleteMixin


class ApplicationStatus(enum.Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    NEEDS_CHANGES = "NEEDS_CHANGES"
    SUBMITTED = "SUBMITTED"
    PROJECT_APPROVED = "PROJECT_APPROVED"
    FINANCE_APPROVED = "FINANCE_APPROVED"
    POSTED = "POSTED"
    GENERATED = "GENERATED"
    SENT = "SENT"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class RetentionEntryType(enum.Enum):
    HOLD = "HOLD"
    RELEASE = "RELEASE"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"


class PaymentApplication(Base, TimestampMixin,  AuditMixin, SoftDeleteMixin):
    __tablename__ = "payment_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_versions.id"), nullable=False)
    application_no: Mapped[str] = mapped_column(String(64), nullable=False)
    period_no: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    application_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.DRAFT)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="TWD")
    gross_completed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    retention_held_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    retention_released_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    deduction_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    invoice_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supersedes_application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("payment_applications.id"), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_action_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # idempotency key

    __table_args__ = (
        UniqueConstraint("contract_id", "application_no", "revision_no", name="uq_payment_applications"),
    )


class PaymentApplicationLine(Base, TimestampMixin,  AuditMixin):
    __tablename__ = "payment_application_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payment_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_items.id"), nullable=False)
    contract_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_versions.id"), nullable=False)
    description_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    unit_snapshot: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    previous_approved_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    current_claimed_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    current_approved_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    cumulative_approved_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    current_completed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    retention_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0"))
    retention_held: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    retention_released: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    deduction_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    calculation_method: Mapped[str] = mapped_column(String(32), nullable=False, default="QUANTITY")
    user_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")


class MilestoneEvent(Base, TimestampMixin,  AuditMixin):
    __tablename__ = "milestone_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_items.id"), nullable=True)
    milestone_name: Mapped[str] = mapped_column(String(128), nullable=False)
    milestone_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RetentionEntry(Base, TimestampMixin,  AuditMixin):
    __tablename__ = "retention_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("payment_applications.id"), nullable=True)
    contract_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_items.id"), nullable=True)
    entry_type: Mapped[str] = mapped_column(Enum(RetentionEntryType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("retention_entries.id"), nullable=True)
