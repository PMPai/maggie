import enum
import uuid
from decimal import Decimal
from sqlalchemy import Enum, String, Text, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, OrganizationMixin, AuditMixin, SoftDeleteMixin


class MappingType(enum.Enum):
    ONE_TO_ONE = "ONE_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"


class MatchMethod(enum.Enum):
    MANUAL = "MANUAL"
    EXACT_ALIAS = "EXACT_ALIAS"
    RULE = "RULE"
    FULLTEXT = "FULLTEXT"
    VECTOR = "VECTOR"
    LLM = "LLM"


class UnitCompatibility(enum.Enum):
    SAME = "SAME"
    CONVERTIBLE = "CONVERTIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


class MappingStatus(enum.Enum):
    SUGGESTED = "SUGGESTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class ItemMapping(Base, TimestampMixin, OrganizationMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "item_mappings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_items.id"), nullable=False)
    standard_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("standard_items.id"), nullable=False)
    mapping_type: Mapped[MappingType] = mapped_column(Enum(MappingType), nullable=False, default=MappingType.ONE_TO_ONE)
    match_method: Mapped[MatchMethod] = mapped_column(Enum(MatchMethod), nullable=False, default=MatchMethod.MANUAL)
    unit_compatibility: Mapped[UnitCompatibility] = mapped_column(Enum(UnitCompatibility), nullable=False, default=UnitCompatibility.SAME)
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=1)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[MappingStatus] = mapped_column(Enum(MappingStatus), nullable=False, default=MappingStatus.SUGGESTED)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    llm_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    __table_args__ = (UniqueConstraint("contract_item_id", "standard_item_id", name="uq_item_mappings"),)


class MappingComponent(Base, TimestampMixin, AuditMixin):
    __tablename__ = "mapping_components"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_mapping_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("item_mappings.id", ondelete="CASCADE"), nullable=False)
    contract_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contract_items.id"), nullable=False)
    standard_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("standard_items.id"), nullable=False)
    component_ratio: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=1)
