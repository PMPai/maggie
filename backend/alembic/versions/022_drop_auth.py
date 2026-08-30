"""drop auth tables and organization_id columns

Revision ID: 022_drop_auth
Revises: 021_drop_matching
Create Date: 2026-08-30
"""
from alembic import op

revision = "022_drop_auth"
down_revision = "021_drop_matching"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop FK constraints that reference auth tables
    op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_project_manager_id_fkey")
    # Drop project_members
    op.execute("DROP TABLE IF EXISTS project_members")
    # Drop auth tables (CASCADE to handle FK dependencies)
    op.execute("DROP TABLE IF EXISTS user_groups CASCADE")
    op.execute("DROP TABLE IF EXISTS group_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS groups CASCADE")
    op.execute("DROP TABLE IF EXISTS user_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS roles CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS organizations CASCADE")
    # Drop project_manager_id column from projects
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS project_manager_id")
    # Remove organization_id columns from all business tables
    org_tables = [
        "projects", "companies", "contracts", "contract_versions",
        "contract_items", "payment_rules", "payment_applications",
        "payment_application_lines", "milestone_events", "retention_entries",
        "variations", "variation_lines", "deductions",
        "invoices", "invoice_application_links",
        "collections", "collection_allocations",
        "financial_adjustments", "approval_workflows", "approval_steps",
        "approvals", "audit_logs", "documents", "storage_roots",
        "document_links", "document_templates", "generated_documents",
    ]
    for table in org_tables:
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS organization_id")


def downgrade() -> None:
    pass
