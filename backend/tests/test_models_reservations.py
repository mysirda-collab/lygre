import pytest
from app.models.time_slot import TimeSlot
from app.models.reservation import Reservation
from app.models.sms_log import SmsLog
from app.models.sms_template import SmsTemplate
# ensure related models are imported so SQLAlchemy registry can resolve names
from app.models.job import Job  # noqa: F401
from app.models.customer import Customer  # noqa: F401


def test_create_timeslot():
    ts = TimeSlot()
    assert hasattr(ts, 'start')


def test_create_reservation_fields():
    r = Reservation()
    assert hasattr(r, 'token')
    assert hasattr(r, 'reminder_sent_at')
    assert hasattr(r, 'confirmation_sent_at')


def test_sms_log_fields():
    s = SmsLog()
    assert hasattr(s, 'external_message_id')


def test_sms_template_fields():
    t = SmsTemplate()
    assert hasattr(t, 'body')
 