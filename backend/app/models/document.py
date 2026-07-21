import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, OrganizationMixin, AuditMixin, SoftDeleteMixin


class StorageRoot(Base, TimestampMixin, OrganizationMixin, AuditMixin):
    __tablename__ = "storage_roots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    base_path: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_type: Mapped[str] = mapped_column(String(16), nullable=False, default="LOCAL")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    health_status: Mapped[str] = mapped_column(String(16), nullable=False, default="HEALTHY")


class Document(Base, TimestampMixin, OrganizationMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    storage_root_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storage_roots.id"), nullable=False)
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(512), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)  # CONTRACT, APPLICATION, INVOICE, etc.
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_original: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    ocr_status: Mapped[str] = mapped_column(String(16), nullable=False, default="NOT_REQUIRED")
    extraction_status: Mapped[str] = mapped_column(String(16), nullable=False, default="NOT_REQUIRED")
    retention_status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")


class DocumentLink(Base, TimestampMixin):
    __tablename__ = "document_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    link_type: Mapped[str] = mapped_column(String(32), nullable=False)  # PROJECT, CONTRACT, CONTRACT_VERSION, CONTRACT_ITEM, APPLICATION, etc.
    linked_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
