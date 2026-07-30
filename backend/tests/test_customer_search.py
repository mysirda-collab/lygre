from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.crud.customer import search_customers
from app.crud.job import get_jobs
from app.models.base import Base
from app.models.customer import Customer
from app.models.job import Job
from app.models import job as _job  # noqa: F401
from app.models import reservation as _reservation  # noqa: F401
from app.models import sms_log as _sms_log  # noqa: F401
from app.models import time_slot as _time_slot  # noqa: F401


def test_customer_search_matches_normalized_phone_with_or_without_country_prefix() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        customer = Customer(
            uuid="phone-search",
            customer_number="C-PHONE",
            name="Telefonní zákazník",
            phone="+420 603 111 222",
        )
        db.add(customer)
        db.commit()

        assert [item.id for item in search_customers(db, query="603111222")] == [customer.id]
        assert [item.id for item in search_customers(db, query="+420603111222")] == [customer.id]


def test_job_fulltext_search_matches_normalized_phone() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        job = Job(job_number="PHONE-JOB", customer_name="Telefonní zakázka", phone="+420 (777) 123-456")
        db.add(job)
        db.commit()

        jobs, total = get_jobs(db, search="777123456")

        assert total == 1
        assert [item.id for item in jobs] == [job.id]
