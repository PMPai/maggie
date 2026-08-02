"""add expected_payment_date + actual_payment_date to contract_items"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contract_items", sa.Column("expected_payment_date", sa.Date(), nullable=True))
    op.add_column("contract_items", sa.Column("actual_payment_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("contract_items", "actual_payment_date")
    op.drop_column("contract_items", "expected_payment_date")
