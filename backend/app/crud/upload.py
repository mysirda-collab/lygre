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
    processing_status: str = "Zpracovává se",
) -> Upload:
    upload = Upload(
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        content_type=content_type,
        file_size=file_size,
        status=status,
        processing_status=processing_status,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def get_uploads(db: Session) -> Sequence[Upload]:
    return db.scalars(select(Upload).order_by(Upload.uploaded_at.desc())).all()


def get_upload_by_id(db: Session, upload_id: int) -> Upload | None:
    return db.get(Upload, upload_id)


def update_upload(db: Session, upload: Upload, **kwargs: object) -> Upload:
    for key, value in kwargs.items():
        setattr(upload, key, value)
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload
