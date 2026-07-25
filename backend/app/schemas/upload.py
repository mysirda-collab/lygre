from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UploadCreateResponse(BaseModel):
    id: int
    created_ids: list[int] = Field(default_factory=list)
    created_count: int = 1
    source_document_id: str | None = None
    source_original_filename: str | None = None
    total_pages: int | None = None


class UploadRead(BaseModel):
    id: int
    original_filename: str
    stored_filename: str
    file_path: str
    content_type: str | None = None
    file_size: int
    uploaded_at: datetime
    status: str = Field(default="Hotovo")
    error_message: str | None = None
    extracted_text: str | None = None
    parsed_data: dict[str, Any] | None = None
    job_id: int | None = None
    processing_status: str = Field(default="Hotovo")
    source_document_id: str | None = None
    source_original_filename: str | None = None
    source_stored_filename: str | None = None
    source_file_path: str | None = None
    page_number: int | None = None
    total_pages: int | None = None

    class Config:
        from_attributes = True
