from datetime import datetime
import re
from typing import Any
import logging

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
        # extract full text
        text = self.parser.extract_text_from_pdf(file_path)
        # try to decode QR from the single-page PDF bytes (if available)
        qr_job = None
        try:
            from pathlib import Path
            p = Path(file_path)
            data = p.read_bytes()
            candidates = self.parser.extract_order_sheet_candidates(data)
            for cand in candidates:
                try:
                    q = self.parser._extract_qr_job_number(cand.page_pdf_bytes)
                    if q:
                        qr_job = q
                        break
                except Exception:
                    continue
        except Exception:
            qr_job = None

        return self.process_upload_text(upload, text, qr_job=qr_job)

    def process_upload_text(self, upload: Upload, text: str, qr_job: str | None = None) -> tuple[dict[str, Any], Job | None]:
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
            pd = parsed_payload.get("parsed_data")
            if isinstance(pd, dict):
                parser_confidence = pd.get("parser_confidence")
        try:
            parser_confidence = float(parser_confidence) if parser_confidence is not None else None
        except Exception:
            parser_confidence = None

        # Prefer QR job number when present (authoritative). Do not fallback
        # to order_number if QR exists.
        job_number = None
        if qr_job:
            job_number = qr_job
            parsed_payload["job_number"] = job_number
        else:
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
        if customer_number:
            customer = get_customer_by_number(self.db, customer_number)
        if not customer:
            phone_val = self._normalize_phone(parsed_payload.get("phone"))
            if phone_val:
                cid = _uuid.uuid4().hex
                customer = find_or_create(self.db, uuid=cid, customer_number=None, name=customer_name or "", phone=phone_val, email=parsed_payload.get("email"), street=parsed_payload.get("street"), city=parsed_payload.get("city"), zip=parsed_payload.get("zip"))

        if not customer:
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
            "status": "scheduled",
            "parser_confidence": parser_confidence,
            "order_number": parsed_payload.get("order_number") or parsed_payload.get("order"),
        }

        try:
            validated = JobCreate.model_validate(job_data)
            job_data = validated.model_dump()
        except ValidationError as exc:
            # Log full validation error
            logging.exception("JobCreate validation failed for upload id %s: %s", upload.id if upload else None, exc)
            # If customer_name field triggered validation error, log details for debugging
            err_text = str(exc)
            if "customer_name" in err_text:
                try:
                    page_no = getattr(upload, 'page_number', None)
                    cn = parsed_payload.get('customer_name')
                    ln = len(cn) if cn is not None else 0
                    logging.error("Validation failure on customer_name - page=%s, len=%s, value=%s", page_no, ln, repr(cn))
                    logging.error("Full parsed_payload for upload id %s: %s", upload.id if upload else None, parsed_payload)
                except Exception:
                    pass
            upload.error_message = str(exc)[:1000]
            self.db.add(upload)
            self.db.commit()
            # re-raise so caller (endpoint/test) sees the error
            raise

        existing = get_job_by_number(self.db, job_data["job_number"])
        if existing:
            created = existing
        else:
            created = create_job(self.db, job_data)

        if customer:
            created.customer_id = customer.id

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
        # remove common separators
        cleaned = re.sub(r"[\s()\-./]", "", text)
        # if contains letters, try to extract digit sequence
        if re.search(r"[A-Za-zÁ-ž]", cleaned):
            m = re.search(r"(?:\+?\d{6,}\d?)", cleaned)
            if not m:
                return None
            cleaned = m.group(0)
        digits = re.sub(r"\D", "", cleaned)
        if len(digits) < 6:
            return None
        if cleaned.startswith("+"):
            return "+" + digits
        return digits

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
