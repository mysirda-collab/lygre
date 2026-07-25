from datetime import datetime
import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobBase(BaseModel):
    job_number: str = Field(min_length=1, max_length=50)
    status: str = Field(default="new", max_length=50)
    priority: str = Field(default="medium", max_length=20)
    customer_name: str = Field(min_length=1, max_length=150)
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
        allowed = {"new", "scheduled", "done", "cancelled"}
        if value not in allowed:
            raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
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
    pass


class JobUpdate(JobBase):
    pass


class JobRead(JobBase):
    id: int
    created_at: datetime
    updated_at: datetime

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


class JobAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    details: str | None = None
    created_at: datetime


class JobDetailResponse(BaseModel):
    job: JobRead
    attachments: list[JobAttachmentRead]
    audit_logs: list[JobAuditLogRead]


class DashboardSummaryResponse(BaseModel):
    status_counts: dict[str, int]
    recent_jobs: list[JobRead]
    overdue_jobs: list[JobRead]
    today_installations: list[JobRead]
