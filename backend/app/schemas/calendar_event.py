from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.calendar_event import CalendarEventType


class CalendarEventTechnicianSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str


class CalendarEventJobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_number: str
    status: str
    customer_name: str


class CalendarEventBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    event_type: str = Field(default=CalendarEventType.INSTALLATION, max_length=50)
    starts_at: datetime
    ends_at: datetime
    job_id: int = Field(gt=0)
    technician_id: int = Field(gt=0)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be empty")
        return cleaned

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {
            CalendarEventType.INSTALLATION,
            CalendarEventType.SERVICE,
            CalendarEventType.INSPECTION,
        }
        if normalized not in allowed:
            raise ValueError("event_type must be one of: installation, service, inspection")
        return normalized

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_range(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be greater than starts_at")
        return self


class CalendarEventCreate(CalendarEventBase):
    pass


class CalendarEventUpdate(CalendarEventBase):
    pass


class CalendarEventReschedule(BaseModel):
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_range(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be greater than starts_at")
        return self


class CalendarEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    event_type: str
    starts_at: datetime
    ends_at: datetime
    job_id: int
    technician_id: int
    notes: str | None
    created_at: datetime
    updated_at: datetime
    job: CalendarEventJobSummary
    technician: CalendarEventTechnicianSummary


class CalendarEventListResponse(BaseModel):
    items: list[CalendarEventRead]


class TechnicianRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
