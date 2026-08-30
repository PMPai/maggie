"""add unit_cost to contract_items

Revision ID: 023_add_unit_cost
Revises: 022_drop_auth
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "023_add_unit_cost"
down_revision = "022_drop_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contract_items", sa.Column("unit_cost", sa.Numeric(18, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("contract_items", "unit_cost")
