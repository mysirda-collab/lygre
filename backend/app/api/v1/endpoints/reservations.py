from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.reservation import (
    ReservationAvailabilityListResponse,
    ReservationConfirmRequest,
    ReservationCreateRequest,
    ReservationPublicContext,
    ReservationPublicStatus,
    ReservationRead,
)
from app.schemas.time_slot import TimeSlotAvailabilityRead, TimeSlotRead
from app.services.calendar_service import CalendarService, TimeSlotValidationError
from app.services.notification_service import NotificationService
from app.services.reservation_service import (
    ReservationNotFoundError,
    ReservationService,
    ReservationServiceError,
    ReservationTokenExpiredError,
    SlotCapacityExceededError,
    SlotNotAvailableError,
)

router = APIRouter()


def _reservation_service(db: Session) -> ReservationService:
    return ReservationService(db)


def _calendar_service(db: Session) -> CalendarService:
    return CalendarService(db)


def _notification_service(db: Session) -> NotificationService:
    return NotificationService(db)


def _raise_reservation_http_error(exc: Exception) -> None:
    if isinstance(exc, ReservationNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, (ReservationTokenExpiredError, TimeSlotValidationError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, (SlotNotAvailableError, SlotCapacityExceededError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, ReservationServiceError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    raise exc


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED, summary="Create reservation request")
def create_reservation_request(
    payload: ReservationCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> ReservationRead:
    service = _reservation_service(db)
    try:
        reservation = service.create_reservation_request(job_id=payload.job_id, customer_id=payload.customer_id)
    except Exception as exc:
        _raise_reservation_http_error(exc)
    return ReservationRead.model_validate(reservation)


@router.get("/public/{token}", response_model=ReservationPublicStatus, summary="Public reservation token status")
def reservation_public_status(token: str, db: Session = Depends(get_db)) -> ReservationPublicStatus:
    service = _reservation_service(db)
    try:
        reservation = service.get_reservation_by_token(token=token)
    except Exception as exc:
        _raise_reservation_http_error(exc)
    return ReservationPublicStatus(
        reservation_id=reservation.id,
        status=reservation.status,
        token_expires_at=reservation.token_expires_at,
        token_used=reservation.token_used,
    )


@router.get("/public/{token}/context", response_model=ReservationPublicContext, summary="Public reservation context")
def reservation_public_context(token: str, db: Session = Depends(get_db)) -> ReservationPublicContext:
    service = _reservation_service(db)
    try:
        payload = service.get_public_context_by_token(token=token)
    except Exception as exc:
        _raise_reservation_http_error(exc)
    return ReservationPublicContext.model_validate(payload)


@router.get(
    "/public/{token}/available-slots",
    response_model=ReservationAvailabilityListResponse,
    summary="Public list of available slots for reservation token",
)
def reservation_public_available_slots(
    token: str,
    start: datetime = Query(...),
    end: datetime = Query(...),
    required_capacity: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
) -> ReservationAvailabilityListResponse:
    reservation_service = _reservation_service(db)
    calendar_service = _calendar_service(db)
    try:
        reservation_service.get_reservation_by_token(token=token, must_be_active=True)
        items = calendar_service.list_available_slots(
            start_from=start,
            end_to=end,
            required_capacity=required_capacity,
        )
    except Exception as exc:
        _raise_reservation_http_error(exc)
    return ReservationAvailabilityListResponse(
        items=[
            TimeSlotAvailabilityRead(
                slot=TimeSlotRead.model_validate(item.slot),
                remaining_capacity=item.remaining_capacity,
            )
            for item in items
        ]
    )


@router.post("/public/confirm", response_model=ReservationRead, summary="Public reservation confirmation")
def reservation_public_confirm(
    payload: ReservationConfirmRequest,
    db: Session = Depends(get_db),
) -> ReservationRead:
    reservation_service = _reservation_service(db)
    notification_service = _notification_service(db)
    try:
        reservation = reservation_service.confirm_reservation(token=payload.token, slot_id=payload.slot_id)
        notification_service.send_reservation_confirmation(reservation)
    except Exception as exc:
        _raise_reservation_http_error(exc)
    return ReservationRead.model_validate(reservation)
