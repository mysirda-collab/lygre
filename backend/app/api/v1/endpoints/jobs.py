import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.audit import create_audit_log
from app.crud.job import (
    create_job,
    delete_job,
    get_dashboard_summary,
    get_job_by_id,
    get_job_by_number,
    get_job_detail_data,
    get_jobs,
    update_job,
)
from app.dependencies.auth import require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.job import DashboardSummaryResponse, JobCreate, JobDetailResponse, JobListResponse, JobRead, JobUpdate

router = APIRouter()
logger = logging.getLogger("jobs")


@router.get("", response_model=JobListResponse, summary="List jobs")
def list_jobs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    technician: str | None = Query(default=None),
    customer: str | None = Query(default=None),
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
        installation_date_from=installation_date_from or installation_date,
        installation_date_to=installation_date_to,
        search=search,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )
    return JobListResponse(items=list(jobs), total=total, page=skip // limit + 1, page_size=limit)


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse, summary="Dashboard summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> DashboardSummaryResponse:
    data = get_dashboard_summary(db)
    return DashboardSummaryResponse(**data)


@router.get("/{job_id}/detail", response_model=JobDetailResponse, summary="Get job detail")
def get_job_detail(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> JobDetailResponse:
    job, attachments, audit_logs = get_job_detail_data(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobDetailResponse(job=job, attachments=attachments, audit_logs=audit_logs)


@router.get("/{job_id}", response_model=JobRead, summary="Get job by id")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> JobRead:
    job = get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


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
    return created


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
    return updated


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
