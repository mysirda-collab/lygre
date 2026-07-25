from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.calendar_event import CalendarEvent
from app.models.job import Job
from app.models.user import User, UserRole

TECHNICIAN_ROLES = [UserRole.WORKER, UserRole.MANAGER, UserRole.ADMIN]


def get_calendar_event_by_id(db: Session, event_id: int) -> CalendarEvent | None:
    return db.scalar(
        select(CalendarEvent)
        .where(CalendarEvent.id == event_id, CalendarEvent.is_deleted.is_(False))
        .options(joinedload(CalendarEvent.job), joinedload(CalendarEvent.technician))
    )


def list_calendar_events(
    db: Session,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    technician_id: int | None = None,
) -> Sequence[CalendarEvent]:
    query = (
        select(CalendarEvent)
        .where(CalendarEvent.is_deleted.is_(False))
        .options(joinedload(CalendarEvent.job), joinedload(CalendarEvent.technician))
    )

    if start and end:
        query = query.where(CalendarEvent.starts_at < end, CalendarEvent.ends_at > start)
    elif start:
        query = query.where(CalendarEvent.ends_at > start)
    elif end:
        query = query.where(CalendarEvent.starts_at < end)

    if technician_id:
        query = query.where(CalendarEvent.technician_id == technician_id)

    return db.scalars(query.order_by(CalendarEvent.starts_at.asc())).all()


def get_conflicting_event(
    db: Session,
    *,
    technician_id: int,
    starts_at: datetime,
    ends_at: datetime,
    exclude_event_id: int | None = None,
) -> CalendarEvent | None:
    conditions = [
        CalendarEvent.is_deleted.is_(False),
        CalendarEvent.technician_id == technician_id,
        CalendarEvent.starts_at < ends_at,
        CalendarEvent.ends_at > starts_at,
    ]
    if exclude_event_id is not None:
        conditions.append(CalendarEvent.id != exclude_event_id)
    return db.scalar(select(CalendarEvent).where(and_(*conditions)).limit(1))


def create_calendar_event(db: Session, *, data: dict) -> CalendarEvent:
    event = CalendarEvent(**data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return get_calendar_event_by_id(db, event.id)  # type: ignore[return-value]


def update_calendar_event(db: Session, *, event: CalendarEvent, data: dict) -> CalendarEvent:
    for key, value in data.items():
        setattr(event, key, value)
    db.add(event)
    db.commit()
    db.refresh(event)
    return get_calendar_event_by_id(db, event.id)  # type: ignore[return-value]


def delete_calendar_event(db: Session, *, event: CalendarEvent) -> None:
    event.is_deleted = True
    db.add(event)
    db.commit()


def get_job_for_event(db: Session, *, job_id: int) -> Job | None:
    return db.scalar(select(Job).where(Job.id == job_id, Job.is_deleted.is_(False)))


def get_technician_for_event(db: Session, *, technician_id: int) -> User | None:
    return db.scalar(
        select(User).where(
            User.id == technician_id,
            User.is_active.is_(True),
            User.role.in_(TECHNICIAN_ROLES),
        )
    )


def list_technicians(db: Session) -> Sequence[User]:
    return db.scalars(
        select(User)
        .where(User.is_active.is_(True), User.role.in_(TECHNICIAN_ROLES))
        .order_by(func.lower(User.full_name).asc())
    ).all()
