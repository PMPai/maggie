"""matching_reviews"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "matching_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_mapping_id", UUID(as_uuid=True), sa.ForeignKey("item_mappings.id")),
        sa.Column("contract_item_id", UUID(as_uuid=True), sa.ForeignKey("contract_items.id"), nullable=False),
        sa.Column("review_type", sa.String(32), nullable=False),
        sa.Column("candidate_mappings", JSONB),
        sa.Column("reviewer_id", UUID(as_uuid=True)),
        sa.Column("decision", sa.String(16)),
        sa.Column("notes", sa.Text),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_matching_reviews_project_id", "matching_reviews", ["project_id"])
    op.create_index("ix_matching_reviews_organization_id", "matching_reviews", ["organization_id"])


def downgrade():
    op.drop_table("matching_reviews")
