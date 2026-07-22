"""db views for reporting"""
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE OR REPLACE VIEW v_contract_item_balances AS
        SELECT ci.id, ci.contract_version_id, cv.contract_id, ci.line_no, ci.source_description, ci.unit,
               ci.contract_quantity,
               COALESCE(SUM(v.quantity_delta) FILTER (WHERE v.status = 'APPROVED'), 0) AS variation_qty,
               ci.contract_quantity + COALESCE(SUM(v.quantity_delta) FILTER (WHERE v.status = 'APPROVED'), 0) AS available_qty,
               COALESCE(SUM(pal.cumulative_approved_quantity), 0) AS cumulative_approved
        FROM contract_items ci
        LEFT JOIN contract_versions cv ON cv.id = ci.contract_version_id
        LEFT JOIN variations v ON v.contract_item_id = ci.id
        LEFT JOIN payment_application_lines pal ON pal.contract_item_id = ci.id
        GROUP BY ci.id, ci.contract_version_id, cv.contract_id, ci.line_no, ci.source_description, ci.unit, ci.contract_quantity
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW v_project_commercial_summary AS
        SELECT p.id AS project_id, p.internal_project_code, p.project_name,
               COALESCE(SUM(cv.amount_inc_tax), 0) AS contract_value,
               COALESCE(SUM(pa.invoice_amount), 0) AS invoiced_to_date,
               COALESCE(SUM(pa.gross_completed_amount), 0) AS gross_completed,
               COALESCE(SUM(pa.retention_held_amount) - SUM(pa.retention_released_amount), 0) AS retention_held
        FROM projects p
        LEFT JOIN contracts c ON c.project_id = p.id
        LEFT JOIN contract_versions cv ON cv.contract_id = c.id AND cv.status = 'APPROVED'
        LEFT JOIN payment_applications pa ON pa.contract_id = c.id AND pa.status = 'POSTED'
        GROUP BY p.id, p.internal_project_code, p.project_name
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW v_retention_balances AS
        SELECT contract_id,
               SUM(CASE WHEN entry_type = 'HOLD' THEN amount ELSE 0 END) AS total_held,
               SUM(CASE WHEN entry_type = 'RELEASE' THEN amount ELSE 0 END) AS total_released,
               SUM(CASE WHEN entry_type = 'ADJUSTMENT' THEN amount ELSE 0 END) AS total_adjustment,
               SUM(CASE WHEN entry_type = 'HOLD' THEN amount ELSE 0 END) -
               SUM(CASE WHEN entry_type = 'RELEASE' THEN amount ELSE 0 END) AS balance
        FROM retention_entries
        GROUP BY contract_id
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW v_uninvoiced_approved_amounts AS
        SELECT pa.id AS application_id, pa.application_no, pa.contract_id, pa.invoice_amount,
               COALESCE(SUM(ial.linked_amount), 0) AS linked_amount,
               pa.invoice_amount - COALESCE(SUM(ial.linked_amount), 0) AS uninvoiced_amount
        FROM payment_applications pa
        LEFT JOIN invoice_application_links ial ON ial.payment_application_id = pa.id
        WHERE pa.status = 'POSTED'
        GROUP BY pa.id, pa.application_no, pa.contract_id, pa.invoice_amount
        HAVING pa.invoice_amount - COALESCE(SUM(ial.linked_amount), 0) > 0.01
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW v_invoice_outstanding AS
        SELECT i.id AS invoice_id, i.invoice_no, i.contract_id, i.amount_inc_tax,
               COALESCE(SUM(ca.allocated_amount), 0) AS allocated_amount,
               i.amount_inc_tax - COALESCE(SUM(ca.allocated_amount), 0) AS outstanding_amount
        FROM invoices i
        LEFT JOIN collection_allocations ca ON ca.invoice_id = i.id
        WHERE i.status IN ('ISSUED', 'PARTIALLY_PAID')
        GROUP BY i.id, i.invoice_no, i.contract_id, i.amount_inc_tax
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW v_collection_variances AS
        SELECT i.id AS invoice_id, i.invoice_no, i.amount_inc_tax AS expected,
               COALESCE(SUM(ca.allocated_amount), 0) AS received,
               i.amount_inc_tax - COALESCE(SUM(ca.allocated_amount), 0) AS variance
        FROM invoices i
        LEFT JOIN collection_allocations ca ON ca.invoice_id = i.id
        GROUP BY i.id, i.invoice_no, i.amount_inc_tax
        HAVING ABS(i.amount_inc_tax - COALESCE(SUM(ca.allocated_amount), 0)) > 0.01
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW v_cost_margin_analysis AS
        SELECT p.id AS project_id, p.internal_project_code,
               COALESCE(SUM(cv.amount_inc_tax), 0) AS contract_value,
               COALESCE(SUM(scv.unit_cost * ci.contract_quantity), 0) AS standard_cost,
               COALESCE(SUM(cv.amount_inc_tax), 0) - COALESCE(SUM(scv.unit_cost * ci.contract_quantity), 0) AS margin
        FROM projects p
        LEFT JOIN contracts c ON c.project_id = p.id
        LEFT JOIN contract_versions cv ON cv.contract_id = c.id AND cv.status = 'APPROVED'
        LEFT JOIN contract_items ci ON ci.contract_version_id = cv.id
        LEFT JOIN item_mappings im ON im.contract_item_id = ci.id AND im.status = 'APPROVED'
        LEFT JOIN standard_cost_versions scv ON scv.standard_item_id = im.standard_item_id AND scv.status = 'ACTIVE'
        GROUP BY p.id, p.internal_project_code
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW v_pending_exceptions AS
        SELECT 'VARIATION' AS type, v.id AS resource_id, v.variation_no AS description, v.status::text AS status
        FROM variations v WHERE v.status IN ('DRAFT', 'UNDER_REVIEW')
        UNION ALL
        SELECT 'MAPPING' AS type, im.id AS resource_id, CONCAT('Mapping ', im.id) AS description, im.status::text
        FROM item_mappings im WHERE im.status IN ('SUGGESTED', 'PENDING_REVIEW', 'NEEDS_CLARIFICATION')
        UNION ALL
        SELECT 'DEDUCTION' AS type, d.id AS resource_id, d.deduction_no AS description, d.status::text
        FROM deductions d WHERE d.status = 'DRAFT'
        UNION ALL
        SELECT 'VARIANCE' AS type, i.id AS resource_id, i.invoice_no AS description, 'UNRECONCILED' AS status
        FROM invoices i
        LEFT JOIN collection_allocations ca ON ca.invoice_id = i.id
        GROUP BY i.id, i.invoice_no, i.amount_inc_tax
        HAVING ABS(i.amount_inc_tax - COALESCE(SUM(ca.allocated_amount), 0)) > 0.01
        """
    )


def downgrade():
    op.execute("DROP VIEW IF EXISTS v_pending_exceptions")
    op.execute("DROP VIEW IF EXISTS v_cost_margin_analysis")
    op.execute("DROP VIEW IF EXISTS v_collection_variances")
    op.execute("DROP VIEW IF EXISTS v_invoice_outstanding")
    op.execute("DROP VIEW IF EXISTS v_uninvoiced_approved_amounts")
    op.execute("DROP VIEW IF EXISTS v_retention_balances")
    op.execute("DROP VIEW IF EXISTS v_project_commercial_summary")
    op.execute("DROP VIEW IF EXISTS v_contract_item_balances")
