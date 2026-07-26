from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.models.reservation import Reservation
from app.models.time_slot import TimeSlot


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class TimeSlotCreateData:
    start: datetime
    end: datetime
    capacity: int = 1
    enabled: bool = True
    blocked: bool = False
    technician: str | None = None
    title: str | None = None
    location: str | None = None
    note: str | None = None
    installation_type: str | None = None


@dataclass(frozen=True)
class TimeSlotUpdateData:
    start: datetime | None = None
    end: datetime | None = None
    capacity: int | None = None
    enabled: bool | None = None
    blocked: bool | None = None
    technician: str | None = None
    title: str | None = None
    location: str | None = None
    note: str | None = None
    installation_type: str | None = None


@dataclass(frozen=True)
class AvailableSlot:
    slot: TimeSlot
    remaining_capacity: int


class CalendarServiceError(Exception):
    pass


class TimeSlotNotFoundError(CalendarServiceError):
    pass


class TimeSlotConflictError(CalendarServiceError):
    pass


class TimeSlotValidationError(CalendarServiceError):
    pass


class CalendarService:
    ACTIVE_RESERVATION_STATUSES = {"confirmed"}

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_slot(self, payload: TimeSlotCreateData) -> TimeSlot:
        start = as_utc(payload.start)
        end = as_utc(payload.end)
        self._validate_slot_range(start, end)
        self._validate_capacity(payload.capacity)

        if self.has_time_conflict(
            start=start,
            end=end,
            technician=payload.technician,
            location=payload.location,
            for_update=True,
        ):
            raise TimeSlotConflictError("Slot overlaps with an existing slot")

        now = utc_now()
        slot = TimeSlot(
            start=start,
            end=end,
            capacity=payload.capacity,
            enabled=payload.enabled,
            blocked=payload.blocked,
            technician=payload.technician,
            title=payload.title,
            location=payload.location,
            note=payload.note,
            installation_type=payload.installation_type,
            created_at=now,
            updated_at=now,
        )
        self.db.add(slot)
        self.db.commit()
        self.db.refresh(slot)
        return slot

    def update_slot(self, slot_id: int, payload: TimeSlotUpdateData) -> TimeSlot:
        slot = self._get_slot_for_update(slot_id)

        new_start = as_utc(payload.start) if payload.start is not None else as_utc(slot.start)
        new_end = as_utc(payload.end) if payload.end is not None else as_utc(slot.end)
        new_capacity = payload.capacity if payload.capacity is not None else slot.capacity
        new_technician = payload.technician if payload.technician is not None else slot.technician
        new_location = payload.location if payload.location is not None else slot.location

        self._validate_slot_range(new_start, new_end)
        self._validate_capacity(new_capacity)

        if self.has_time_conflict(
            start=new_start,
            end=new_end,
            technician=new_technician,
            location=new_location,
            exclude_slot_id=slot.id,
            for_update=True,
        ):
            raise TimeSlotConflictError("Updated slot overlaps with an existing slot")

        slot.start = new_start
        slot.end = new_end
        slot.capacity = new_capacity
        if payload.enabled is not None:
            slot.enabled = payload.enabled
        if payload.blocked is not None:
            slot.blocked = payload.blocked
        slot.technician = new_technician
        slot.title = payload.title if payload.title is not None else slot.title
        slot.location = new_location
        slot.note = payload.note if payload.note is not None else slot.note
        slot.installation_type = (
            payload.installation_type if payload.installation_type is not None else slot.installation_type
        )
        slot.updated_at = utc_now()

        self.db.add(slot)
        self.db.commit()
        self.db.refresh(slot)
        return slot

    def block_slot(self, slot_id: int, *, blocked: bool = True, disable: bool = True) -> TimeSlot:
        slot = self._get_slot_for_update(slot_id)
        slot.blocked = blocked
        if disable:
            slot.enabled = not blocked
        slot.updated_at = utc_now()
        self.db.add(slot)
        self.db.commit()
        self.db.refresh(slot)
        return slot

    def list_available_slots(
        self,
        *,
        start_from: datetime,
        end_to: datetime,
        technician: str | None = None,
        location: str | None = None,
        installation_type: str | None = None,
        required_capacity: int = 1,
    ) -> list[AvailableSlot]:
        self._validate_slot_range(as_utc(start_from), as_utc(end_to))
        self._validate_capacity(required_capacity)

        q: Select[tuple[TimeSlot]] = select(TimeSlot).where(
            TimeSlot.enabled.is_(True),
            TimeSlot.blocked.is_(False),
            TimeSlot.start < as_utc(end_to),
            TimeSlot.end > as_utc(start_from),
        )
        if technician is not None:
            q = q.where(TimeSlot.technician == technician)
        if location is not None:
            q = q.where(TimeSlot.location == location)
        if installation_type is not None:
            q = q.where(TimeSlot.installation_type == installation_type)

        slots = self.db.scalars(q.order_by(TimeSlot.start.asc())).all()
        result: list[AvailableSlot] = []
        for slot in slots:
            remaining = self.get_remaining_capacity(slot.id)
            if remaining >= required_capacity:
                result.append(AvailableSlot(slot=slot, remaining_capacity=remaining))
        return result

    def has_time_conflict(
        self,
        *,
        start: datetime,
        end: datetime,
        technician: str | None,
        location: str | None,
        exclude_slot_id: int | None = None,
        for_update: bool = False,
    ) -> bool:
        self._validate_slot_range(as_utc(start), as_utc(end))
        if technician is None and location is None:
            return False

        conditions = [
            TimeSlot.start < as_utc(end),
            TimeSlot.end > as_utc(start),
        ]
        if technician is not None:
            conditions.append(TimeSlot.technician == technician)
        elif location is not None:
            conditions.append(TimeSlot.location == location)

        if exclude_slot_id is not None:
            conditions.append(TimeSlot.id != exclude_slot_id)

        query: Select[tuple[TimeSlot]] = select(TimeSlot.id).where(and_(*conditions)).limit(1)
        if for_update:
            query = query.with_for_update()
        return self.db.scalar(query) is not None

    def get_remaining_capacity(self, slot_id: int) -> int:
        slot = self.db.scalar(select(TimeSlot).where(TimeSlot.id == slot_id))
        if not slot:
            raise TimeSlotNotFoundError("Slot not found")
        used = self.db.scalar(
            select(func.count(Reservation.id)).where(
                Reservation.slot_id == slot.id,
                Reservation.status.in_(self.ACTIVE_RESERVATION_STATUSES),
            )
        )
        return max(0, slot.capacity - (used or 0))

    def _get_slot_for_update(self, slot_id: int) -> TimeSlot:
        stmt: Select[tuple[TimeSlot]] = select(TimeSlot).where(TimeSlot.id == slot_id).with_for_update()
        slot = self.db.scalar(stmt)
        if not slot:
            raise TimeSlotNotFoundError("Slot not found")
        return slot

    @staticmethod
    def _validate_slot_range(start: datetime, end: datetime) -> None:
        if end <= start:
            raise TimeSlotValidationError("Slot end must be after start")

    @staticmethod
    def _validate_capacity(capacity: int) -> None:
        if capacity < 1:
            raise TimeSlotValidationError("Slot capacity must be at least 1")
