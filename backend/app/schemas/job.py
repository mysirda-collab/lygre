from datetime import datetime
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

JOB_STATUSES = {
    "Nová", "Vyžaduje kontrolu", "Klient nekontaktován", "Klient kontaktován",
    "Čeká na termín", "Termín naplánován", "Probíhá realizace", "Dokončeno", "Zrušeno",
    # Legacy API values remain valid for backward compatibility.
    "new", "scheduled", "done", "cancelled",
}


class JobBase(BaseModel):
    job_number: str = Field(min_length=1, max_length=50)
    status: str = Field(default="new", max_length=50)
    priority: str = Field(default="medium", max_length=20)
    customer_name: str = Field(min_length=1, max_length=1000)
    company: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    street: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)
    zip: Optional[str] = Field(default=None, max_length=20)
    installation_date: Optional[datetime] = None
    technician: Optional[str] = Field(default=None, max_length=150)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in JOB_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(JOB_STATUSES))}")
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        allowed = {"low", "medium", "high", "urgent"}
        normalized = value.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"priority must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("job_number")
    @classmethod
    def validate_job_number(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("job_number must not be empty")
        return cleaned

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("customer_name must not be empty")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned):
            raise ValueError("email has invalid format")
        return cleaned

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not re.fullmatch(r"[0-9+()\-\s]{6,25}", cleaned):
            raise ValueError("phone has invalid format")
        return cleaned

    @field_validator("zip")
    @classmethod
    def validate_zip(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not re.fullmatch(r"\d{3}\s?\d{2}", cleaned):
            raise ValueError("zip must be in format 12345 or 123 45")
        return cleaned

    @field_validator("company", "street", "city", "technician", "notes")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class JobCreate(JobBase):
    customer_id: int | None = None
    order_number: str | None = None
    parser_confidence: float = 0.0


class JobUpdate(JobBase):
    pass


class JobRead(JobBase):
    id: int
    created_at: datetime
    updated_at: datetime
    customer_id: int | None = None
    order_number: str | None = None
    parser_confidence: float = 0.0

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int


class JobAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    uploaded_at: datetime
    file_size: int
    status: str
    source_document_id: str | None = None
    source_original_filename: str | None = None
    page_number: int | None = None
    total_pages: int | None = None
    is_primary: bool = False
    parsed_data: dict[str, Any] | None = None
    error_message: str | None = None


class JobAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    details: str | None = None
    created_at: datetime


class JobStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    previous_status: str | None
    new_status: str
    changed_at: datetime


class JobNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=5000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Note must not be empty")
        return text


class JobNoteUpdate(JobNoteCreate):
    pass


class JobStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_job_status(cls, value: str) -> str:
        if value not in JOB_STATUSES:
            raise ValueError("Invalid job status")
        return value


class JobNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    author_user_id: int | None
    author_name: str | None
    created_at: datetime
    updated_at: datetime | None
    updated_by_user_id: int | None
    updated_by_name: str | None


class JobDetailResponse(BaseModel):
    job: JobRead
    customer: dict[str, Any] | None = None
    attachments: list[JobAttachmentRead]
    audit_logs: list[JobAuditLogRead]
    status_history: list[JobStatusHistoryRead] = []
    notes: list[JobNoteRead] = []
    primary_attachment_id: int | None = None


class DashboardSummaryResponse(BaseModel):
    status_counts: dict[str, int]
    recent_jobs: list[JobRead]
    overdue_jobs: list[JobRead]
    today_installations: list[JobRead]
    pipeline_counts: dict[str, int] = {}
