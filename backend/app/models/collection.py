import enum
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy import Enum, String, Text, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin,  AuditMixin, SoftDeleteMixin


class CollectionStatus(enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REVERSED = "REVERSED"


class Collection(Base, TimestampMixin,  AuditMixin, SoftDeleteMixin):
    __tablename__ = "collections"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_no: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount_received: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False, default="BANK_TRANSFER")
    bank_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CollectionStatus] = mapped_column(Enum(CollectionStatus), nullable=False, default=CollectionStatus.CONFIRMED)
    __table_args__ = (UniqueConstraint("contract_id", "receipt_no", name="uq_collections_contract_no"),)


class CollectionAllocation(Base, TimestampMixin, AuditMixin):
    __tablename__ = "collection_allocations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
