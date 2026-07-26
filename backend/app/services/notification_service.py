from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.job import Job
from app.models.reservation import Reservation
from app.models.sms_log import SmsLog
from app.models.sms_template import SmsTemplate
from app.models.time_slot import TimeSlot
from app.services.sms_provider import DummySmsProvider, SmsProvider, SmsSendResult


def utc_now() -> datetime:
    return datetime.now(UTC)


class NotificationServiceError(Exception):
    pass


class NotificationTemplateRenderError(NotificationServiceError):
    pass


class NotificationService:
    def __init__(self, db: Session, provider: SmsProvider | None = None) -> None:
        self.db = db
        self.provider = provider or DummySmsProvider()

    def send_reservation_confirmation(self, reservation: Reservation) -> SmsLog:
        locked = self._lock_reservation(reservation.id)
        if locked.confirmation_sent_at is not None:
            existing = self._get_latest_sms_log(locked.id, "reservation_confirmation")
            if existing:
                return existing
            return self._create_skipped_log(
                sms_type="reservation_confirmation",
                customer_id=locked.customer_id,
                job_id=locked.job_id,
                reservation_id=locked.id,
                reason="Confirmation already sent",
            )

        # Claim before send to prevent duplicate sends under concurrent workers.
        locked.confirmation_sent_at = utc_now()
        locked.updated_at = utc_now()
        self.db.add(locked)
        self.db.commit()
        self.db.refresh(locked)

        customer = self._get_customer(locked.customer_id)
        job = self._get_job(locked.job_id)
        slot = self._get_slot(locked.slot_id) if locked.slot_id is not None else None

        phone = customer.phone or job.phone
        context = {
            "customer_name": customer.name,
            "job_number": job.job_number,
            "slot_start": slot.start.isoformat() if slot else "",
            "slot_end": slot.end.isoformat() if slot else "",
            "location": slot.location or "" if slot else "",
        }
        text = self.render_template(
            "reservation_confirmation",
            context,
            fallback=(
                "Dobry den {customer_name}, potvrzujeme termin zakazky {job_number} "
                "od {slot_start} do {slot_end}."
            ),
        )
        sms = self.send_sms(
            phone=phone,
            text=text,
            sms_type="reservation_confirmation",
            customer_id=customer.id,
            job_id=job.id,
            reservation_id=locked.id,
        )
        if sms.status != "sent":
            # Release claim on failure so scheduler/API can retry later.
            locked.confirmation_sent_at = None
            locked.updated_at = utc_now()
            self.db.add(locked)
            self.db.commit()
            self.db.refresh(locked)
        return sms

    def send_reservation_reminder(self, reservation: Reservation) -> SmsLog:
        locked = self._lock_reservation(reservation.id)
        if locked.reminder_sent_at is not None:
            existing = self._get_latest_sms_log(locked.id, "reservation_reminder")
            if existing:
                return existing
            return self._create_skipped_log(
                sms_type="reservation_reminder",
                customer_id=locked.customer_id,
                job_id=locked.job_id,
                reservation_id=locked.id,
                reason="Reminder already sent",
            )

        # Claim before send to prevent duplicate sends under concurrent workers.
        locked.reminder_sent_at = utc_now()
        locked.updated_at = utc_now()
        self.db.add(locked)
        self.db.commit()
        self.db.refresh(locked)

        customer = self._get_customer(locked.customer_id)
        job = self._get_job(locked.job_id)
        slot = self._get_slot(locked.slot_id) if locked.slot_id is not None else None

        phone = customer.phone or job.phone
        context = {
            "customer_name": customer.name,
            "job_number": job.job_number,
            "slot_start": slot.start.isoformat() if slot else "",
            "slot_end": slot.end.isoformat() if slot else "",
            "location": slot.location or "" if slot else "",
        }
        text = self.render_template(
            "reservation_reminder",
            context,
            fallback=(
                "Pripominka: zakazka {job_number} je planovana od {slot_start} do {slot_end}."
            ),
        )
        sms = self.send_sms(
            phone=phone,
            text=text,
            sms_type="reservation_reminder",
            customer_id=customer.id,
            job_id=job.id,
            reservation_id=locked.id,
        )
        if sms.status != "sent":
            # Release claim on failure so scheduler can retry.
            locked.reminder_sent_at = None
            locked.updated_at = utc_now()
            self.db.add(locked)
            self.db.commit()
            self.db.refresh(locked)
        return sms

    def send_sms(
        self,
        *,
        phone: str | None,
        text: str,
        sms_type: str,
        customer_id: int | None,
        job_id: int | None,
        reservation_id: int | None,
    ) -> SmsLog:
        created = utc_now()
        sms = SmsLog(
            customer_id=customer_id,
            job_id=job_id,
            reservation_id=reservation_id,
            type=sms_type,
            provider=self.provider.name,
            phone=phone or "",
            text=text,
            status="pending",
            error=None,
            external_message_id=None,
            created_at=created,
            sent_at=None,
            delivered_at=None,
        )
        self.db.add(sms)
        self.db.commit()
        self.db.refresh(sms)

        try:
            result = self.provider.send_sms(phone=phone or "", text=text)
        except Exception as exc:  # pragma: no cover - provider adapters are external
            result = SmsSendResult(success=False, error=str(exc))
        sms.status = "sent" if result.success else "failed"
        sms.external_message_id = result.external_message_id
        sms.error = result.error
        sms.sent_at = utc_now()
        self.db.add(sms)
        self.db.commit()
        self.db.refresh(sms)
        return sms

    def render_template(self, name: str, context: dict[str, str], *, fallback: str) -> str:
        template = self.db.scalar(select(SmsTemplate).where(SmsTemplate.name == name))
        body = template.body if template else fallback
        try:
            return body.format_map(context)
        except KeyError as exc:
            raise NotificationTemplateRenderError(f"Missing template variable: {exc}") from exc

    def _get_customer(self, customer_id: int) -> Customer:
        customer = self.db.scalar(select(Customer).where(Customer.id == customer_id))
        if not customer:
            raise NotificationServiceError("Customer not found")
        return customer

    def _get_job(self, job_id: int) -> Job:
        job = self.db.scalar(select(Job).where(Job.id == job_id, Job.is_deleted.is_(False)))
        if not job:
            raise NotificationServiceError("Job not found")
        return job

    def _get_slot(self, slot_id: int | None) -> TimeSlot:
        if slot_id is None:
            raise NotificationServiceError("Reservation has no slot")
        slot = self.db.scalar(select(TimeSlot).where(TimeSlot.id == slot_id))
        if not slot:
            raise NotificationServiceError("Slot not found")
        return slot

    def _lock_reservation(self, reservation_id: int) -> Reservation:
        reservation = self.db.scalar(
            select(Reservation).where(Reservation.id == reservation_id).with_for_update()
        )
        if not reservation:
            raise NotificationServiceError("Reservation not found")
        return reservation

    def _get_latest_sms_log(self, reservation_id: int, sms_type: str) -> SmsLog | None:
        return self.db.scalar(
            select(SmsLog)
            .where(SmsLog.reservation_id == reservation_id, SmsLog.type == sms_type)
            .order_by(SmsLog.created_at.desc(), SmsLog.id.desc())
            .limit(1)
        )

    def _create_skipped_log(
        self,
        *,
        sms_type: str,
        customer_id: int | None,
        job_id: int | None,
        reservation_id: int | None,
        reason: str,
    ) -> SmsLog:
        sms = SmsLog(
            customer_id=customer_id,
            job_id=job_id,
            reservation_id=reservation_id,
            type=sms_type,
            provider=self.provider.name,
            phone="",
            text="",
            status="skipped",
            error=reason,
            external_message_id=None,
            created_at=utc_now(),
            sent_at=utc_now(),
            delivered_at=None,
        )
        self.db.add(sms)
        self.db.commit()
        self.db.refresh(sms)
        return sms
