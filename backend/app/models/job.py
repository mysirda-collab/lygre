from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)

from sqlalchemy import Boolean, DateTime, String, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from app.models.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    customer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    company: Mapped[str | None] = mapped_column(String(150), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    installation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    technician: Mapped[str | None] = mapped_column(String(150), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    order_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parser_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    customer = relationship("Customer", back_populates="jobs")
    reservations = relationship("Reservation", back_populates="job")
    sms_logs = relationship("SmsLog", back_populates="job")
    # Attachment link removed to prefer single-direction relation via Upload.job_id
