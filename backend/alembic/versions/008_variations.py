"""variations and variation lines"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from app.models.variation import VariationType, VariationStatus

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "variations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_item_id", UUID(as_uuid=True), sa.ForeignKey("contract_items.id")),
        sa.Column("variation_no", sa.String(64), nullable=False),
        sa.Column("variation_type", sa.Enum(VariationType), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("reason", sa.Text),
        sa.Column("amount_ex_tax", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("amount_inc_tax", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("quantity_delta", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("effective_date", sa.Date),
        sa.Column("status", sa.Enum(VariationStatus), nullable=False, server_default="DRAFT"),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("approved_at", sa.Date),
        sa.Column("source_document_id", UUID(as_uuid=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("contract_id", "variation_no", name="uq_variations_contract_no"),
    )
    op.create_index("ix_variations_organization_id", "variations", ["organization_id"])
    op.create_index("ix_variations_project_id", "variations", ["project_id"])
    op.create_index("ix_variations_contract_id", "variations", ["contract_id"])

    op.create_table(
        "variation_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("variation_id", UUID(as_uuid=True), sa.ForeignKey("variations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_item_id", UUID(as_uuid=True), sa.ForeignKey("contract_items.id"), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("unit_price_new", sa.Numeric(18, 2)),
        sa.Column("amount_delta", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("description", sa.Text),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_variation_lines_variation_id", "variation_lines", ["variation_id"])


def downgrade():
    op.drop_table("variation_lines")
    op.drop_table("variations")
