from datetime import datetime
import re
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.crud.job import create_job, get_job_by_number
from app.crud.customer import get_customer_by_number, find_by_phone, create_customer, find_or_create
import uuid as _uuid
from app.models.job import Job
from app.models.upload import Upload
from app.schemas.job import JobCreate
from app.services.pdf_parser_service import PdfParserService


class JobCreationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.parser = PdfParserService()

    def process_upload(self, upload: Upload, file_path: str) -> tuple[dict[str, Any], Job | None]:
        text = self.parser.extract_text_from_pdf(file_path)
        return self.process_upload_text(upload, text)

    def process_upload_text(self, upload: Upload, text: str) -> tuple[dict[str, Any], Job | None]:
        parsed_payload = self.parser.build_parsed_payload(text)

        upload.extracted_text = text
        upload.parsed_data = parsed_payload["parsed_data"]
        upload.processing_status = "Zpracovává se"
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)

        should_create_job = bool(parsed_payload.get("should_create_job"))
        used_fallback = not should_create_job

        parser_confidence = parsed_payload.get("parser_confidence")
        if parser_confidence is None:
            # parser may provide confidence inside parsed_data
            pd = parsed_payload.get("parsed_data")
            if isinstance(pd, dict):
                parser_confidence = pd.get("parser_confidence")
        try:
            parser_confidence = float(parser_confidence) if parser_confidence is not None else None
        except Exception:
            parser_confidence = None

        job_number = parsed_payload.get("job_number")
        if not job_number:
            used_fallback = True
            suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            job_number = f"AUTO-{suffix}-{upload.id}"
            parsed_payload["job_number"] = job_number
            parsed_data = parsed_payload.get("parsed_data")
            if isinstance(parsed_data, dict):
                parsed_data["job_number"] = job_number

        customer_number = parsed_payload.get("customer_number")
        customer_name = parsed_payload.get("customer_name")
        customer = None

        # identification rules: prefer customer_number, then phone
        if parser_confidence is not None and parser_confidence >= 0.7:
            if customer_number:
                customer = get_customer_by_number(self.db, customer_number)
                if not customer:
                    # create new customer
                    cid = _uuid.uuid4().hex
                    customer = create_customer(self.db, uuid=cid, customer_number=customer_number, name=customer_name or "", phone=parsed_payload.get("phone"), email=parsed_payload.get("email"), street=parsed_payload.get("street"), city=parsed_payload.get("city"), zip=parsed_payload.get("zip"))
            else:
                phone_val = self._normalize_phone(parsed_payload.get("phone"))
                if phone_val:
                    matches = find_by_phone(self.db, phone_val)
                    if len(matches) == 1:
                        customer = matches[0]
        else:
            # low confidence: try to assign if unambiguous, otherwise leave None
            if customer_number:
                customer = get_customer_by_number(self.db, customer_number)
            else:
                phone_val = self._normalize_phone(parsed_payload.get("phone"))
                if phone_val:
                    matches = find_by_phone(self.db, phone_val)
                    if len(matches) == 1:
                        customer = matches[0]

        if not customer:
            # ensure a display name for the job even when customer is unknown
            if not customer_name:
                customer_name = f"Neidentifikovany zakaznik (strana {upload.page_number or 1})"
                parsed_payload["customer_name"] = customer_name
                parsed_data = parsed_payload.get("parsed_data")
                if isinstance(parsed_data, dict):
                    parsed_data["customer_name"] = customer_name

        phone = self._normalize_phone(parsed_payload.get("phone"))
        email = self._normalize_email(parsed_payload.get("email"))
        zip_code = self._normalize_zip(parsed_payload.get("zip"))

        parsed_payload["phone"] = phone
        parsed_payload["email"] = email
        parsed_payload["zip"] = zip_code
        parsed_data = parsed_payload.get("parsed_data")
        if isinstance(parsed_data, dict):
            parsed_data["phone"] = phone
            parsed_data["email"] = email
            parsed_data["zip"] = zip_code

        # ensure parser_confidence is always a float 0.0-1.0
        try:
            parser_confidence = float(parser_confidence) if parser_confidence is not None else 0.0
        except Exception:
            parser_confidence = 0.0
        if parser_confidence < 0.0:
            parser_confidence = 0.0
        if parser_confidence > 1.0:
            parser_confidence = 1.0

        job_data = {
            "job_number": job_number,
            "customer_name": customer_name,
            "phone": phone,
            "email": email,
            "street": parsed_payload.get("street"),
            "city": parsed_payload.get("city"),
            "zip": zip_code,
            "status": "new",
            "parser_confidence": parser_confidence,
            "order_number": parsed_payload.get("order_number") or parsed_payload.get("order"),
        }

        try:
            validated = JobCreate.model_validate(job_data)
            job_data = validated.model_dump()
        except ValidationError as exc:
            used_fallback = True
            fallback_job_data = {
                "job_number": job_number,
                "customer_name": customer_name,
                "status": "new",
            }
            validated = JobCreate.model_validate(fallback_job_data)
            job_data = validated.model_dump()
            upload.error_message = str(exc)[:1000]

        existing = get_job_by_number(self.db, job_data["job_number"])
        if existing:
            used_fallback = True
            job_data["job_number"] = f"{job_data['job_number']}-{upload.id}"

        created = create_job(self.db, job_data)
        # link job and upload via Upload.job_id only (single-direction)
        if customer:
            created.customer_id = customer.id

        # persist additional job fields
        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)

        upload.job_id = created.id
        if used_fallback:
            upload.processing_status = "Vyžaduje kontrolu"
            upload.status = "Vyžaduje kontrolu"
        else:
            upload.processing_status = "Hotovo"
            upload.status = "Hotovo"
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)
        return parsed_payload, created

    def _normalize_phone(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        match = re.search(r"(?:\+\d{1,3}\s?)?(?:\d[\d\s()\-]{5,}\d)", text)
        if not match:
            return None
        normalized = re.sub(r"\s+", " ", match.group(0)).strip(" ;,")
        return normalized or None

    def _normalize_email(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value)
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        if not match:
            return None
        return match.group(0).strip()

    def _normalize_zip(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value)
        match = re.search(r"\b\d{3}\s?\d{2}\b", text)
        if not match:
            return None
        return match.group(0).strip()
