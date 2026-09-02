"""invoices and invoice_application_links"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from app.models.invoice import InvoiceType, InvoiceStatus

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_no", sa.String(64), nullable=False),
        sa.Column("invoice_type", sa.Enum(InvoiceType), nullable=False, server_default="STANDARD"),
        sa.Column("issue_date", sa.Date),
        sa.Column("due_date", sa.Date),
        sa.Column("amount_ex_tax", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("amount_inc_tax", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("tax_rate", sa.Numeric(10, 6), nullable=False, server_default="0.05"),
        sa.Column("status", sa.Enum(InvoiceStatus), nullable=False, server_default="PLANNED"),
        sa.Column("source", sa.String(32), nullable=False, server_default="MANUAL"),
        sa.Column("notes", sa.Text),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("contract_id", "invoice_no", name="uq_invoices_contract_no"),
        sa.CheckConstraint("amount_ex_tax + tax_amount = amount_inc_tax", name="ck_invoice_amounts"),
    )
    op.create_index("ix_invoices_project_id", "invoices", ["project_id"])
    op.create_index("ix_invoices_contract_id", "invoices", ["contract_id"])

    op.create_table(
        "invoice_application_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_application_id", UUID(as_uuid=True), sa.ForeignKey("payment_applications.id"), nullable=False),
        sa.Column("linked_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_invoice_app_links_invoice_id", "invoice_application_links", ["invoice_id"])


def downgrade():
    op.drop_table("invoice_application_links")
    op.drop_table("invoices")
