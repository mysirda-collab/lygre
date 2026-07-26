from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TimeSlot(Base):
    __tablename__ = "time_slots"
    __table_args__ = (
        Index("ix_time_slots_start_end", "start", "end"),
        Index("ix_time_slots_enabled_blocked_start", "enabled", "blocked", "start"),
        Index("ix_time_slots_technician_start_end", "technician", "start", "end"),
        Index("ix_time_slots_location_start", "location", "start"),
        CheckConstraint('"start" < "end"', name="ck_time_slots_start_before_end"),
        CheckConstraint("capacity >= 1", name="ck_time_slots_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    technician: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # additional fields requested
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    installation_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    reservations = relationship("Reservation", back_populates="slot")
