from datetime import datetime
from pydantic import BaseModel, Field


class CustomerBase(BaseModel):
    customer_number: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = None
    email: str | None = None
    street: str | None = None
    city: str | None = None
    zip: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(CustomerBase):
    pass


class CustomerRead(CustomerBase):
    id: int
    uuid: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
