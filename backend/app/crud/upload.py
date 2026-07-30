from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.upload import Upload


def create_upload(
    db: Session,
    *,
    original_filename: str,
    stored_filename: str,
    file_path: str,
    content_type: str | None,
    file_size: int,
    status: str = "Hotovo",
    processing_status: str = "WAITING",
    processing_progress: int = 0,
    processing_message: str | None = "Čeká na zpracování",
    source_document_id: str | None = None,
    source_original_filename: str | None = None,
    source_stored_filename: str | None = None,
    source_file_path: str | None = None,
    page_number: int | None = None,
    total_pages: int | None = None,
) -> Upload:
    upload = Upload(
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        content_type=content_type,
        file_size=file_size,
        status=status,
        processing_status=processing_status,
        processing_progress=processing_progress,
        processing_message=processing_message,
        source_document_id=source_document_id,
        source_original_filename=source_original_filename,
        source_stored_filename=source_stored_filename,
        source_file_path=source_file_path,
        page_number=page_number,
        total_pages=total_pages,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def get_uploads(db: Session) -> Sequence[Upload]:
    return db.scalars(select(Upload).order_by(Upload.uploaded_at.desc())).all()


def get_upload_by_id(db: Session, upload_id: int) -> Upload | None:
    return db.get(Upload, upload_id)


def get_first_waiting_upload(db: Session) -> Upload | None:
    return db.scalars(
        select(Upload)
        .where(Upload.processing_status == "WAITING")
        .order_by(Upload.uploaded_at.asc(), Upload.id.asc())
        .limit(1)
    ).first()


def update_upload(db: Session, upload: Upload, **kwargs: object) -> Upload:
    for key, value in kwargs.items():
        setattr(upload, key, value)
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload
