import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Enum, String, Text, Boolean, Integer, Numeric, Date, ForeignKey, DateTime, UniqueConstraint, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, OrganizationMixin, AuditMixin, SoftDeleteMixin


class TaxMode(enum.Enum):
    EXCLUSIVE = "EXCLUSIVE"
    INCLUSIVE = "INCLUSIVE"
    MIXED = "MIXED"


class RoundingPolicy(enum.Enum):
    ROUND_HALF_UP = "ROUND_HALF_UP"
    ROUND_DOWN = "ROUND_DOWN"
    BANKERS = "BANKERS"


class Contract(Base, TimestampMixin, OrganizationMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    external_contract_no: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_name: Mapped[str] = mapped_column(String(256), nullable=False)
    customer_company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    contractor_company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    signed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="TWD")
    tax_mode: Mapped[str] = mapped_column(Enum(TaxMode), nullable=False, default=TaxMode.EXCLUSIVE)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0.05"))
    rounding_policy: Mapped[str] = mapped_column(Enum(RoundingPolicy), nullable=False, default=RoundingPolicy.ROUND_HALF_UP)
    rounding_granularity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("1"))
    original_amount_ex_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    original_tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    original_amount_inc_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_versions.id", use_alter=True, name="fk_contracts_active_version_id"), nullable=True)


class ContractVersionType(enum.Enum):
    QUOTATION = "QUOTATION"
    SIGNED_CONTRACT = "SIGNED_CONTRACT"
    PROVISIONAL = "PROVISIONAL"
    INTERNAL_ADJUSTMENT = "INTERNAL_ADJUSTMENT"
    APPROVED_VARIATION = "APPROVED_VARIATION"


class ContractVersionStatus(enum.Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class ContractVersion(Base, TimestampMixin, OrganizationMixin, AuditMixin):
    __tablename__ = "contract_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    version_type: Mapped[str] = mapped_column(Enum(ContractVersionType), nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount_ex_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    amount_inc_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(Enum(ContractVersionStatus), nullable=False, default=ContractVersionStatus.DRAFT)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("contract_id", "version_no", name="uq_contract_versions"),
        CheckConstraint("amount_ex_tax + tax_amount = amount_inc_tax", name="ck_contract_version_amounts"),
    )


class CalculationMethod(enum.Enum):
    QUANTITY = "QUANTITY"
    LUMP_SUM = "LUMP_SUM"
    PERCENTAGE = "PERCENTAGE"
    MILESTONE = "MILESTONE"
    ALLOWANCE = "ALLOWANCE"
    ADJUSTMENT = "ADJUSTMENT"
    HEADING = "HEADING"


class ContractItem(Base, TimestampMixin, OrganizationMixin, AuditMixin):
    __tablename__ = "contract_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_items.id"), nullable=True)
    line_no: Mapped[str] = mapped_column(String(32), nullable=False)
    item_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_description: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contract_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    line_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    calculation_method: Mapped[str] = mapped_column(Enum(CalculationMethod), nullable=False, default=CalculationMethod.QUANTITY)
    tax_category: Mapped[str] = mapped_column(String(32), nullable=False, default="STANDARD")
    retention_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    retention_exempt_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_heading: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_billable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_bbox_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    expected_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class PaymentRuleType(enum.Enum):
    PROGRESS_PAYMENT = "PROGRESS_PAYMENT"
    RETENTION_HOLD = "RETENTION_HOLD"
    RETENTION_RELEASE = "RETENTION_RELEASE"
    MILESTONE_PAYMENT = "MILESTONE_PAYMENT"
    ADVANCE_PAYMENT = "ADVANCE_PAYMENT"
    DEDUCTION = "DEDUCTION"
    TAX = "TAX"
    ROUNDING = "ROUNDING"
    PENALTY = "PENALTY"


class PaymentRule(Base, TimestampMixin, OrganizationMixin, AuditMixin):
    __tablename__ = "payment_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_items.id"), nullable=True)
    rule_type: Mapped[str] = mapped_column(Enum(PaymentRuleType), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0"))
    condition_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    condition_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculation_base: Mapped[str] = mapped_column(String(32), nullable=False, default="CURRENT_PERIOD")
    release_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
