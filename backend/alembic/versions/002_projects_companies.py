"""projects and companies"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# ProjectMemberRoleEnum was removed from the models in Phase 1 (auth strip).
# Inline the enum name so this historical migration still imports cleanly.
_ProjectMemberRoleEnum = sa.Enum("PROJECT_MANAGER", "COST_REVIEWER", "PROJECT_USER", "FINANCE_USER", name="projectmemberroleenum")

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("company_type", sa.String(32), nullable=False),
        sa.Column("tax_id", sa.String(32)),
        sa.Column("address", sa.Text),
        sa.Column("phone", sa.String(32)),
        sa.Column("contact_person", sa.String(128)),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "code", name="uq_companies_org_code"),
    )
    op.create_index("ix_companies_organization_id", "companies", ["organization_id"])

    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("internal_project_code", sa.String(32), nullable=False),
        sa.Column("project_name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("project_manager_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("start_date", sa.Date),
        sa.Column("planned_end_date", sa.Date),
        sa.Column("actual_end_date", sa.Date),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="TWD"),
        sa.Column("default_tax_rate", sa.Numeric(10, 6), nullable=False, server_default="0.05"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "internal_project_code", name="uq_projects_org_code"),
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])

    op.create_table(
        "project_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_role", _ProjectMemberRoleEnum, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members"),
    )

    op.create_table(
        "project_parties",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("role_in_project", sa.String(32), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("project_parties")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("companies")
