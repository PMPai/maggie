"""financial_adjustments"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_adjustments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("adjustment_no", sa.String(64), nullable=False),
        sa.Column("adjustment_type", sa.String(32), nullable=False),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id")),
        sa.Column("collection_id", UUID(as_uuid=True), sa.ForeignKey("collections.id")),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("reason", sa.Text),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("approved_at", sa.Date),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "adjustment_no", name="uq_financial_adjustments_project_no"),
    )
    op.create_index("ix_financial_adjustments_project_id", "financial_adjustments", ["project_id"])


def downgrade():
    op.drop_table("financial_adjustments")
