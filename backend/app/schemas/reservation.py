from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.time_slot import TimeSlotAvailabilityRead


class ReservationCreateRequest(BaseModel):
    job_id: int = Field(gt=0)
    customer_id: int = Field(gt=0)


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    customer_id: int
    slot_id: int | None
    token: str
    token_expires_at: datetime | None
    token_used: bool
    status: str
    reminder_sent_at: datetime | None
    confirmation_sent_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReservationPublicStatus(BaseModel):
    reservation_id: int
    status: str
    token_expires_at: datetime | None
    token_used: bool


class ReservationConfirmRequest(BaseModel):
    token: str = Field(min_length=8, max_length=128)
    slot_id: int = Field(gt=0)


class ReservationAvailabilityListResponse(BaseModel):
    items: list[TimeSlotAvailabilityRead]


class ReservationPublicSelectedSlot(BaseModel):
    id: int
    start: datetime
    end: datetime
    title: str | None
    location: str | None
    installation_type: str | None


class ReservationPublicContext(BaseModel):
    customer_name: str | None
    job_number: str | None
    reservation_status: str
    token_expires_at: datetime | None
    token_used: bool
    can_confirm: bool
    selected_slot: ReservationPublicSelectedSlot | None
