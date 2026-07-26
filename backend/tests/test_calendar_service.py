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
from app.services.calendar_service import (
    CalendarService,
    TimeSlotCapacityError,
    TimeSlotConflictError,
    TimeSlotCreateData,
    TimeSlotUpdateData,
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


def _seed_customer_job(db: Session) -> tuple[Customer, Job]:
    customer = Customer(uuid="cust-cs", customer_number="C-CS-1", name="Karel")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    job = Job(job_number="A-CS-1", customer_name="Karel", customer_id=customer.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return customer, job


def test_create_slot_success(db_session: Session) -> None:
    svc = CalendarService(db_session)
    now = datetime.now(UTC)
    slot = svc.create_slot(
        TimeSlotCreateData(
            start=now + timedelta(days=1),
            end=now + timedelta(days=1, hours=2),
            capacity=2,
            technician="Pavel",
            location="Praha",
            title="Montaz",
            installation_type="Standard",
        )
    )
    assert slot.id is not None
    assert slot.capacity == 2
    assert slot.enabled is True
    assert slot.blocked is False


def test_create_slot_detects_collision_for_same_technician(db_session: Session) -> None:
    svc = CalendarService(db_session)
    now = datetime.now(UTC)
    svc.create_slot(
        TimeSlotCreateData(
            start=now + timedelta(days=1),
            end=now + timedelta(days=1, hours=2),
            technician="Pavel",
            location="Praha",
        )
    )

    with pytest.raises(TimeSlotConflictError):
        svc.create_slot(
            TimeSlotCreateData(
                start=now + timedelta(days=1, minutes=30),
                end=now + timedelta(days=1, hours=3),
                technician="Pavel",
                location="Brno",
            )
        )


def test_update_slot_checks_collision(db_session: Session) -> None:
    svc = CalendarService(db_session)
    now = datetime.now(UTC)
    first = svc.create_slot(
        TimeSlotCreateData(
            start=now + timedelta(days=1),
            end=now + timedelta(days=1, hours=2),
            technician="Pavel",
            location="Praha",
        )
    )
    second = svc.create_slot(
        TimeSlotCreateData(
            start=now + timedelta(days=1, hours=3),
            end=now + timedelta(days=1, hours=4),
            technician="Pavel",
            location="Praha",
        )
    )

    with pytest.raises(TimeSlotConflictError):
        svc.update_slot(
            second.id,
            TimeSlotUpdateData(
                start=first.start + timedelta(minutes=15),
                end=first.end + timedelta(minutes=15),
            ),
        )


def test_block_slot_disables_slot(db_session: Session) -> None:
    svc = CalendarService(db_session)
    now = datetime.now(UTC)
    slot = svc.create_slot(
        TimeSlotCreateData(
            start=now + timedelta(days=1),
            end=now + timedelta(days=1, hours=2),
            technician="Pavel",
            location="Praha",
        )
    )

    blocked = svc.block_slot(slot.id)

    assert blocked.blocked is True
    assert blocked.enabled is False


def test_list_available_slots_respects_capacity(db_session: Session) -> None:
    svc = CalendarService(db_session)
    customer, job = _seed_customer_job(db_session)
    now = datetime.now(UTC)
    slot = svc.create_slot(
        TimeSlotCreateData(
            start=now + timedelta(days=1),
            end=now + timedelta(days=1, hours=2),
            capacity=1,
            technician="Pavel",
            location="Praha",
        )
    )

    reservation = Reservation(
        job_id=job.id,
        customer_id=customer.id,
        slot_id=slot.id,
        token="token-capacity",
        token_expires_at=now + timedelta(days=2),
        token_used=True,
        status="confirmed",
        created_at=now,
        updated_at=now,
    )
    db_session.add(reservation)
    db_session.commit()

    available = svc.list_available_slots(
        start_from=now,
        end_to=now + timedelta(days=2),
        technician="Pavel",
        required_capacity=1,
    )

    assert len(available) == 0


def test_update_slot_rejects_capacity_below_confirmed_count(db_session: Session) -> None:
    svc = CalendarService(db_session)
    customer, job = _seed_customer_job(db_session)
    now = datetime.now(UTC)
    slot = svc.create_slot(
        TimeSlotCreateData(
            start=now + timedelta(days=1),
            end=now + timedelta(days=1, hours=2),
            capacity=2,
            technician="Pavel",
            location="Praha",
        )
    )

    first = Reservation(
        job_id=job.id,
        customer_id=customer.id,
        slot_id=slot.id,
        token="token-c1",
        token_expires_at=now + timedelta(days=2),
        token_used=True,
        status="confirmed",
        created_at=now,
        updated_at=now,
    )
    second = Reservation(
        job_id=job.id,
        customer_id=customer.id,
        slot_id=slot.id,
        token="token-c2",
        token_expires_at=now + timedelta(days=2),
        token_used=True,
        status="confirmed",
        created_at=now,
        updated_at=now,
    )
    db_session.add(first)
    db_session.add(second)
    db_session.commit()

    with pytest.raises(TimeSlotCapacityError):
        svc.update_slot(slot.id, TimeSlotUpdateData(capacity=1))
