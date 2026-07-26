from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import audit_log as _audit_log  # noqa: F401
from app.models import calendar_event as _calendar_event  # noqa: F401
from app.models import customer as _customer  # noqa: F401
from app.models import job as _job  # noqa: F401
from app.models import refresh_token as _refresh_token  # noqa: F401
from app.models import reservation as _reservation  # noqa: F401
from app.models import sms_log as _sms_log  # noqa: F401
from app.models import sms_template as _sms_template  # noqa: F401
from app.models import time_slot as _time_slot  # noqa: F401
from app.models import upload as _upload  # noqa: F401
from app.models import user as _user  # noqa: F401
from app.models.base import Base
from app.models.customer import Customer
from app.models.job import Job
from app.models.reservation import Reservation
from app.models.time_slot import TimeSlot
from app.services.reservation_service import (
    ReservationService,
    ReservationTokenExpiredError,
    SlotCapacityExceededError,
)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _seed_customer_and_job(db: Session) -> tuple[Customer, Job]:
    customer = Customer(
        uuid="cust-1",
        customer_number="C-001",
        name="Jan Novak",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    job = Job(
        job_number="A-RES-001",
        customer_name="Jan Novak",
        customer_id=customer.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return customer, job


def _seed_slot(db: Session, *, capacity: int = 1) -> TimeSlot:
    now = datetime.now(UTC)
    slot = TimeSlot(
        start=now + timedelta(days=1),
        end=now + timedelta(days=1, hours=2),
        capacity=capacity,
        enabled=True,
        blocked=False,
        technician="Pavel",
        title="Montaz",
        location="Praha",
        note=None,
        installation_type="Standard",
        created_at=now,
        updated_at=now,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


def test_create_reservation_request_generates_token(db_session: Session) -> None:
    customer, job = _seed_customer_and_job(db_session)
    service = ReservationService(db_session)

    reservation = service.create_reservation_request(job_id=job.id, customer_id=customer.id)

    assert reservation.id is not None
    assert reservation.token
    assert reservation.slot_id is None
    assert reservation.status == "requested"
    assert reservation.token_used is False
    assert reservation.token_expires_at is not None


def test_confirm_reservation_success(db_session: Session) -> None:
    customer, job = _seed_customer_and_job(db_session)
    slot = _seed_slot(db_session, capacity=1)
    service = ReservationService(db_session)
    reservation = service.create_reservation_request(job_id=job.id, customer_id=customer.id)

    confirmed = service.confirm_reservation(token=reservation.token, slot_id=slot.id)

    assert confirmed.status == "confirmed"
    assert confirmed.slot_id == slot.id
    assert confirmed.token_used is True
    assert confirmed.confirmed_at is not None


def test_confirm_reservation_rejects_expired_token(db_session: Session) -> None:
    customer, job = _seed_customer_and_job(db_session)
    slot = _seed_slot(db_session, capacity=1)
    service = ReservationService(db_session)
    reservation = service.create_reservation_request(job_id=job.id, customer_id=customer.id)
    reservation.token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.add(reservation)
    db_session.commit()

    with pytest.raises(ReservationTokenExpiredError):
        service.confirm_reservation(token=reservation.token, slot_id=slot.id)


def test_confirm_reservation_rejects_full_capacity(db_session: Session) -> None:
    customer, job = _seed_customer_and_job(db_session)
    slot = _seed_slot(db_session, capacity=1)
    service = ReservationService(db_session)

    first = service.create_reservation_request(job_id=job.id, customer_id=customer.id)
    service.confirm_reservation(token=first.token, slot_id=slot.id)

    second = Reservation(
        job_id=job.id,
        customer_id=customer.id,
        token="manual-token-2",
        token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        token_used=False,
        status="requested",
        reminder_sent_at=None,
        confirmation_sent_at=None,
        confirmed_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(second)
    db_session.commit()
    db_session.refresh(second)

    with pytest.raises(SlotCapacityExceededError):
        service.confirm_reservation(token=second.token, slot_id=slot.id)
