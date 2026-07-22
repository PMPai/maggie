"""deductions"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from app.models.deduction import DeductionType, TaxTreatment, DeductionStatus

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "deductions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_application_id", UUID(as_uuid=True), sa.ForeignKey("payment_applications.id")),
        sa.Column("deduction_no", sa.String(64), nullable=False),
        sa.Column("deduction_type", sa.Enum(DeductionType), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("reason", sa.Text),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_treatment", sa.Enum(TaxTreatment), nullable=False, server_default="TAXABLE"),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("effective_date", sa.Date),
        sa.Column("status", sa.Enum(DeductionStatus), nullable=False, server_default="DRAFT"),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("approved_at", sa.Date),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("contract_id", "deduction_no", name="uq_deductions_contract_no"),
    )
    op.create_index("ix_deductions_organization_id", "deductions", ["organization_id"])
    op.create_index("ix_deductions_project_id", "deductions", ["project_id"])
    op.create_index("ix_deductions_contract_id", "deductions", ["contract_id"])


def downgrade():
    op.drop_table("deductions")
