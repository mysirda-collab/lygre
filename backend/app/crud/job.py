from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.job import Job, JobNote, JobStatusHistory
from app.models.reservation import Reservation
from app.models.time_slot import TimeSlot
from app.models.upload import Upload


def utc_now() -> datetime:
    return datetime.now(UTC)


VALID_STATUSES = {"new", "scheduled", "done", "cancelled", "Nová", "Vyžaduje kontrolu", "Klient nekontaktován", "Klient kontaktován", "Čeká na termín", "Termín naplánován", "Probíhá realizace", "Dokončeno", "Zrušeno"}
VALID_SORT_FIELDS = {"job_number", "customer_name", "installation_date", "created_at", "updated_at"}
VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


def _apply_filters(
    query,
    *,
    status: str | None,
    priority: str | None,
    technician: str | None,
    customer: str | None,
    customer_id: int | None,
    installation_date_from: datetime | None,
    installation_date_to: datetime | None,
    search: str | None,
):
    filters = [Job.is_deleted.is_(False)]

    if status:
        filters.append(Job.status == status)
    if priority:
        normalized_priority = priority.strip().lower()
        if normalized_priority in VALID_PRIORITIES:
            filters.append(Job.priority == normalized_priority)
    if technician:
        filters.append(Job.technician.ilike(f"%{technician}%"))
    if customer:
        filters.append(Job.customer_name.ilike(f"%{customer}%"))
    if customer_id is not None:
        filters.append(Job.customer_id == customer_id)
    if installation_date_from:
        filters.append(Job.installation_date >= installation_date_from)
    if installation_date_to:
        filters.append(Job.installation_date <= installation_date_to)
    if search:
        search_term = f"%{search.lower()}%"
        search_filters = [
            Job.job_number.ilike(search_term),
            Job.customer_name.ilike(search_term),
            Job.street.ilike(search_term),
            Job.city.ilike(search_term),
            Job.company.ilike(search_term),
            Job.notes.ilike(search_term),
            Job.technician.ilike(search_term),
            Job.phone.ilike(search_term),
        ]
        normalized_phone = "".join(character for character in search if character.isdigit())
        if len(normalized_phone) == 12 and normalized_phone.startswith("420"):
            normalized_phone = normalized_phone[3:]
        if len(normalized_phone) == 9:
            normalized_phone_column = Job.phone
            for separator in (" ", "+", "-", "(", ")"):
                normalized_phone_column = func.replace(normalized_phone_column, separator, "")
            search_filters.append(normalized_phone_column.like(f"%{normalized_phone}"))
        filters.append(or_(*search_filters))

    return query.where(and_(*filters))


def get_jobs(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    priority: str | None = None,
    technician: str | None = None,
    customer: str | None = None,
    customer_id: int | None = None,
    installation_date_from: datetime | None = None,
    installation_date_to: datetime | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_desc: bool = True,
) -> tuple[Sequence[Job], int]:
    query = _apply_filters(
        select(Job),
        status=status,
        priority=priority,
        technician=technician,
        customer=customer,
        customer_id=customer_id,
        installation_date_from=installation_date_from,
        installation_date_to=installation_date_to,
        search=search,
    )

    if sort_by not in VALID_SORT_FIELDS:
        sort_by = "created_at"
    sort_column = getattr(Job, sort_by)
    ordering = sort_column.desc() if sort_desc else sort_column.asc()

    total_query = _apply_filters(
        select(Job.id),
        status=status,
        priority=priority,
        technician=technician,
        customer=customer,
        customer_id=customer_id,
        installation_date_from=installation_date_from,
        installation_date_to=installation_date_to,
        search=search,
    )

    total = db.scalar(select(func.count()).select_from(total_query.subquery()))
    rows = db.scalars(query.order_by(ordering).offset(skip).limit(limit)).all()
    return rows, total or 0


def get_job_by_id(db: Session, job_id: int) -> Job | None:
    return db.scalar(select(Job).where(Job.id == job_id, Job.is_deleted.is_(False)))


def get_job_by_number(db: Session, job_number: str) -> Job | None:
    return db.scalar(select(Job).where(Job.job_number == job_number, Job.is_deleted.is_(False)))


def create_job(db: Session, job_data: dict[str, Any]) -> Job:
    job = Job(**job_data)
    db.add(job)
    db.flush()
    db.add(JobStatusHistory(job_id=job.id, previous_status=None, new_status=job.status))
    db.commit()
    db.refresh(job)
    return job


def update_job(db: Session, job: Job, job_data: dict[str, Any]) -> Job:
    previous_status = job.status
    for key, value in job_data.items():
        setattr(job, key, value)
    job.updated_at = utc_now()
    db.add(job)
    if "status" in job_data and job.status != previous_status:
        db.add(JobStatusHistory(job_id=job.id, previous_status=previous_status, new_status=job.status))
    db.commit()
    db.refresh(job)
    return job


def get_job_notes(db: Session, job_id: int) -> list[JobNote]:
    return list(
        db.scalars(
            select(JobNote)
            .where(JobNote.job_id == job_id)
            .order_by(JobNote.created_at.desc(), JobNote.id.desc())
        ).all()
    )


def get_job_note(db: Session, note_id: int) -> JobNote | None:
    return db.get(JobNote, note_id)


def add_job_note(db: Session, job_id: int, text: str, author_user_id: int) -> JobNote:
    note = JobNote(job_id=job_id, text=text.strip(), author_user_id=author_user_id)
    db.add(note)
    db.add(AuditLog(entity_type="job", entity_id=job_id, action="note_added", details="Přidána poznámka."))
    db.commit()
    db.refresh(note)
    return note


def update_job_note(db: Session, note: JobNote, text: str, updated_by_user_id: int) -> JobNote:
    note.text = text.strip()
    note.updated_at = utc_now()
    note.updated_by_user_id = updated_by_user_id
    db.add(note)
    db.add(AuditLog(entity_type="job", entity_id=note.job_id, action="note_updated", details="Upravena poznámka."))
    db.commit()
    db.refresh(note)
    return note


def delete_job(db: Session, job: Job) -> None:
    job.is_deleted = True
    job.updated_at = utc_now()
    db.add(job)
    db.commit()


def get_dashboard_summary(db: Session) -> dict[str, Any]:
    status_rows = db.execute(
        select(Job.status, func.count(Job.id)).where(Job.is_deleted.is_(False)).group_by(Job.status)
    ).all()
    status_counts = {status: count for status, count in status_rows}

    recent_jobs = db.scalars(
        select(Job).where(Job.is_deleted.is_(False)).order_by(Job.created_at.desc()).limit(10)
    ).all()

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)

    overdue_jobs = db.scalars(
        select(Job)
        .where(
            Job.is_deleted.is_(False),
            Job.installation_date.is_not(None),
            Job.installation_date < today_start,
            Job.status.not_in(["done", "cancelled"]),
        )
        .order_by(Job.installation_date.asc())
        .limit(20)
    ).all()

    today_installations = db.scalars(
        select(Job)
        .where(
            Job.is_deleted.is_(False),
            Job.installation_date.is_not(None),
            Job.installation_date >= today_start,
            Job.installation_date <= today_end,
        )
        .order_by(Job.installation_date.asc())
        .limit(20)
    ).all()

    tomorrow_start = today_start.replace(day=today_start.day) + timedelta(days=1)
    tomorrow_end = tomorrow_start.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Pipeline metrics for reservation workflow cards.
    new_imports = db.scalar(
        select(func.count(Job.id)).where(Job.is_deleted.is_(False), Job.status == "new")
    )
    waiting_sms = db.scalar(
        select(func.count(Reservation.id)).where(
            Reservation.status == "confirmed",
            Reservation.confirmation_sent_at.is_(None),
        )
    )
    waiting_reservation = db.scalar(
        select(func.count(Reservation.id)).where(
            Reservation.status == "requested",
            Reservation.token_used.is_(False),
        )
    )
    reservation_confirmed = db.scalar(
        select(func.count(Reservation.id)).where(Reservation.status == "confirmed")
    )
    installation_today = db.scalar(
        select(func.count(Reservation.id))
        .join(TimeSlot, TimeSlot.id == Reservation.slot_id)
        .where(
            Reservation.status == "confirmed",
            TimeSlot.start >= today_start,
            TimeSlot.start <= today_end,
        )
    )
    installation_tomorrow = db.scalar(
        select(func.count(Reservation.id))
        .join(TimeSlot, TimeSlot.id == Reservation.slot_id)
        .where(
            Reservation.status == "confirmed",
            TimeSlot.start >= tomorrow_start,
            TimeSlot.start <= tomorrow_end,
        )
    )
    completed = db.scalar(
        select(func.count(Job.id)).where(Job.is_deleted.is_(False), Job.status == "done")
    )

    return {
        "status_counts": status_counts,
        "recent_jobs": list(recent_jobs),
        "overdue_jobs": list(overdue_jobs),
        "today_installations": list(today_installations),
        "pipeline_counts": {
            "new_imports": int(new_imports or 0),
            "waiting_sms": int(waiting_sms or 0),
            "waiting_reservation": int(waiting_reservation or 0),
            "reservation_confirmed": int(reservation_confirmed or 0),
            "installation_today": int(installation_today or 0),
            "installation_tomorrow": int(installation_tomorrow or 0),
            "completed": int(completed or 0),
        },
    }


def get_job_detail_data(db: Session, job_id: int) -> tuple[Job | None, list[Upload], list[AuditLog], list[JobStatusHistory], list[JobNote]]:
    job = get_job_by_id(db, job_id)
    if not job:
        return None, [], [], [], []

    attachments = db.scalars(
        select(Upload)
        .where(Upload.job_id == job_id)
        .order_by(Upload.uploaded_at.desc())
    ).all()
    audit_logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.entity_type == "job", AuditLog.entity_id == job_id)
        .order_by(AuditLog.created_at.desc())
    ).all()
    history = db.scalars(select(JobStatusHistory).where(JobStatusHistory.job_id == job_id).order_by(JobStatusHistory.changed_at.desc())).all()
    notes = get_job_notes(db, job_id)
    return job, list(attachments), list(audit_logs), list(history), list(notes)
