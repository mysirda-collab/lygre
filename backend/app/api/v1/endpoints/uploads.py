from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.job import create_job, get_job_by_id, get_job_by_number, update_job
from app.crud.upload import create_upload, get_upload_by_id, get_uploads, update_upload
from app.dependencies.auth import require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.job import JobCreate, JobRead
from app.schemas.upload import UploadCreateResponse, UploadRead

router = APIRouter()


@router.post("/pdf", response_model=UploadCreateResponse, status_code=status.HTTP_201_CREATED, summary="Upload PDF")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> UploadCreateResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Soubor je povinný")

    filename_lower = file.filename.lower()
    if not filename_lower.endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Podporován je pouze soubor PDF")

    content_type = file.content_type or "application/pdf"
    if content_type.lower() not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Podporován je pouze soubor PDF")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Soubor je prázdný")

    upload_dir = Path(settings.uploads_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # service = JobCreationService(db)
    created_ids: list[int] = []
    source_document_id = uuid4().hex
    source_stored_filename = f"{uuid4().hex}.pdf"
    source_file_path = upload_dir / source_stored_filename
    source_file_path.write_bytes(contents)

    try:
        reader = PdfReader(BytesIO(contents))
        total_pages = len(reader.pages)
    except Exception:
        total_pages = 0

    if total_pages <= 0:
        stored_filename = f"{uuid4().hex}.pdf"
        page_path = upload_dir / stored_filename
        page_path.write_bytes(contents)

        upload = create_upload(
            db=db,
            original_filename=f"{file.filename} - strana 1/1",
            stored_filename=stored_filename,
            file_path=str(page_path),
            content_type=content_type,
            file_size=page_path.stat().st_size,
            status="Čeká",
            processing_status="WAITING",
            source_document_id=source_document_id,
            source_original_filename=file.filename,
            source_stored_filename=source_stored_filename,
            source_file_path=str(source_file_path),
            page_number=1,
            total_pages=1,
        )
        created_ids.append(upload.id)

        # Processing will be done asynchronously by scheduler.
    else:
        for page_number, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)
            stored_filename = f"{uuid4().hex}.pdf"
            page_path = upload_dir / stored_filename
            with page_path.open("wb") as f:
                writer.write(f)

            upload = create_upload(
                db=db,
                original_filename=f"{file.filename} - strana {page_number}/{total_pages}",
                stored_filename=stored_filename,
                file_path=str(page_path),
                content_type=content_type,
                file_size=page_path.stat().st_size,
                status="Čeká",
                processing_status="WAITING",
                source_document_id=source_document_id,
                source_original_filename=file.filename,
                source_stored_filename=source_stored_filename,
                source_file_path=str(source_file_path),
                page_number=page_number,
                total_pages=total_pages,
            )
            created_ids.append(upload.id)

            # Processing will be done asynchronously by scheduler.

    return UploadCreateResponse(
        id=created_ids[0],
        created_ids=created_ids,
        created_count=len(created_ids),
        source_document_id=source_document_id,
        source_original_filename=file.filename,
        total_pages=total_pages or 1,
    )


@router.get("/pdf", response_model=list[UploadRead], summary="List uploaded PDFs")
def list_uploads(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> list[UploadRead]:
    uploads = get_uploads(db=db)
    return list(uploads)


@router.get("/pdf/{upload_id}", response_model=UploadRead, summary="Get upload")
def get_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> UploadRead:
    upload = get_upload_by_id(db=db, upload_id=upload_id)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload nenalezen")
    return upload


@router.post("/pdf/{upload_id}/review", response_model=JobRead, summary="Create or update job from review")
def review_upload_job(
    upload_id: int,
    job_in: JobCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> JobRead:
    upload = get_upload_by_id(db=db, upload_id=upload_id)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload nenalezen")

    if upload.job_id:
        job = get_job_by_id(db=db, job_id=upload.job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zakázka nenalezena")
        updated = update_job(db=db, job=job, job_data=job_in.model_dump())
        upload.status = "Hotovo"
        upload.processing_status = "Hotovo"
        db.add(upload)
        db.commit()
        db.refresh(upload)
        return updated

    job_data = job_in.model_dump()
    if get_job_by_number(db=db, job_number=job_data["job_number"]):
        job_data["job_number"] = f"{job_data['job_number']}-{upload.id}"

    created = create_job(db=db, job_data=job_data)
    upload.job_id = created.id
    upload.status = "Hotovo"
    upload.processing_status = "Hotovo"
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return created


@router.get("/pdf/{upload_id}/file")
def download_upload_file(
    upload_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> FileResponse:
    upload = get_upload_by_id(db=db, upload_id=upload_id)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload nenalezen")

    file_path = Path(upload.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soubor nebyl nalezen na disku")

    return FileResponse(
        path=file_path,
        media_type=upload.content_type or "application/pdf",
        filename=upload.original_filename,
    )


@router.get("/pdf/{upload_id}/source-file")
def download_upload_source_file(
    upload_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WORKER)),
) -> FileResponse:
    upload = get_upload_by_id(db=db, upload_id=upload_id)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload nenalezen")

    source_path = Path(upload.source_file_path or upload.file_path)
    if not source_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Původní soubor nebyl nalezen na disku")

    return FileResponse(
        path=source_path,
        media_type=upload.content_type or "application/pdf",
        filename=upload.source_original_filename or upload.original_filename,
    )
