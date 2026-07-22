"""collections and collection_allocations"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from app.models.collection import CollectionStatus

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "collections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receipt_no", sa.String(64), nullable=False),
        sa.Column("receipt_date", sa.Date),
        sa.Column("amount_received", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_method", sa.String(32), nullable=False, server_default="BANK_TRANSFER"),
        sa.Column("bank_reference", sa.String(128)),
        sa.Column("notes", sa.Text),
        sa.Column("status", sa.Enum(CollectionStatus), nullable=False, server_default="CONFIRMED"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("contract_id", "receipt_no", name="uq_collections_contract_no"),
    )
    op.create_index("ix_collections_project_id", "collections", ["project_id"])
    op.create_index("ix_collections_contract_id", "collections", ["contract_id"])

    op.create_table(
        "collection_allocations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("collection_id", UUID(as_uuid=True), sa.ForeignKey("collections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_collection_allocations_collection_id", "collection_allocations", ["collection_id"])
    op.create_index("ix_collection_allocations_invoice_id", "collection_allocations", ["invoice_id"])


def downgrade():
    op.drop_table("collection_allocations")
    op.drop_table("collections")
