import hashlib
import os
import uuid as _uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import StorageRoot, Document, DocumentLink
from app.models.approval import AuditLog
from app.config import get_settings

settings = get_settings()
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".csv", ".msg", ".eml"}


class PathTraversalException(Exception):
    pass


def _resolve_safe_path(storage_root: StorageRoot, relative_path: str) -> Path:
    """Resolve a relative path within a storage root, rejecting traversal attempts."""
    base = Path(storage_root.base_path).resolve()
    target = (base / relative_path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise PathTraversalException(f"Path '{relative_path}' escapes storage root")
    return target


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def save_upload(
    upload: UploadFile,
    project_id: _uuid.UUID,
    org_code: str,
    project_code: str,
    document_type: str,
    db: AsyncSession,
    user_id: _uuid.UUID,
) -> Document:
    # Validate extension
    ext = Path(upload.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed")

    # Read content
    content = await upload.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="File too large")

    # Compute hash
    sha = compute_sha256_bytes(content)

    # Get or create storage root
    result = await db.execute(select(StorageRoot).where(StorageRoot.is_active == True))
    root = result.scalar_one_or_none()
    if not root:
        root = StorageRoot(
            code="default",
            base_path=settings.FILE_STORAGE_ROOT, storage_type="LOCAL",
            is_active=True, read_only=False, created_by=user_id, updated_by=user_id,
        )
        db.add(root)
        await db.flush()

    # Build safe relative path
    stored_name = f"{_uuid.uuid4()}{ext}"
    relative_path = f"{org_code}/{project_code}/{document_type.lower()}s/{stored_name}"

    # Verify path safety
    _resolve_safe_path(root, relative_path)

    # Write file
    full_path = _resolve_safe_path(root, relative_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(content)

    # Create document record
    doc = Document(
        project_id=project_id, storage_root_id=root.id,
        original_name=upload.filename, stored_name=stored_name, relative_path=relative_path,
        document_type=document_type, mime_type=upload.content_type or "application/octet-stream",
        file_extension=ext, size_bytes=len(content), sha256=sha,
        is_original=True, is_immutable=True, uploaded_by=user_id,
        created_by=user_id, updated_by=user_id,
    )
    db.add(doc)
    await db.flush()

    # Create project link
    link = DocumentLink(document_id=doc.id, link_type="PROJECT", linked_id=project_id)
    db.add(link)
    db.add(AuditLog(
        user_id=user_id,
        action="UPLOAD",
        resource_type="document",
        resource_id=str(doc.id),
        detail={"document_type": document_type, "original_name": doc.original_name, "project_id": str(project_id)},
    ))
    await db.commit()
    await db.refresh(doc)
    return doc


async def get_file_path(doc: Document, db: AsyncSession) -> Path:
    """Get the filesystem path for a document, verifying containment."""
    result = await db.execute(select(StorageRoot).where(StorageRoot.id == doc.storage_root_id))
    root = result.scalar_one()
    return _resolve_safe_path(root, doc.relative_path)
