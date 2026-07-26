from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.services.notification_service import NotificationService
from app.services.reservation_service import ReservationService


def utc_now() -> datetime:
    return datetime.now(UTC)


class SchedulerService:
    def __init__(
        self,
        db: Session,
        notification_service: NotificationService,
        reservation_service: ReservationService | None = None,
    ) -> None:
        self.db = db
        self.notification_service = notification_service
        self.reservation_service = reservation_service or ReservationService(db)

    def process_due_reminders(self, *, now: datetime | None = None, reminder_window_hours: int = 24) -> int:
        current = now or utc_now()
        reservation_ids = self.reservation_service.list_due_reminder_reservation_ids(
            now=current,
            reminder_window_hours=reminder_window_hours,
        )
        sent = 0
        for reservation_id in reservation_ids:
            reservation = self.reservation_service.get_reservation(reservation_id)
            sms = self.notification_service.send_reservation_reminder(reservation)
            if sms.status == "sent":
                sent += 1
        return sent
