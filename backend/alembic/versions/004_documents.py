"""documents and storage"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "storage_roots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("base_path", sa.String(512), nullable=False),
        sa.Column("storage_type", sa.String(16), nullable=False, server_default="LOCAL"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("read_only", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("health_status", sa.String(16), nullable=False, server_default="HEALTHY"),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id")),
        sa.Column("storage_root_id", UUID(as_uuid=True), sa.ForeignKey("storage_roots.id"), nullable=False),
        sa.Column("original_name", sa.String(512), nullable=False),
        sa.Column("stored_name", sa.String(512), nullable=False),
        sa.Column("relative_path", sa.String(1024), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_extension", sa.String(16), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("version_no", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_original", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_generated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_immutable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ocr_status", sa.String(16), nullable=False, server_default="NOT_REQUIRED"),
        sa.Column("extraction_status", sa.String(16), nullable=False, server_default="NOT_REQUIRED"),
        sa.Column("retention_status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_relative_path", "documents", ["relative_path"])

    op.create_table(
        "document_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("link_type", sa.String(32), nullable=False),
        sa.Column("linked_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_links_document_id", "document_links", ["document_id"])
    op.create_index("ix_document_links_linked_id", "document_links", ["linked_id"])


def downgrade():
    op.drop_table("document_links")
    op.drop_table("documents")
    op.drop_table("storage_roots")
