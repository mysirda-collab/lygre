from datetime import UTC, datetime, timedelta

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
from app.models.sms_log import SmsLog
from app.models.time_slot import TimeSlot
from app.services.notification_service import NotificationService
from app.services.scheduler_service import SchedulerService


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    db._lygre_test_engine = engine  # type: ignore[attr-defined]
    return db


def test_scheduler_sends_due_reminders() -> None:
    db = _session()
    try:
        now = datetime.now(UTC)
        customer = Customer(uuid="cust-sch", customer_number="C-SCH-1", name="Scheduler", phone="+420603000222")
        db.add(customer)
        db.commit()
        db.refresh(customer)

        job = Job(job_number="A-SCH-1", customer_name="Scheduler", customer_id=customer.id)
        db.add(job)
        db.commit()
        db.refresh(job)

        slot = TimeSlot(
            start=now + timedelta(hours=23),
            end=now + timedelta(hours=24),
            capacity=1,
            enabled=True,
            blocked=False,
            technician="Pavel",
            location="Praha",
            created_at=now,
            updated_at=now,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        reservation = Reservation(
            job_id=job.id,
            customer_id=customer.id,
            slot_id=slot.id,
            token="sch-token",
            token_expires_at=now + timedelta(days=2),
            token_used=True,
            status="confirmed",
            created_at=now,
            updated_at=now,
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)

        scheduler = SchedulerService(db, NotificationService(db))
        sent = scheduler.process_due_reminders(now=now, reminder_window_hours=24)

        assert sent == 1
        db.refresh(reservation)
        assert reservation.reminder_sent_at is not None

        sms = db.query(SmsLog).filter(SmsLog.type == "reservation_reminder").all()
        assert len(sms) == 1
        assert sms[0].status == "sent"

        # second run must not send duplicate reminder
        sent_again = scheduler.process_due_reminders(now=now, reminder_window_hours=24)
        assert sent_again == 0
        sms_again = db.query(SmsLog).filter(SmsLog.type == "reservation_reminder", SmsLog.status == "sent").all()
        assert len(sms_again) == 1
    finally:
        db.close()
        db._lygre_test_engine.dispose()  # type: ignore[attr-defined]


def test_notification_service_reminder_is_idempotent() -> None:
    db = _session()
    try:
        now = datetime.now(UTC)
        customer = Customer(uuid="cust-idem", customer_number="C-IDEM-1", name="Idempotence", phone="+420603000223")
        db.add(customer)
        db.commit()
        db.refresh(customer)

        job = Job(job_number="A-IDEM-1", customer_name="Idempotence", customer_id=customer.id)
        db.add(job)
        db.commit()
        db.refresh(job)

        slot = TimeSlot(
            start=now + timedelta(hours=3),
            end=now + timedelta(hours=4),
            capacity=1,
            enabled=True,
            blocked=False,
            technician="Pavel",
            location="Praha",
            created_at=now,
            updated_at=now,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        reservation = Reservation(
            job_id=job.id,
            customer_id=customer.id,
            slot_id=slot.id,
            token="idem-token",
            token_expires_at=now + timedelta(days=2),
            token_used=True,
            status="confirmed",
            created_at=now,
            updated_at=now,
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)

        notification = NotificationService(db)
        first = notification.send_reservation_reminder(reservation)
        second = notification.send_reservation_reminder(reservation)

        assert first.status == "sent"
        assert second.status in {"sent", "skipped"}
        sent_logs = db.query(SmsLog).filter(SmsLog.type == "reservation_reminder", SmsLog.status == "sent").all()
        assert len(sent_logs) == 1
    finally:
        db.close()
        db._lygre_test_engine.dispose()  # type: ignore[attr-defined]
