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
from sqlalchemy.exc import IntegrityError
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.time_slot import (
    TimeSlotAvailabilityListResponse,
    TimeSlotAvailabilityRead,
    TimeSlotBlockRequest,
    TimeSlotCreate,
    TimeSlotListResponse,
    TimeSlotRead,
    TimeSlotUpdate,
)
from app.services.calendar_service import (
    CalendarService,
    TimeSlotCapacityError,
    TimeSlotConflictError,
    TimeSlotCreateData,
    TimeSlotNotFoundError,
    TimeSlotUpdateData,
    TimeSlotValidationError,
)
from app.schemas.calendar_event import (
    CalendarEventCreate,
    CalendarEventListResponse,
    CalendarEventRead,
    CalendarEventReschedule,
    CalendarEventUpdate,
    TechnicianRead,
)

router = APIRouter()


def _slot_service(db: Session) -> CalendarService:
    return CalendarService(db)


def _slot_to_read(service: CalendarService, slot) -> TimeSlotRead:
    remaining = service.get_remaining_capacity(slot.id)
    occupied = max(0, slot.capacity - remaining)
    payload = {
        "id": slot.id,
        "start": slot.start,
        "end": slot.end,
        "capacity": slot.capacity,
        "enabled": slot.enabled,
        "blocked": slot.blocked,
        "technician": slot.technician,
        "title": slot.title,
        "location": slot.location,
        "note": slot.note,
        "installation_type": slot.installation_type,
        "occupied_capacity": occupied,
        "remaining_capacity": remaining,
        "created_at": slot.created_at,
        "updated_at": slot.updated_at,
    }
    return TimeSlotRead.model_validate(payload)


def _raise_slot_http_error(exc: Exception) -> None:
    if isinstance(exc, TimeSlotNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, TimeSlotConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, (TimeSlotValidationError, TimeSlotCapacityError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    raise exc


@router.get("/slots", response_model=TimeSlotListResponse, summary="List time slots")
def list_slots(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    technician: str | None = Query(default=None),
    location: str | None = Query(default=None),
    installation_type: str | None = Query(default=None),
    include_blocked: bool = Query(default=True),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> TimeSlotListResponse:
    service = _slot_service(db)
    items = service.list_slots(
        start_from=start,
        end_to=end,
        technician=technician,
        location=location,
        installation_type=installation_type,
        include_blocked=include_blocked,
    )
    return TimeSlotListResponse(items=[_slot_to_read(service, slot) for slot in items])


@router.get("/slots/{slot_id}", response_model=TimeSlotRead, summary="Get time slot")
def get_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> TimeSlotRead:
    service = _slot_service(db)
    try:
        slot = service.get_slot(slot_id)
    except Exception as exc:
        _raise_slot_http_error(exc)
    return _slot_to_read(service, slot)


@router.post("/slots", response_model=TimeSlotRead, status_code=status.HTTP_201_CREATED, summary="Create time slot")
def create_slot(
    payload: TimeSlotCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> TimeSlotRead:
    service = _slot_service(db)
    try:
        created = service.create_slot(
            TimeSlotCreateData(
                start=payload.start,
                end=payload.end,
                capacity=payload.capacity,
                enabled=payload.enabled,
                blocked=payload.blocked,
                technician=payload.technician,
                title=payload.title,
                location=payload.location,
                note=payload.note,
                installation_type=payload.installation_type,
            )
        )
    except Exception as exc:
        _raise_slot_http_error(exc)
    return _slot_to_read(service, created)


@router.put("/slots/{slot_id}", response_model=TimeSlotRead, summary="Update time slot")
def update_slot(
    slot_id: int,
    payload: TimeSlotUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> TimeSlotRead:
    service = _slot_service(db)
    try:
        updated = service.update_slot(
            slot_id,
            TimeSlotUpdateData(
                start=payload.start,
                end=payload.end,
                capacity=payload.capacity,
                enabled=payload.enabled,
                blocked=payload.blocked,
                technician=payload.technician,
                title=payload.title,
                location=payload.location,
                note=payload.note,
                installation_type=payload.installation_type,
            ),
        )
    except Exception as exc:
        _raise_slot_http_error(exc)
    return _slot_to_read(service, updated)


@router.patch("/slots/{slot_id}/block", response_model=TimeSlotRead, summary="Block or unblock slot")
def block_slot(
    slot_id: int,
    payload: TimeSlotBlockRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> TimeSlotRead:
    service = _slot_service(db)
    try:
        updated = service.block_slot(slot_id, blocked=payload.blocked, disable=payload.disable)
    except Exception as exc:
        _raise_slot_http_error(exc)
    return _slot_to_read(service, updated)


@router.get("/available-slots", response_model=TimeSlotAvailabilityListResponse, summary="List available slots")
def available_slots(
    start: datetime = Query(...),
    end: datetime = Query(...),
    technician: str | None = Query(default=None),
    location: str | None = Query(default=None),
    installation_type: str | None = Query(default=None),
    required_capacity: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> TimeSlotAvailabilityListResponse:
    service = _slot_service(db)
    try:
        items = service.list_available_slots(
            start_from=start,
            end_to=end,
            technician=technician,
            location=location,
            installation_type=installation_type,
            required_capacity=required_capacity,
        )
    except Exception as exc:
        _raise_slot_http_error(exc)

    return TimeSlotAvailabilityListResponse(
        items=[
            TimeSlotAvailabilityRead(
                slot=_slot_to_read(service, item.slot),
                remaining_capacity=item.remaining_capacity,
            )
            for item in items
        ]
    )


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
    try:
        created = create_calendar_event(db, data=payload.model_dump())
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Technician already has an event in this time range")
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
    try:
        updated = update_calendar_event(db, event=event, data=payload.model_dump())
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Technician already has an event in this time range")
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
