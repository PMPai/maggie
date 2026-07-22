"""document templates and generated documents"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id")),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("template_type", sa.String(32), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("effective_from", sa.Date),
        sa.Column("effective_to", sa.Date),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_templates_organization_id", "document_templates", ["organization_id"])

    op.create_table(
        "generated_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("payment_application_id", UUID(as_uuid=True), sa.ForeignKey("payment_applications.id")),
        sa.Column("document_template_id", UUID(as_uuid=True), sa.ForeignKey("document_templates.id")),
        sa.Column("doc_type", sa.String(16), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("version_no", sa.Integer, nullable=False, server_default="1"),
        sa.Column("generated_by", UUID(as_uuid=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_generated_documents_organization_id", "generated_documents", ["organization_id"])
    op.create_index("ix_generated_documents_payment_application_id", "generated_documents", ["payment_application_id"])


def downgrade():
    op.drop_table("generated_documents")
    op.drop_table("document_templates")
