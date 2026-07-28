from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.crud.upload import get_first_waiting_upload, update_upload
from app.services.job_creation_service import JobCreationService
from app.services.notification_service import NotificationService
from app.services.reservation_service import ReservationService

logger = logging.getLogger(__name__)


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

    #
    # Reservation reminders
    #
    def process_due_reminders(
        self,
        *,
        now: datetime | None = None,
        reminder_window_hours: int = 24,
    ) -> int:
        current = now or utc_now()

        reservation_ids = (
            self.reservation_service.list_due_reminder_reservation_ids(
                now=current,
                reminder_window_hours=reminder_window_hours,
            )
        )

        sent = 0

        for reservation_id in reservation_ids:
            reservation = self.reservation_service.get_reservation(reservation_id)
            sms = self.notification_service.send_reservation_reminder(reservation)

            if sms.status == "sent":
                sent += 1

        return sent

    #
    # Background PDF processing
    #
    def process_waiting_uploads(self) -> int:

        upload = get_first_waiting_upload(self.db)

        if upload is None:
            return 0

        logger.info(
            "Processing upload id=%s page=%s",
            upload.id,
            upload.page_number,
        )

        update_upload(
            self.db,
            upload,
            status="Zpracovává se",
            processing_status="PROCESSING",
            error_message=None,
        )

        try:
            JobCreationService(self.db).process_upload(
                upload,
                upload.file_path,
            )

            update_upload(
                self.db,
                upload,
                status="Hotovo",
                processing_status="DONE",
            )

            logger.info("Upload %s finished", upload.id)

            return 1

        except Exception as exc:

            logger.exception("Upload %s failed", upload.id)

            update_upload(
                self.db,
                upload,
                status="Vyžaduje kontrolu",
                processing_status="ERROR",
                error_message=str(exc)[:1000],
            )

            return 0
