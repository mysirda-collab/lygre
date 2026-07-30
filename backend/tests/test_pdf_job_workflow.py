from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.customer import Customer
from app.models.job import Job, JobNote, JobStatusHistory
from app.models.upload import Upload
from app.models import calendar_event as _calendar_event  # noqa: F401
from app.models import reservation as _reservation  # noqa: F401
from app.models import sms_log as _sms_log  # noqa: F401
from app.models import sms_template as _sms_template  # noqa: F401
from app.models import time_slot as _time_slot  # noqa: F401
from app.models import user as _user  # noqa: F401
from app.services.job_creation_service import JobCreationService


def _upload(db: Session, name: str) -> Upload:
    item = Upload(original_filename=name, stored_filename=name, file_path=name, file_size=1)
    db.add(item)
    db.commit()
    return item


def _service(db: Session) -> JobCreationService:
    service = JobCreationService(db)
    service._update_progress = lambda *args, **kwargs: None
    return service


def test_incomplete_pdf_creates_traceable_review_job_and_prevents_duplicates() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db, patch("app.services.job_creation_service.enrich_with_optional_ai", side_effect=lambda _, values: values):
        first_upload = _upload(db, "first.pdf")
        payload, first_job = _service(db).process_upload_text(first_upload, "neúplný dokument")
        assert first_job is not None
        assert first_job.status == "Vyžaduje kontrolu"
        assert first_upload.job_id == first_job.id
        assert payload["parsed_data"]["validation_warnings"]

        duplicate_upload = _upload(db, "duplicate.pdf")
        duplicate, duplicate_job = _service(db).process_upload_text(duplicate_upload, "neúplný dokument", qr_job=first_job.job_number)
        assert duplicate_job.id == first_job.id
        assert duplicate_upload.job_id == first_job.id
        assert len(db.scalars(select(Job)).all()) == 1
        assert duplicate["parsed_data"]["review_required"] is True


def test_customer_matching_order_status_history_and_notes() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        customer = Customer(uuid="existing", customer_number="C-100", name="Existující", phone="420603111222", email="match@example.cz")
        db.add(customer)
        db.commit()
        upload = _upload(db, "matched.pdf")
        parsed = {
            "job_number": "JOB-100", "customer_number": " C-100 ", "customer_name": "Jiné jméno",
            "phone": "603 999 999", "email": "other@example.cz", "should_create_job": True,
            "missing_fields": [], "parser_confidence": 1.0,
        }
        service = _service(db)
        with patch.object(service.parser, "build_parsed_payload", return_value={**parsed, "parsed_data": dict(parsed)}):
            with patch("app.services.job_creation_service.enrich_with_optional_ai", side_effect=lambda _, values: values):
                _, job = service.process_upload_text(upload, "spolehlivý text")
        assert job.customer_id == customer.id
        assert job.status == "Nová"
        assert len(db.scalars(select(Customer)).all()) == 1

        from app.crud.job import add_job_note, update_job
        update_job(db, job, {"status": "Klient kontaktován"})
        note = add_job_note(db, job.id, "Domluven telefonát", 1)
        history = db.scalars(select(JobStatusHistory).where(JobStatusHistory.job_id == job.id)).all()
        assert [(item.previous_status, item.new_status) for item in history] == [(None, "Nová"), ("Nová", "Klient kontaktován")]
        assert db.get(JobNote, note.id).text == "Domluven telefonát"
