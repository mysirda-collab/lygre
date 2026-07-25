from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.audit import create_audit_log
from app.crud.calendar_event import (
    create_calendar_event,
    delete_calendar_event,
    get_calendar_event_by_id,
    get_conflicting_event,
    get_job_for_event,
    get_technician_for_event,
    list_calendar_events,
    list_technicians,
    update_calendar_event,
)
from app.dependencies.auth import require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.calendar_event import (
    CalendarEventCreate,
    CalendarEventListResponse,
    CalendarEventRead,
    CalendarEventReschedule,
    CalendarEventUpdate,
    TechnicianRead,
)

router = APIRouter()


def _validate_references(db: Session, *, job_id: int, technician_id: int) -> None:
    if not get_job_for_event(db, job_id=job_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not get_technician_for_event(db, technician_id=technician_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Technician not found")


def _ensure_no_collision(
    db: Session,
    *,
    technician_id: int,
    starts_at: datetime,
    ends_at: datetime,
    exclude_event_id: int | None = None,
) -> None:
    conflict = get_conflicting_event(
        db,
        technician_id=technician_id,
        starts_at=starts_at,
        ends_at=ends_at,
        exclude_event_id=exclude_event_id,
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Technician already has an event in this time range",
        )


@router.get("/technicians", response_model=list[TechnicianRead], summary="List technicians")
def technicians(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> list[TechnicianRead]:
    return list(list_technicians(db))


@router.get("/events", response_model=CalendarEventListResponse, summary="List calendar events")
def events(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    technician_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> CalendarEventListResponse:
    items = list_calendar_events(db, start=start, end=end, technician_id=technician_id)
    return CalendarEventListResponse(items=list(items))


@router.post("/events", response_model=CalendarEventRead, status_code=status.HTTP_201_CREATED, summary="Create calendar event")
def create_event(
    payload: CalendarEventCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> CalendarEventRead:
    _validate_references(db, job_id=payload.job_id, technician_id=payload.technician_id)
    _ensure_no_collision(
        db,
        technician_id=payload.technician_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    created = create_calendar_event(db, data=payload.model_dump())
    create_audit_log(
        db,
        entity_type="calendar_event",
        entity_id=created.id,
        action="create",
        details=f"{actor.email} created event {created.title} for job {created.job_id}",
    )
    return created


@router.get("/events/{event_id}", response_model=CalendarEventRead, summary="Get calendar event")
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> CalendarEventRead:
    event = get_calendar_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.put("/events/{event_id}", response_model=CalendarEventRead, summary="Update calendar event")
def update_event(
    event_id: int,
    payload: CalendarEventUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> CalendarEventRead:
    event = get_calendar_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    _validate_references(db, job_id=payload.job_id, technician_id=payload.technician_id)
    _ensure_no_collision(
        db,
        technician_id=payload.technician_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        exclude_event_id=event.id,
    )
    updated = update_calendar_event(db, event=event, data=payload.model_dump())
    create_audit_log(
        db,
        entity_type="calendar_event",
        entity_id=updated.id,
        action="update",
        details=f"{actor.email} updated event {updated.title}",
    )
    return updated


@router.patch("/events/{event_id}/schedule", response_model=CalendarEventRead, summary="Reschedule calendar event")
def reschedule_event(
    event_id: int,
    payload: CalendarEventReschedule,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> CalendarEventRead:
    event = get_calendar_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    _ensure_no_collision(
        db,
        technician_id=event.technician_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        exclude_event_id=event.id,
    )
    updated = update_calendar_event(
        db,
        event=event,
        data={"starts_at": payload.starts_at, "ends_at": payload.ends_at},
    )
    create_audit_log(
        db,
        entity_type="calendar_event",
        entity_id=updated.id,
        action="reschedule",
        details=f"{actor.email} moved event {updated.title}",
    )
    return updated


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete calendar event")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> None:
    event = get_calendar_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    delete_calendar_event(db, event=event)
    create_audit_log(
        db,
        entity_type="calendar_event",
        entity_id=event.id,
        action="delete",
        details=f"{actor.email} deleted event {event.title}",
    )
