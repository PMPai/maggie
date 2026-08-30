import enum
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy import Enum, String, Text, Date, Numeric, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin,  AuditMixin, SoftDeleteMixin


class InvoiceType(enum.Enum):
    STANDARD = "STANDARD"
    DEBIT_NOTE = "DEBIT_NOTE"
    CREDIT_NOTE = "CREDIT_NOTE"


class InvoiceStatus(enum.Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    VOID = "VOID"


class Invoice(Base, TimestampMixin,  AuditMixin, SoftDeleteMixin):
    __tablename__ = "invoices"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_no: Mapped[str] = mapped_column(String(64), nullable=False)
    invoice_type: Mapped[InvoiceType] = mapped_column(Enum(InvoiceType), nullable=False, default=InvoiceType.STANDARD)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount_ex_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    amount_inc_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0.05"))
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint("contract_id", "invoice_no", name="uq_invoices_contract_no"),
        CheckConstraint("amount_ex_tax + tax_amount = amount_inc_tax", name="ck_invoice_amounts"),
    )


class InvoiceApplicationLink(Base, TimestampMixin, AuditMixin):
    __tablename__ = "invoice_application_links"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    payment_application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payment_applications.id"), nullable=False)
    linked_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
