from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.reservation import Reservation
from app.models.time_slot import TimeSlot
from app.services.notification_service import NotificationService


def utc_now() -> datetime:
    return datetime.now(UTC)


class SchedulerService:
    def __init__(self, db: Session, notification_service: NotificationService) -> None:
        self.db = db
        self.notification_service = notification_service

    def process_due_reminders(self, *, now: datetime | None = None, reminder_window_hours: int = 24) -> int:
        current = now or utc_now()
        horizon = current + timedelta(hours=reminder_window_hours)

        stmt: Select[tuple[Reservation]] = (
            select(Reservation)
            .join(TimeSlot, TimeSlot.id == Reservation.slot_id)
            .where(
                Reservation.status == "confirmed",
                Reservation.reminder_sent_at.is_(None),
                TimeSlot.start >= current,
                TimeSlot.start <= horizon,
            )
            .order_by(TimeSlot.start.asc())
        )

        reservations = self.db.scalars(stmt).all()
        sent = 0
        for reservation in reservations:
            sms = self.notification_service.send_reservation_reminder(reservation)
            if sms.status == "sent":
                sent += 1
        return sent
