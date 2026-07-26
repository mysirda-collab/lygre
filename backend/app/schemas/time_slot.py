from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TimeSlotBase(BaseModel):
    start: datetime
    end: datetime
    capacity: int = Field(default=1, ge=1)
    enabled: bool = True
    blocked: bool = False
    technician: str | None = Field(default=None, max_length=150)
    title: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    installation_type: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class TimeSlotCreate(TimeSlotBase):
    pass


class TimeSlotUpdate(BaseModel):
    start: datetime | None = None
    end: datetime | None = None
    capacity: int | None = Field(default=None, ge=1)
    enabled: bool | None = None
    blocked: bool | None = None
    technician: str | None = Field(default=None, max_length=150)
    title: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    installation_type: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_optional_range(self):
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class TimeSlotBlockRequest(BaseModel):
    blocked: bool = True
    disable: bool = True


class TimeSlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start: datetime
    end: datetime
    capacity: int
    enabled: bool
    blocked: bool
    technician: str | None
    title: str | None
    location: str | None
    note: str | None
    installation_type: str | None
    occupied_capacity: int = Field(default=0, ge=0)
    remaining_capacity: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class TimeSlotListResponse(BaseModel):
    items: list[TimeSlotRead]


class TimeSlotAvailabilityRead(BaseModel):
    slot: TimeSlotRead
    remaining_capacity: int = Field(ge=0)


class TimeSlotAvailabilityListResponse(BaseModel):
    items: list[TimeSlotAvailabilityRead]
