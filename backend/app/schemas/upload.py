from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UploadCreateResponse(BaseModel):
    id: int


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

    class Config:
        from_attributes = True
