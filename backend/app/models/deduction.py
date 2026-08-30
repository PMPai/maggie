import enum
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy import Enum, String, Text, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin,  AuditMixin, SoftDeleteMixin


class DeductionType(enum.Enum):
    ADVANCE_OFFSET = "ADVANCE_OFFSET"
    MATERIAL_DEDUCTION = "MATERIAL_DEDUCTION"
    EQUIPMENT_DEDUCTION = "EQUIPMENT_DEDUCTION"
    QUALITY_PENALTY = "QUALITY_PENALTY"
    OTHER = "OTHER"


class TaxTreatment(enum.Enum):
    TAXABLE = "TAXABLE"
    NON_TAXABLE = "NON_TAXABLE"
    TAX_ADJUSTMENT = "TAX_ADJUSTMENT"


class DeductionStatus(enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Deduction(Base, TimestampMixin,  AuditMixin, SoftDeleteMixin):
    __tablename__ = "deductions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("payment_applications.id"), nullable=True)
    deduction_no: Mapped[str] = mapped_column(String(64), nullable=False)
    deduction_type: Mapped[DeductionType] = mapped_column(Enum(DeductionType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_treatment: Mapped[TaxTreatment] = mapped_column(Enum(TaxTreatment), nullable=False, default=TaxTreatment.TAXABLE)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[DeductionStatus] = mapped_column(Enum(DeductionStatus), nullable=False, default=DeductionStatus.DRAFT)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    __table_args__ = (UniqueConstraint("contract_id", "deduction_no", name="uq_deductions_contract_no"),)
