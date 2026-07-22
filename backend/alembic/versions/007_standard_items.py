"""standard items, aliases and cost versions"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "standard_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("category", sa.String(128)),
        sa.Column("unit", sa.String(32)),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "code", name="uq_standard_items_org_code"),
    )
    op.create_index("ix_standard_items_organization_id", "standard_items", ["organization_id"])

    op.create_table(
        "standard_item_aliases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("standard_item_id", UUID(as_uuid=True), sa.ForeignKey("standard_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_text", sa.String(256), nullable=False),
        sa.Column("alias_source", sa.String(32), nullable=False, server_default="MANUAL"),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("approved_at", sa.Date),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("standard_item_id", "alias_text", name="uq_standard_item_aliases"),
    )
    op.create_index("ix_standard_item_aliases_organization_id", "standard_item_aliases", ["organization_id"])

    op.create_table(
        "standard_cost_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("standard_item_id", UUID(as_uuid=True), sa.ForeignKey("standard_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer, nullable=False),
        sa.Column("effective_from", sa.Date),
        sa.Column("effective_to", sa.Date),
        sa.Column("unit_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("cost_basis", sa.String(32), nullable=False, server_default="STANDARD"),
        sa.Column("source", sa.String(32)),
        sa.Column("notes", sa.Text),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("standard_item_id", "version_no", name="uq_standard_cost_versions"),
    )
    op.create_index("ix_standard_cost_versions_organization_id", "standard_cost_versions", ["organization_id"])


def downgrade():
    op.drop_table("standard_cost_versions")
    op.drop_table("standard_item_aliases")
    op.drop_table("standard_items")
