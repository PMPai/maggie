"""add special_fund_description to projects"""
from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("special_fund_description", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("projects", "special_fund_description")