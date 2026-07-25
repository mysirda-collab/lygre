from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.crud.job import create_job, get_job_by_number
from app.models.job import Job
from app.models.upload import Upload
from app.services.pdf_parser_service import PdfParserService


class JobCreationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.parser = PdfParserService()

    def process_upload(self, upload: Upload, file_path: str) -> tuple[dict[str, Any], Job | None]:
        text = self.parser.extract_text_from_pdf(file_path)
        parsed_payload = self.parser.build_parsed_payload(text)

        upload.extracted_text = text
        upload.parsed_data = parsed_payload["parsed_data"]
        upload.processing_status = "Zpracovává se"
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)

        if not parsed_payload.get("should_create_job"):
            upload.processing_status = "Vyžaduje kontrolu"
            upload.status = "Vyžaduje kontrolu"
            self.db.add(upload)
            self.db.commit()
            self.db.refresh(upload)
            return parsed_payload, None

        job_number = parsed_payload.get("job_number")
        customer_name = parsed_payload.get("customer_name")

        if not customer_name:
            upload.processing_status = "Vyžaduje kontrolu"
            upload.status = "Vyžaduje kontrolu"
            self.db.add(upload)
            self.db.commit()
            self.db.refresh(upload)
            return parsed_payload, None

        if not job_number:
            suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            job_number = f"AUTO-{suffix}-{upload.id}"
            parsed_payload["job_number"] = job_number
            parsed_data = parsed_payload.get("parsed_data")
            if isinstance(parsed_data, dict):
                parsed_data["job_number"] = job_number

        job_data = {
            "job_number": job_number,
            "customer_name": customer_name,
            "phone": parsed_payload.get("phone"),
            "email": parsed_payload.get("email"),
            "street": parsed_payload.get("street"),
            "city": parsed_payload.get("city"),
            "zip": parsed_payload.get("zip"),
            "status": "new",
        }

        existing = get_job_by_number(self.db, job_data["job_number"])
        if existing:
            upload.job_id = existing.id
            upload.processing_status = "Hotovo"
            upload.status = "Hotovo"
            self.db.add(upload)
            self.db.commit()
            self.db.refresh(upload)
            return parsed_payload, existing

        created = create_job(self.db, job_data)
        upload.job_id = created.id
        upload.processing_status = "Hotovo"
        upload.status = "Hotovo"
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)
        return parsed_payload, created
