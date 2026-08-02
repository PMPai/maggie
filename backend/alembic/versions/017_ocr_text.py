"""add documents.ocr_text column"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("ocr_text", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("documents", "ocr_text")
