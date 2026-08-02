import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser, require_project_member
from app.models.project import Project
from app.models.document import Document
from app.services.file_service import save_upload, get_file_path
from app.schemas.document import DocumentResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Query(...),
    document_type: str = Query("CONTRACT"),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one()
    doc = await save_upload(
        upload=file, project_id=pid, org_code=current.organization_id.hex[:8],
        project_code=project.internal_project_code, document_type=document_type,
        db=db, organization_id=current.organization_id, user_id=current.user.id,
    )
    return DocumentResponse(
        id=str(doc.id), original_name=doc.original_name, document_type=doc.document_type,
        mime_type=doc.mime_type, size_bytes=doc.size_bytes, sha256=doc.sha256,
        version_no=doc.version_no, is_original=doc.is_original, is_immutable=doc.is_immutable,
        ocr_status=doc.ocr_status, ocr_text=doc.ocr_text,
        uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        project_id=str(doc.project_id) if doc.project_id else None,
    )


@router.get("/{document_id}/download")
async def download_document(document_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    did = uuid.UUID(document_id)
    result = await db.execute(select(Document).where(Document.id == did, Document.deleted_at.is_(None)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.project_id:
        await require_project_member(doc.project_id, current, db)
    file_path = await get_file_path(doc, db)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        path=str(file_path), media_type=doc.mime_type,
        filename=doc.original_name,
    )


@router.get("/{document_id}/preview")
async def preview_document(document_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    did = uuid.UUID(document_id)
    result = await db.execute(select(Document).where(Document.id == did, Document.deleted_at.is_(None)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.project_id:
        await require_project_member(doc.project_id, current, db)
    file_path = await get_file_path(doc, db)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(path=str(file_path), media_type=doc.mime_type)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    did = uuid.UUID(document_id)
    result = await db.execute(select(Document).where(Document.id == did, Document.deleted_at.is_(None)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.project_id:
        await require_project_member(doc.project_id, current, db)
    return DocumentResponse(
        id=str(doc.id), original_name=doc.original_name, document_type=doc.document_type,
        mime_type=doc.mime_type, size_bytes=doc.size_bytes, sha256=doc.sha256,
        version_no=doc.version_no, is_original=doc.is_original, is_immutable=doc.is_immutable,
        ocr_status=doc.ocr_status, ocr_text=doc.ocr_text,
        uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        project_id=str(doc.project_id) if doc.project_id else None,
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(project_id: str = Query(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(project_id)
    await require_project_member(pid, current, db)
    result = await db.execute(
        select(Document).where(Document.project_id == pid, Document.deleted_at.is_(None))
    )
    return [DocumentResponse(
        id=str(d.id), original_name=d.original_name, document_type=d.document_type,
        mime_type=d.mime_type, size_bytes=d.size_bytes, sha256=d.sha256,
        version_no=d.version_no, is_original=d.is_original, is_immutable=d.is_immutable,
        ocr_status=d.ocr_status, ocr_text=d.ocr_text,
        uploaded_at=d.uploaded_at.isoformat() if d.uploaded_at else None,
        project_id=str(d.project_id) if d.project_id else None,
    ) for d in result.scalars().all()]
