"""drop matching tables

Revision ID: 021_drop_matching
Revises: 020
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "021_drop_matching"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_cost_margin_analysis CASCADE")
    op.execute("DROP VIEW IF EXISTS v_pending_exceptions CASCADE")
    op.drop_table("matching_reviews")
    op.drop_table("mapping_components")
    op.drop_table("item_mappings")
    op.drop_table("standard_cost_versions")
    op.drop_table("standard_item_aliases")
    op.drop_table("standard_items")


def downgrade() -> None:
    pass
