"""update v_invoice_outstanding view for new invoice statuses

Revision ID: 025_update_invoice_view
Revises: 024_collection_invoice_status
Create Date: 2026-08-30
"""
from alembic import op

revision = "025_update_invoice_view"
down_revision = "024_collection_invoice_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_invoice_outstanding")
    op.execute(
        """
        CREATE OR REPLACE VIEW v_invoice_outstanding AS
        SELECT i.id AS invoice_id, i.invoice_no, i.contract_id, i.amount_inc_tax,
               COALESCE(SUM(ca.allocated_amount), 0) AS allocated_amount,
               i.amount_inc_tax - COALESCE(SUM(ca.allocated_amount), 0) AS outstanding_amount
        FROM invoices i
        LEFT JOIN collection_allocations ca ON ca.invoice_id = i.id
        WHERE i.status IN ('ISSUED', 'SENT')
        GROUP BY i.id, i.invoice_no, i.contract_id, i.amount_inc_tax
        """
    )


def downgrade() -> None:
    pass
