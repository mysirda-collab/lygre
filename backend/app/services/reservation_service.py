from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import secrets

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.job import Job
from app.models.reservation import Reservation
from app.models.time_slot import TimeSlot


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ReservationServiceError(Exception):
    pass


class ReservationNotFoundError(ReservationServiceError):
    pass


class ReservationTokenExpiredError(ReservationServiceError):
    pass


class SlotNotAvailableError(ReservationServiceError):
    pass


class SlotCapacityExceededError(ReservationServiceError):
    pass


@dataclass(frozen=True)
class ReservationTokenConfig:
    ttl_hours: int = 48


class ReservationService:
    ACTIVE_SLOT_STATUSES = {"confirmed"}

    def __init__(self, db: Session, *, token_config: ReservationTokenConfig | None = None) -> None:
        self.db = db
        self.token_config = token_config or ReservationTokenConfig()

    def create_reservation_request(self, *, job_id: int, customer_id: int) -> Reservation:
        self._ensure_job_exists(job_id)
        self._ensure_customer_exists(customer_id)

        now = utc_now()
        reservation = Reservation(
            job_id=job_id,
            customer_id=customer_id,
            slot_id=None,
            token=self._generate_token(),
            token_expires_at=now + timedelta(hours=self.token_config.ttl_hours),
            token_used=False,
            status="requested",
            reminder_sent_at=None,
            confirmation_sent_at=None,
            confirmed_at=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(reservation)
        self.db.commit()
        self.db.refresh(reservation)
        return reservation

    def get_reservation(self, reservation_id: int) -> Reservation:
        reservation = self.db.scalar(select(Reservation).where(Reservation.id == reservation_id))
        if not reservation:
            raise ReservationNotFoundError("Reservation not found")
        return reservation

    def get_reservation_by_token(self, *, token: str, must_be_active: bool = False) -> Reservation:
        reservation = self.db.scalar(select(Reservation).where(Reservation.token == token))
        if not reservation:
            raise ReservationNotFoundError("Reservation token not found")

        if must_be_active:
            now = utc_now()
            if reservation.token_expires_at and as_utc(reservation.token_expires_at) < now:
                raise ReservationTokenExpiredError("Reservation token expired")
            if reservation.token_used:
                raise ReservationTokenExpiredError("Reservation token already used")
        return reservation

    def confirm_reservation(self, *, token: str, slot_id: int) -> Reservation:
        reservation = self._reservation_by_token_query(for_update=True).where(Reservation.token == token)
        reservation_obj = self.db.scalar(reservation)
        if not reservation_obj:
            raise ReservationNotFoundError("Reservation token not found")

        now = utc_now()
        if reservation_obj.token_expires_at and as_utc(reservation_obj.token_expires_at) < now:
            raise ReservationTokenExpiredError("Reservation token expired")
        if reservation_obj.token_used:
            raise ReservationTokenExpiredError("Reservation token already used")

        slot_stmt: Select[tuple[TimeSlot]] = select(TimeSlot).where(TimeSlot.id == slot_id).with_for_update()
        slot = self.db.scalar(slot_stmt)
        if not slot:
            raise SlotNotAvailableError("Selected slot does not exist")
        if not slot.enabled or slot.blocked:
            raise SlotNotAvailableError("Selected slot is not available")

        active_reservations = self.db.scalar(
            select(func.count(Reservation.id)).where(
                Reservation.slot_id == slot.id,
                Reservation.status.in_(self.ACTIVE_SLOT_STATUSES),
            )
        )
        if (active_reservations or 0) >= slot.capacity:
            raise SlotCapacityExceededError("Selected slot is full")

        reservation_obj.slot_id = slot.id
        reservation_obj.status = "confirmed"
        reservation_obj.token_used = True
        reservation_obj.confirmed_at = now
        reservation_obj.updated_at = now
        self.db.add(reservation_obj)
        self.db.commit()
        self.db.refresh(reservation_obj)
        return reservation_obj

    def _reservation_by_token_query(self, *, for_update: bool) -> Select[tuple[Reservation]]:
        stmt: Select[tuple[Reservation]] = select(Reservation)
        if for_update:
            stmt = stmt.with_for_update()
        return stmt

    def _ensure_job_exists(self, job_id: int) -> None:
        job = self.db.scalar(select(Job).where(Job.id == job_id, Job.is_deleted.is_(False)))
        if not job:
            raise ReservationServiceError("Job not found")

    def _ensure_customer_exists(self, customer_id: int) -> None:
        customer = self.db.scalar(select(Customer).where(Customer.id == customer_id))
        if not customer:
            raise ReservationServiceError("Customer not found")

    @staticmethod
    def _generate_token() -> str:
        return secrets.token_urlsafe(32)
