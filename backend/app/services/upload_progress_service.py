import logging
import time

from sqlalchemy import update

from app.dependencies.database import SessionLocal
from app.models.upload import Upload

log = logging.getLogger(__name__)


def update_upload_progress(
    upload_id: int,
    *,
    progress: int,
    message: str,
    processing_status: str = "Zpracovává se",
) -> None:
    progress = max(0, min(progress, 100))
    db = SessionLocal()
    try:
        db.execute(
            update(Upload)
            .where(Upload.id == upload_id)
            .values(
                processing_progress=progress,
                processing_message=message,
                processing_status=processing_status,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def mark_upload_failed(upload_id: int, *, message: str, error_message: str | None = None) -> None:
    db = SessionLocal()
    try:
        values: dict[str, object] = {
            "status": "Chyba",
            "processing_status": "Chyba",
            "processing_progress": 100,
            "processing_message": message,
        }
        if error_message is not None:
            values["error_message"] = error_message[:1000]

        db.execute(update(Upload).where(Upload.id == upload_id).values(**values))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class UploadProgressReporter:
    def __init__(self, upload_id: int, *, min_progress_delta: int = 5, min_interval_seconds: float = 1.0) -> None:
        self.upload_id = upload_id
        self.min_progress_delta = min_progress_delta
        self.min_interval_seconds = min_interval_seconds
        self._last_progress: int | None = None
        self._last_saved_at = 0.0

    def report(
        self,
        progress: int,
        message: str,
        *,
        processing_status: str = "Zpracovává se",
        force: bool = False,
    ) -> None:
        progress = max(0, min(progress, 100))
        now = time.monotonic()

        if not force and self._last_progress is not None:
            progress_delta = abs(progress - self._last_progress)
            elapsed = now - self._last_saved_at
            if progress_delta < self.min_progress_delta and elapsed < self.min_interval_seconds:
                return

        try:
            update_upload_progress(
                self.upload_id,
                progress=progress,
                message=message,
                processing_status=processing_status,
            )
        except Exception:
            log.exception("Nepodařilo se uložit průběh zpracování uploadu %s", self.upload_id)
            return

        self._last_progress = progress
        self._last_saved_at = now
