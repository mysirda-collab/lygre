from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)

from sqlalchemy import Boolean, DateTime, String, Integer, Float, ForeignKey, Text
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
    status_history = relationship("JobStatusHistory", back_populates="job", cascade="all, delete-orphan")
    note_entries = relationship("JobNote", back_populates="job", cascade="all, delete-orphan")
    # Attachment link removed to prefer single-direction relation via Upload.job_id


class JobStatusHistory(Base):
    __tablename__ = "job_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    job = relationship("Job", back_populates="status_history")


class JobNote(Base):
    __tablename__ = "job_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    job = relationship("Job", back_populates="note_entries")
    author = relationship("User", foreign_keys=[author_user_id])
    updated_by_user = relationship("User", foreign_keys=[updated_by_user_id])

    @property
    def author_name(self) -> str | None:
        return self.author.full_name if self.author else None

    @property
    def updated_by_name(self) -> str | None:
        return self.updated_by_user.full_name if self.updated_by_user else None
