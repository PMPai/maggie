from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    original_name: str
    document_type: str
    mime_type: str
    size_bytes: int
    sha256: str
    version_no: int
    is_original: bool
    is_immutable: bool
    ocr_status: str
    ocr_text: str | None = None
    uploaded_at: str | None = None
    project_id: str | None = None
