"""update collection + invoice status enums

Revision ID: 024_collection_invoice_status
Revises: 023_add_unit_cost
Create Date: 2026-08-30
"""
from alembic import op

revision = "024_collection_invoice_status"
down_revision = "023_add_unit_cost"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Collections: PENDING→PLANNED, REVERSED→CANCELLED, add RECEIVED
    op.execute("ALTER TYPE collectionstatus RENAME VALUE 'PENDING' TO 'PLANNED'")
    op.execute("ALTER TYPE collectionstatus RENAME VALUE 'REVERSED' TO 'CANCELLED'")
    op.execute("ALTER TYPE collectionstatus ADD VALUE IF NOT EXISTS 'RECEIVED'")
    # Invoices: DRAFT→PLANNED, add SENT, map PARTIALLY_PAID→ISSUED
    op.execute("ALTER TYPE invoicestatus RENAME VALUE 'DRAFT' TO 'PLANNED'")
    op.execute("ALTER TYPE invoicestatus ADD VALUE IF NOT EXISTS 'SENT'")
    op.execute("UPDATE invoices SET status='ISSUED' WHERE status='PARTIALLY_PAID'")


def downgrade() -> None:
    pass
