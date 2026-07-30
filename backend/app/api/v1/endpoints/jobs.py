import logging
from datetime import datetime
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.audit import create_audit_log
from app.crud.job import (
    create_job,
    add_job_note,
    delete_job,
    get_dashboard_summary,
    get_job_by_id,
    get_job_by_number,
    get_job_detail_data,
    get_job_note,
    get_job_notes,
    get_jobs,
    update_job,
    update_job_note,
)
from app.dependencies.auth import require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.job import DashboardSummaryResponse, JobCreate, JobDetailResponse, JobListResponse, JobNoteCreate, JobNoteRead, JobNoteUpdate, JobRead, JobStatusUpdate, JobUpdate, JOB_STATUSES

router = APIRouter()
logger = logging.getLogger("jobs")


def _normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    match = re.search(r"(?:\+\d{1,3}\s?)?(?:\d[\d\s()\-]{5,}\d)", cleaned)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(0)).strip(" ;,") or None


def _normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", cleaned)
    return match.group(0) if match else None


def _normalize_zip(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    match = re.search(r"\b\d{3}\s?\d{2}\b", cleaned)
    return match.group(0) if match else None


def _job_to_read(job: Any) -> JobRead:
    data = {
        "id": job.id,
        "job_number": job.job_number,
        "status": job.status,
        "priority": job.priority,
        "customer_name": job.customer_name,
        "company": job.company,
        "phone": _normalize_phone(job.phone),
        "email": _normalize_email(job.email),
        "street": job.street,
        "city": job.city,
        "zip": _normalize_zip(job.zip),
        "installation_date": job.installation_date,
        "technician": job.technician,
        "notes": job.notes,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "customer_id": job.customer_id,
        "order_number": job.order_number,
        "parser_confidence": job.parser_confidence,
    }
    return JobRead.model_validate(data)


@router.get("", response_model=JobListResponse, summary="List jobs")
def list_jobs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    technician: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    installation_date_from: datetime | None = Query(default=None),
    installation_date_to: datetime | None = Query(default=None),
    installation_date: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_desc: bool = Query(default=True),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> JobListResponse:
    jobs, total = get_jobs(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        priority=priority,
        technician=technician,
        customer=customer,
        customer_id=customer_id,
        installation_date_from=installation_date_from or installation_date,
        installation_date_to=installation_date_to,
        search=search,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )
    items = [_job_to_read(job) for job in jobs]
    return JobListResponse(items=items, total=total, page=skip // limit + 1, page_size=limit)


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse, summary="Dashboard summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> DashboardSummaryResponse:
    data = get_dashboard_summary(db)
    return DashboardSummaryResponse(
        status_counts=data["status_counts"],
        recent_jobs=[_job_to_read(job) for job in data["recent_jobs"]],
        overdue_jobs=[_job_to_read(job) for job in data["overdue_jobs"]],
        today_installations=[_job_to_read(job) for job in data["today_installations"]],
        pipeline_counts=data.get("pipeline_counts", {}),
    )


@router.get("/{job_id}/detail", response_model=JobDetailResponse, summary="Get job detail")
def get_job_detail(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> JobDetailResponse:
    job, attachments, audit_logs, status_history, notes = get_job_detail_data(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    primary_id = None
    for a in attachments:
        if getattr(a, "is_primary", False):
            primary_id = a.id
            break
    customer = None
    if job.customer:
        customer = {key: getattr(job.customer, key) for key in ("id", "customer_number", "name", "phone", "email", "street", "city", "zip")}
    return JobDetailResponse(job=_job_to_read(job), customer=customer, attachments=attachments, audit_logs=audit_logs, status_history=status_history, notes=notes, primary_attachment_id=primary_id)


@router.post("/{job_id}/notes", response_model=JobNoteRead, status_code=status.HTTP_201_CREATED, summary="Add timestamped job note")
def create_job_note_endpoint(
    job_id: int,
    payload: JobNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> JobNoteRead:
    if not get_job_by_id(db, job_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobNoteRead.model_validate(add_job_note(db, job_id, payload.text, current_user.id))


@router.get("/{job_id}/notes", response_model=list[JobNoteRead], summary="List job notes")
def list_job_notes_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> list[JobNoteRead]:
    if not get_job_by_id(db, job_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return [JobNoteRead.model_validate(note) for note in get_job_notes(db, job_id)]


@router.put("/{job_id}/notes/{note_id}", response_model=JobNoteRead, summary="Update job note")
def update_job_note_endpoint(
    job_id: int,
    note_id: int,
    payload: JobNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> JobNoteRead:
    if not get_job_by_id(db, job_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    note = get_job_note(db, note_id)
    if not note or note.job_id != job_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job note not found")
    return JobNoteRead.model_validate(update_job_note(db, note, payload.text, current_user.id))


@router.put("/{job_id}/status", response_model=JobRead, summary="Change current job status")
def change_job_status_endpoint(
    job_id: int,
    payload: JobStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> JobRead:
    job = get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_to_read(update_job(db, job, {"status": payload.status}))


@router.get("/{job_id}", response_model=JobRead, summary="Get job by id")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> JobRead:
    job = get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_to_read(job)


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED, summary="Create job")
def create_job_endpoint(
    job_in: JobCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> JobRead:
    existing = get_job_by_number(db=db, job_number=job_in.job_number)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job number already exists")
    created = create_job(db=db, job_data=job_in.model_dump())
    create_audit_log(db=db, entity_type="job", entity_id=created.id, action="create", details=f"Created job {created.job_number}")
    logger.info("Created job %s", created.job_number)
    return _job_to_read(created)


@router.put("/{job_id}", response_model=JobRead, summary="Update job")
def update_job_endpoint(
    job_id: int,
    job_in: JobUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> JobRead:
    job = get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job_in.job_number != job.job_number:
        existing = get_job_by_number(db=db, job_number=job_in.job_number)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job number already exists")
    updated = update_job(db=db, job=job, job_data=job_in.model_dump())
    create_audit_log(db=db, entity_type="job", entity_id=updated.id, action="update", details=f"Updated job {updated.job_number}")
    logger.info("Updated job %s", updated.job_number)
    return _job_to_read(updated)


@router.patch("/{job_id}", response_model=JobRead, summary="Patch job (partial update)")
def patch_job_endpoint(
    job_id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> JobRead:
    job = get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    # Only allow updating known fields
    allowed = {"job_number", "status", "priority", "customer_name", "company", "phone", "email", "street", "city", "zip", "installation_date", "technician", "notes"}
    update_data = {k: v for k, v in payload.items() if k in allowed}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update")
    if "status" in update_data and update_data["status"] not in JOB_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid job status")
    # validate job_number uniqueness if changed
    if "job_number" in update_data and update_data["job_number"] != job.job_number:
        existing = get_job_by_number(db=db, job_number=update_data["job_number"])
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job number already exists")
    updated = update_job(db=db, job=job, job_data=update_data)
    create_audit_log(db=db, entity_type="job", entity_id=updated.id, action="patch", details=f"Patched job {updated.job_number}")
    logger.info("Patched job %s", updated.job_number)
    return _job_to_read(updated)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete job")
def delete_job_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> None:
    job = get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    delete_job(db=db, job=job)
    create_audit_log(db=db, entity_type="job", entity_id=job.id, action="delete", details=f"Deleted job {job.job_number}")
    logger.info("Deleted job %s", job.job_number)
