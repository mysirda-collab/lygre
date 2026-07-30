import logging

from app.dependencies.database import SessionLocal
from app.crud.upload import get_upload_by_id
from app.services.job_creation_service import JobCreationService
from app.services.upload_progress_service import mark_upload_failed

log = logging.getLogger(__name__)


def process_upload(upload_id: int, file_path: str):
    log.warning("=== BACKGROUND START upload_id=%s file=%s ===", upload_id, file_path)

    db = SessionLocal()
    upload = None
    try:
        upload = get_upload_by_id(db=db, upload_id=upload_id)

        if upload is None:
            log.error("Upload %s nebyl nalezen.", upload_id)
            return

        log.warning("Upload nalezen, spouštím JobCreationService")

        JobCreationService(db).process_upload(upload, file_path)

        log.warning("=== BACKGROUND END upload_id=%s ===", upload_id)

    except Exception as exc:
        log.exception("Chyba při background zpracování uploadu")
        db.rollback()
        mark_upload_failed(upload_id, message="Zpracování skončilo chybou", error_message=str(exc))

    finally:
        db.close()
