from datetime import datetime
import re
from typing import Any
import logging
log = logging.getLogger(__name__)

from pydantic import ValidationError
from sqlalchemy.orm import Session

from sqlalchemy import func, select

from app.crud.job import get_job_by_number
from app.crud.customer import get_customer_by_number
import uuid as _uuid
from app.models.customer import Customer
from app.models.job import Job, JobStatusHistory
from app.models.upload import Upload
from app.schemas.job import JobCreate
from app.services.pdf_parser_service import PdfParserService
from app.services.ai_extraction_service import enrich_with_optional_ai
from app.services.upload_progress_service import UploadProgressReporter, mark_upload_failed


class JobCreationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.parser = PdfParserService()
        self._progress_reporter: UploadProgressReporter | None = None

    def _update_progress(
        self,
        upload: Upload,
        progress: int,
        message: str,
        processing_status: str = "Zpracovává se",
        *,
        force: bool = False,
    ) -> None:
        if self._progress_reporter is None or self._progress_reporter.upload_id != upload.id:
            self._progress_reporter = UploadProgressReporter(upload.id)
        self._progress_reporter.report(
            progress,
            message,
            processing_status=processing_status,
            force=force,
        )

    def process_upload(self, upload: Upload, file_path: str) -> tuple[dict[str, Any], Job | None]:
        self._update_progress(upload, 5, "Inicializuji zpracování PDF", force=True)
        # extract full text
        log.warning("1. extract_text_from_pdf START %s", upload.id)
        text = self.parser.extract_text_from_pdf(
            file_path,
            progress_callback=lambda progress, message: self._update_progress(
                upload,
                progress,
                message,
                force=progress in {10, 20, 50},
            ),
        )
        log.warning("2. extract_text_from_pdf END %s", upload.id)
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

        log.warning("3. process_upload_text START %s", upload.id)
        result = self.process_upload_text(upload, text, qr_job=qr_job)
        log.warning("4. process_upload_text END %s", upload.id)
        return result

    def process_upload_text(self, upload: Upload, text: str, qr_job: str | None = None) -> tuple[dict[str, Any], Job | None]:
        self._update_progress(upload, 60, "Parsování dokumentu", force=True)
        parsed_payload = self.parser.build_parsed_payload(text)
        parsed_payload["parsed_data"] = enrich_with_optional_ai(text, parsed_payload["parsed_data"])
        for key in ("job_number", "customer_name", "phone", "email", "street", "city", "zip", "order_number", "customer_number"):
            if not parsed_payload.get(key):
                parsed_payload[key] = parsed_payload["parsed_data"].get(key)

        upload.extracted_text = text
        upload.parsed_data = parsed_payload["parsed_data"]
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

        existing = get_job_by_number(self.db, job_number)

        customer_number = self._normalize_identifier(parsed_payload.get("customer_number"))
        customer_name = parsed_payload.get("customer_name")
        customer = existing.customer if existing and existing.customer_id else None
        phone = self._normalize_phone(parsed_payload.get("phone"))
        email = self._normalize_email(parsed_payload.get("email"))
        zip_code = self._normalize_zip(parsed_payload.get("zip"))
        self._update_progress(upload, 75, "Vyhledávám existujícího zákazníka", force=True)
        if customer_number:
            customer = get_customer_by_number(self.db, customer_number)
        if not customer and phone:
            normalized_phone_column = Customer.phone
            for separator in (" ", "-", "(", ")", ".", "/"):
                normalized_phone_column = func.replace(normalized_phone_column, separator, "")
            customer = self.db.scalar(select(Customer).where(normalized_phone_column == phone))
        if not customer and email:
            customer = self.db.scalar(select(Customer).where(func.lower(Customer.email) == email))

        if not customer:
            if not customer_name:
                customer_name = f"Neidentifikovany zakaznik (strana {upload.page_number or 1})"
                parsed_payload["customer_name"] = customer_name
                parsed_data = parsed_payload.get("parsed_data")
                if isinstance(parsed_data, dict):
                    parsed_data["customer_name"] = customer_name

            self._update_progress(upload, 85, "Zakládám zákazníka", force=True)
            cid = _uuid.uuid4().hex
            customer = Customer(
                uuid=cid,
                customer_number=customer_number or f"AUTO-{upload.id}-{cid[:8]}",
                name=customer_name,
                phone=phone,
                email=email,
                street=parsed_payload.get("street"),
                city=parsed_payload.get("city"),
                zip=zip_code,
            )
            self.db.add(customer)
            self.db.flush()

        parsed_payload["phone"] = phone
        parsed_payload["email"] = email
        parsed_payload["zip"] = zip_code
        parsed_data = parsed_payload.get("parsed_data")
        if isinstance(parsed_data, dict):
            parsed_data["phone"] = phone
            parsed_data["email"] = email
            parsed_data["zip"] = zip_code
            parsed_data["customer_number"] = customer_number

        warnings = list(parsed_payload.get("missing_fields") or [])
        if used_fallback and not warnings:
            warnings.append("Parser neposkytl dostatek spolehlivých údajů")
        parsed_data["validation_warnings"] = warnings
        parsed_data["review_required"] = bool(used_fallback or warnings or parser_confidence is None)

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
            "status": "Vyžaduje kontrolu" if parsed_data["review_required"] else "Nová",
            "parser_confidence": parser_confidence,
            "order_number": parsed_payload.get("order_number") or parsed_payload.get("order"),
        }

        self._update_progress(upload, 92, "Vytvářím zakázku", force=True)
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
            mark_upload_failed(upload.id, message="Zpracování skončilo chybou validace", error_message=str(exc))
            # re-raise so caller (endpoint/test) sees the error
            raise

        if existing:
            created = existing
        else:
            created = Job(**job_data)
            created.customer_id = customer.id
            self.db.add(created)
            self.db.flush()
            self.db.add(JobStatusHistory(job_id=created.id, previous_status=None, new_status=created.status))

        if created.customer_id is None:
            created.customer_id = customer.id

        self._update_progress(upload, 98, "Ukládám výsledky zpracování", force=True)
        upload.job_id = created.id
        upload.parsed_data = dict(parsed_data)
        if parsed_data["review_required"]:
            upload.status = "Vyžaduje kontrolu"
            final_processing_status = "Vyžaduje kontrolu"
            final_message = "Dokončeno, údaje vyžadují kontrolu"
        else:
            upload.status = "Hotovo"
            final_processing_status = "Hotovo"
            final_message = "Zpracování dokončeno"
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)
        self._update_progress(upload, 100, final_message, processing_status=final_processing_status, force=True)
        return parsed_payload, created

    def _normalize_identifier(self, value: Any) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"\s+", "", str(value)).strip("-:;,/")
        return normalized.upper() or None

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
        return match.group(0).replace(" ", "")

    def _normalize_zip(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value)
        match = re.search(r"\b\d{3}\s?\d{2}\b", text)
        if not match:
            return None
        return match.group(0).strip().lower()
