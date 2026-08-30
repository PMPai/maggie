"""item_mappings and mapping_components"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

# Inlined enum values (models were removed in Phase 0)
_MAPPING_TYPES = ["ONE_TO_ONE", "ONE_TO_MANY", "MANY_TO_ONE"]
_MATCH_METHODS = ["MANUAL", "EXACT_ALIAS", "RULE", "FULLTEXT", "VECTOR", "LLM"]
_UNIT_COMPAT = ["SAME", "CONVERTIBLE", "INCOMPATIBLE", "UNKNOWN"]
_MAPPING_STATUS = ["SUGGESTED", "PENDING_REVIEW", "APPROVED", "REJECTED", "NEEDS_CLARIFICATION"]


def upgrade():
    op.create_table(
        "item_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_item_id", UUID(as_uuid=True), sa.ForeignKey("contract_items.id"), nullable=False),
        sa.Column("standard_item_id", UUID(as_uuid=True), sa.ForeignKey("standard_items.id"), nullable=False),
        sa.Column("mapping_type", sa.Enum(*_MAPPING_TYPES, name="mappingtype"), nullable=False, server_default="ONE_TO_ONE"),
        sa.Column("match_method", sa.Enum(*_MATCH_METHODS, name="matchmethod"), nullable=False, server_default="MANUAL"),
        sa.Column("unit_compatibility", sa.Enum(*_UNIT_COMPAT, name="unitcompatibility"), nullable=False, server_default="SAME"),
        sa.Column("conversion_factor", sa.Numeric(18, 6), nullable=False, server_default="1"),
        sa.Column("confidence", sa.Numeric(5, 2)),
        sa.Column("status", sa.Enum(*_MAPPING_STATUS, name="mappingstatus"), nullable=False, server_default="SUGGESTED"),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("approved_at", UUID(as_uuid=True)),
        sa.Column("llm_reasoning", sa.Text),
        sa.Column("llm_output", JSONB),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("contract_item_id", "standard_item_id", name="uq_item_mappings"),
    )
    op.create_index("ix_item_mappings_project_id", "item_mappings", ["project_id"])
    op.create_index("ix_item_mappings_organization_id", "item_mappings", ["organization_id"])

    op.create_table(
        "mapping_components",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("item_mapping_id", UUID(as_uuid=True), sa.ForeignKey("item_mappings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_item_id", UUID(as_uuid=True), sa.ForeignKey("contract_items.id"), nullable=False),
        sa.Column("standard_item_id", UUID(as_uuid=True), sa.ForeignKey("standard_items.id"), nullable=False),
        sa.Column("component_ratio", sa.Numeric(10, 6), nullable=False, server_default="1"),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_mapping_components_item_mapping_id", "mapping_components", ["item_mapping_id"])


def downgrade():
    op.drop_table("mapping_components")
    op.drop_table("item_mappings")
