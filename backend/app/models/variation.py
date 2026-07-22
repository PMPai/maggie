import enum
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy import Enum, String, Text, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, OrganizationMixin, AuditMixin, SoftDeleteMixin


class VariationType(enum.Enum):
    PRICE_ADJUSTMENT = "PRICE_ADJUSTMENT"
    QUANTITY_ADJUSTMENT = "QUANTITY_ADJUSTMENT"
    SCOPE_CHANGE = "SCOPE_CHANGE"
    LUMP_SUM_ADJUSTMENT = "LUMP_SUM_ADJUSTMENT"


class VariationStatus(enum.Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class Variation(Base, TimestampMixin, OrganizationMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "variations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_items.id"), nullable=True)
    variation_no: Mapped[str] = mapped_column(String(64), nullable=False)
    variation_type: Mapped[VariationType] = mapped_column(Enum(VariationType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_ex_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    amount_inc_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[VariationStatus] = mapped_column(Enum(VariationStatus), nullable=False, default=VariationStatus.DRAFT)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    __table_args__ = (UniqueConstraint("contract_id", "variation_no", name="uq_variations_contract_no"),)


class VariationLine(Base, TimestampMixin, AuditMixin):
    __tablename__ = "variation_lines"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("variations.id", ondelete="CASCADE"), nullable=False)
    contract_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_items.id"), nullable=False)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    unit_price_new: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    amount_delta: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
