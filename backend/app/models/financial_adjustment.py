import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy import String, Text, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin,  AuditMixin, SoftDeleteMixin


class FinancialAdjustment(Base, TimestampMixin,  AuditMixin, SoftDeleteMixin):
    __tablename__ = "financial_adjustments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    adjustment_no: Mapped[str] = mapped_column(String(64), nullable=False)
    adjustment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    collection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("collections.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    __table_args__ = (UniqueConstraint("project_id", "adjustment_no", name="uq_financial_adjustments_project_no"),)
