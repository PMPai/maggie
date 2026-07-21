"""billing tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from app.models.billing import ApplicationStatus, RetentionEntryType

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_version_id", UUID(as_uuid=True), sa.ForeignKey("contract_versions.id"), nullable=False),
        sa.Column("application_no", sa.String(64), nullable=False),
        sa.Column("period_no", sa.Integer, nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("application_date", sa.Date, nullable=False),
        sa.Column("status", sa.Enum(ApplicationStatus), nullable=False, server_default="DRAFT"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="TWD"),
        sa.Column("gross_completed_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("retention_held_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("retention_released_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("deduction_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("taxable_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("invoice_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("approved_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("revision_no", sa.Integer, nullable=False, server_default="0"),
        sa.Column("supersedes_application_id", UUID(as_uuid=True), sa.ForeignKey("payment_applications.id")),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("posted_action_id", sa.String(64)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("contract_id", "application_no", "revision_no", name="uq_payment_applications"),
    )
    op.create_index("ix_payment_applications_project_id", "payment_applications", ["project_id"])
    op.create_index("ix_payment_applications_contract_id", "payment_applications", ["contract_id"])

    op.create_table(
        "payment_application_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("payment_application_id", UUID(as_uuid=True), sa.ForeignKey("payment_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_item_id", UUID(as_uuid=True), sa.ForeignKey("contract_items.id"), nullable=False),
        sa.Column("contract_version_id", UUID(as_uuid=True), sa.ForeignKey("contract_versions.id"), nullable=False),
        sa.Column("description_snapshot", sa.Text, nullable=False),
        sa.Column("unit_snapshot", sa.String(32)),
        sa.Column("unit_price_snapshot", sa.Numeric(18, 2), nullable=False),
        sa.Column("previous_approved_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("current_claimed_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("current_approved_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("cumulative_approved_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("current_completed_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("retention_rate", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("retention_held", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("retention_released", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("deduction_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("taxable_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("calculation_method", sa.String(32), nullable=False, server_default="QUANTITY"),
        sa.Column("user_explanation", sa.Text),
        sa.Column("validation_status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payment_app_lines_app_id", "payment_application_lines", ["payment_application_id"])

    op.create_table(
        "milestone_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_item_id", UUID(as_uuid=True), sa.ForeignKey("contract_items.id")),
        sa.Column("milestone_name", sa.String(128), nullable=False),
        sa.Column("milestone_type", sa.String(32), nullable=False),
        sa.Column("event_date", sa.Date),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "retention_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_application_id", UUID(as_uuid=True), sa.ForeignKey("payment_applications.id")),
        sa.Column("contract_item_id", UUID(as_uuid=True), sa.ForeignKey("contract_items.id")),
        sa.Column("entry_type", sa.Enum(RetentionEntryType), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("reversal_of_id", UUID(as_uuid=True), sa.ForeignKey("retention_entries.id")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_retention_entries_project_id", "retention_entries", ["project_id"])
    op.create_index("ix_retention_entries_contract_id", "retention_entries", ["contract_id"])


def downgrade():
    op.drop_table("retention_entries")
    op.drop_table("milestone_events")
    op.drop_table("payment_application_lines")
    op.drop_table("payment_applications")
