"""drop auth tables and organization_id columns

Revision ID: 022_drop_auth
Revises: 021_drop_matching
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "022_drop_auth"
down_revision = "021_drop_matching"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop project_members
    op.drop_table("project_members")
    # Drop auth tables
    op.drop_table("user_groups")
    op.drop_table("group_roles")
    op.drop_table("groups")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("organizations")
    # Remove organization_id columns from all business tables
    for table in [
        "projects", "companies", "contracts", "contract_versions",
        "contract_items", "payment_rules", "payment_applications",
        "payment_application_lines", "milestone_events", "retention_entries",
        "variations", "variation_lines", "deductions",
        "invoices", "invoice_application_links",
        "collections", "collection_allocations",
        "financial_adjustments", "approval_workflows", "approval_steps",
        "approvals", "audit_logs", "documents", "storage_roots",
        "document_links", "document_templates", "generated_documents",
    ]:
        try:
            op.drop_column(table, "organization_id")
        except Exception:
            pass  # column may not exist on some tables


def downgrade() -> None:
    pass
