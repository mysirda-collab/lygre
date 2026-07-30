import tempfile
import unittest
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.dependencies.database import get_db
from app.main import app as fastapi_app
from app.core.security import hash_password
from app.crud.user import create_user
from app.models.base import Base
from app.models.audit_log import AuditLog
from app.models.calendar_event import CalendarEvent
from app.models.job import Job, JobNote, JobStatusHistory
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models import audit_log as _audit_log  # noqa: F401
from app.models import calendar_event as _calendar_event  # noqa: F401
from app.models import customer as _customer  # noqa: F401
from app.models import job as _job  # noqa: F401
from app.models import refresh_token as _refresh_token  # noqa: F401
from app.models import reservation as _reservation  # noqa: F401
from app.models import sms_log as _sms_log  # noqa: F401
from app.models import sms_template as _sms_template  # noqa: F401
from app.models import time_slot as _time_slot  # noqa: F401
from app.models import upload as _upload  # noqa: F401
from app.models import user as _user  # noqa: F401
from app.models.customer import Customer
from app.models.reservation import Reservation
from app.models.sms_log import SmsLog
from app.models.time_slot import TimeSlot
from app.models.upload import Upload
from app.services.auth_service import seed_admin_user


class ApiIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp_dir = tempfile.TemporaryDirectory()
        cls.db_file = Path(cls.tmp_dir.name) / "test.db"
        cls.upload_dir = Path(cls.tmp_dir.name) / "uploads"
        cls.upload_dir.mkdir(parents=True, exist_ok=True)

        db_url = f"sqlite:///{cls.db_file}"
        cls.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        fastapi_app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(fastapi_app)

    @classmethod
    def tearDownClass(cls) -> None:
        fastapi_app.dependency_overrides.clear()
        cls.engine.dispose()
        cls.tmp_dir.cleanup()

    def setUp(self) -> None:
        with self.SessionLocal() as db:
            db.query(Upload).delete()
            db.query(JobNote).delete()
            db.query(JobStatusHistory).delete()
            db.query(SmsLog).delete()
            db.query(Reservation).delete()
            db.query(TimeSlot).delete()
            db.query(RefreshToken).delete()
            db.query(AuditLog).delete()
            db.query(CalendarEvent).delete()
            db.query(Job).delete()
            db.query(Customer).delete()
            db.query(User).filter(User.email != "admin@lygre.local").delete()
            seed_admin_user(
                db,
                email="admin@lygre.local",
                full_name="Default Admin",
                password="Admin123!",
            )
            db.commit()

    def _login_admin(self) -> tuple[dict[str, str], str]:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@lygre.local", "password": "Admin123!"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        access_token = payload["access_token"]
        refresh_token = payload["refresh_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        return headers, refresh_token

    def _create_job_payload(self, job_number: str = "A-1000") -> dict:
        return {
            "job_number": job_number,
            "status": "new",
            "priority": "medium",
            "customer_name": "Jan Novak",
            "company": None,
            "phone": "+420 603 111 222",
            "email": "jan.novak@example.com",
            "street": "Hlavni 1",
            "city": "Praha",
            "zip": "110 00",
            "installation_date": None,
            "technician": None,
            "notes": None,
        }

    def _create_worker(self, email: str = "technik@lygre.local", full_name: str = "Pavel Technik") -> int:
        with self.SessionLocal() as db:
            worker = create_user(
                db,
                email=email,
                full_name=full_name,
                password_hash=hash_password("Worker123!"),
                role="worker",
                is_active=True,
            )
            return worker.id

    def test_health_endpoint(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_modules_endpoint(self) -> None:
        headers, _ = self._login_admin()
        response = self.client.get("/api/v1/modules", headers=headers)
        self.assertEqual(response.status_code, 200)
        modules = response.json()
        self.assertTrue(any(item["name"] == "orders" for item in modules))

    def test_root_endpoint(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Lygre API is running"})

    def test_jobs_crud_flow(self) -> None:
        headers, _ = self._login_admin()
        create_response = self.client.post("/api/v1/jobs", json=self._create_job_payload("A-1001"), headers=headers)
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()

        list_response = self.client.get("/api/v1/jobs", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(list_response.json()["total"], 1)

        update_payload = self._create_job_payload("A-1001")
        update_payload["customer_name"] = "Petr Novak"
        update_response = self.client.put(f"/api/v1/jobs/{created['id']}", json=update_payload, headers=headers)
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["customer_name"], "Petr Novak")

        delete_response = self.client.delete(f"/api/v1/jobs/{created['id']}", headers=headers)
        self.assertEqual(delete_response.status_code, 204)

    def test_jobs_validation_rejects_invalid_email(self) -> None:
        headers, _ = self._login_admin()
        payload = self._create_job_payload("A-2001")
        payload["email"] = "not-an-email"
        response = self.client.post("/api/v1/jobs", json=payload, headers=headers)
        self.assertEqual(response.status_code, 422)

    def test_job_notes_record_authenticated_author_and_editor(self) -> None:
        headers, _ = self._login_admin()
        created_job = self.client.post("/api/v1/jobs", json=self._create_job_payload("NOTE-1001"), headers=headers).json()

        create_response = self.client.post(
            f"/api/v1/jobs/{created_job['id']}/notes",
            json={"text": "První poznámka"},
            headers=headers,
        )
        self.assertEqual(create_response.status_code, 201)
        created_note = create_response.json()
        self.assertEqual(created_note["author_name"], "Default Admin")
        self.assertIsNotNone(created_note["author_user_id"])
        self.assertIsNotNone(created_note["created_at"])
        self.assertIsNone(created_note["updated_at"])

        original_author_id = created_note["author_user_id"]
        original_created_at = created_note["created_at"]
        worker_id = self._create_worker()
        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "technik@lygre.local", "password": "Worker123!"},
        )
        worker_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        update_response = self.client.put(
            f"/api/v1/jobs/{created_job['id']}/notes/{created_note['id']}",
            json={"text": "Upravená poznámka"},
            headers=worker_headers,
        )
        self.assertEqual(update_response.status_code, 200)
        updated_note = update_response.json()
        self.assertEqual(updated_note["author_user_id"], original_author_id)
        self.assertEqual(updated_note["created_at"], original_created_at)
        self.assertEqual(updated_note["updated_by_user_id"], worker_id)
        self.assertEqual(updated_note["updated_by_name"], "Pavel Technik")
        self.assertIsNotNone(updated_note["updated_at"])

        notes_response = self.client.get(f"/api/v1/jobs/{created_job['id']}/notes", headers=headers)
        self.assertEqual(notes_response.status_code, 200)
        self.assertEqual(notes_response.json()[0]["text"], "Upravená poznámka")

        detail = self.client.get(f"/api/v1/jobs/{created_job['id']}/detail", headers=headers).json()
        history_messages = [item["details"] for item in detail["audit_logs"]]
        self.assertIn("Přidána poznámka.", history_messages)
        self.assertIn("Upravena poznámka.", history_messages)

    def test_job_notes_reject_empty_text_and_cross_job_edit(self) -> None:
        headers, _ = self._login_admin()
        first_job = self.client.post("/api/v1/jobs", json=self._create_job_payload("NOTE-2001"), headers=headers).json()
        second_job = self.client.post("/api/v1/jobs", json=self._create_job_payload("NOTE-2002"), headers=headers).json()
        empty_response = self.client.post(
            f"/api/v1/jobs/{first_job['id']}/notes",
            json={"text": "   "},
            headers=headers,
        )
        self.assertEqual(empty_response.status_code, 422)

        note = self.client.post(
            f"/api/v1/jobs/{first_job['id']}/notes",
            json={"text": "Patří první zakázce"},
            headers=headers,
        ).json()
        cross_edit = self.client.put(
            f"/api/v1/jobs/{second_job['id']}/notes/{note['id']}",
            json={"text": "Nepovolená změna"},
            headers=headers,
        )
        self.assertEqual(cross_edit.status_code, 404)

    def test_auth_refresh_logout_flow(self) -> None:
        headers, refresh_token = self._login_admin()

        me_response = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["email"], "admin@lygre.local")

        refresh_response = self.client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        self.assertEqual(refresh_response.status_code, 200)
        refreshed_access = refresh_response.json()["access_token"]
        self.assertTrue(isinstance(refreshed_access, str))

        logout_response = self.client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        self.assertEqual(logout_response.status_code, 204)

        refresh_after_logout = self.client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        self.assertEqual(refresh_after_logout.status_code, 401)

    def test_protected_endpoint_requires_auth(self) -> None:
        response = self.client.get("/api/v1/jobs")
        self.assertEqual(response.status_code, 401)

    def test_customers_endpoint_requires_auth(self) -> None:
        # ensure customers endpoints are protected
        response = self.client.get("/api/v1/customers")
        self.assertEqual(response.status_code, 401)

    def test_upload_invalid_type_rejected(self) -> None:
        headers, _ = self._login_admin()
        response = self.client.post(
            "/api/v1/uploads/pdf",
            files={"file": ("test.txt", b"hello", "text/plain")},
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_runtime_failure_sets_error_status(self) -> None:
        headers, _ = self._login_admin()
        with patch("app.api.v1.endpoints.uploads.settings.uploads_dir", str(self.upload_dir)):
            response = self.client.post(
                "/api/v1/uploads/pdf",
                files={"file": ("broken.pdf", b"not-a-real-pdf", "application/pdf")},
                headers=headers,
            )
        self.assertEqual(response.status_code, 201)
        upload_id = response.json()["id"]

        detail = self.client.get(f"/api/v1/uploads/pdf/{upload_id}", headers=headers)
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertEqual(body["status"], "Vyžaduje kontrolu")
        self.assertEqual(body["processing_status"], "Vyžaduje kontrolu")

    def test_upload_review_creates_job(self) -> None:
        headers, _ = self._login_admin()
        with self.SessionLocal() as db:
            upload = Upload(
                original_filename="manual.pdf",
                stored_filename="manual.pdf",
                file_path=str(self.upload_dir / "manual.pdf"),
                content_type="application/pdf",
                file_size=100,
                status="Vyžaduje kontrolu",
                processing_status="Vyžaduje kontrolu",
            )
            db.add(upload)
            db.commit()
            db.refresh(upload)
            upload_id = upload.id

        review_response = self.client.post(
            f"/api/v1/uploads/pdf/{upload_id}/review",
            json=self._create_job_payload("A-3001"),
            headers=headers,
        )
        self.assertEqual(review_response.status_code, 200)
        created_job = review_response.json()
        self.assertEqual(created_job["job_number"], "A-3001")

        upload_detail = self.client.get(f"/api/v1/uploads/pdf/{upload_id}", headers=headers)
        self.assertEqual(upload_detail.status_code, 200)
        self.assertEqual(upload_detail.json()["status"], "Hotovo")
        self.assertIsNotNone(upload_detail.json()["job_id"])

    def test_e2e_import_11_page_pdf_creates_uploads_and_jobs(self) -> None:
        headers, _ = self._login_admin()
        # build 11-page PDF in-memory
        writer = PdfWriter()
        for i in range(11):
            writer.add_blank_page(width=200, height=200)
        bio = BytesIO()
        writer.write(bio)
        bio.seek(0)

        with patch("app.api.v1.endpoints.uploads.settings.uploads_dir", str(self.upload_dir)):
            response = self.client.post(
                "/api/v1/uploads/pdf",
                files={"file": ("test_11.pdf", bio.read(), "application/pdf")},
                headers=headers,
            )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body.get("created_count"), 11)

        # verify DB objects linked
        with self.SessionLocal() as db:
            uploads = db.query(Upload).order_by(Upload.id.desc()).limit(11).all()
            self.assertEqual(len(uploads), 11)
            jobs = db.query(Job).order_by(Job.id.desc()).limit(11).all()
            self.assertEqual(len(jobs), 11)
            # ensure parser_confidence is present and between 0.0 and 1.0
            for job in jobs:
                self.assertIsNotNone(job.parser_confidence)
                self.assertGreaterEqual(job.parser_confidence, 0.0)
                self.assertLessEqual(job.parser_confidence, 1.0)
            # ensure uploads point to jobs via job_id
            for u in uploads:
                self.assertIsNotNone(u.job_id)

    def test_upload_file_returns_404_when_missing(self) -> None:
        headers, _ = self._login_admin()
        with self.SessionLocal() as db:
            upload = Upload(
                original_filename="missing.pdf",
                stored_filename="missing.pdf",
                file_path=str(self.upload_dir / "missing.pdf"),
                content_type="application/pdf",
                file_size=100,
                status="Hotovo",
                processing_status="Hotovo",
            )
            db.add(upload)
            db.commit()
            db.refresh(upload)
            upload_id = upload.id

        response = self.client.get(f"/api/v1/uploads/pdf/{upload_id}/file", headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_calendar_events_crud_collision_and_filter(self) -> None:
        headers, _ = self._login_admin()
        worker_id = self._create_worker()

        create_job = self.client.post("/api/v1/jobs", json=self._create_job_payload("A-4001"), headers=headers)
        self.assertEqual(create_job.status_code, 201)
        job_id = create_job.json()["id"]

        payload = {
            "title": "Montaz A-4001",
            "event_type": "installation",
            "starts_at": "2026-07-25T08:00:00Z",
            "ends_at": "2026-07-25T10:00:00Z",
            "job_id": job_id,
            "technician_id": worker_id,
            "notes": "Prvni navsteva",
        }

        create_event = self.client.post("/api/v1/calendar/events", json=payload, headers=headers)
        self.assertEqual(create_event.status_code, 201)
        event = create_event.json()
        self.assertEqual(event["job_id"], job_id)
        self.assertEqual(event["technician_id"], worker_id)

        conflicting = self.client.post(
            "/api/v1/calendar/events",
            json={
                **payload,
                "title": "Kolize",
                "starts_at": "2026-07-25T09:00:00Z",
                "ends_at": "2026-07-25T11:00:00Z",
            },
            headers=headers,
        )
        self.assertEqual(conflicting.status_code, 409)

        events_list = self.client.get(
            f"/api/v1/calendar/events?start=2026-07-25T00:00:00Z&end=2026-07-26T00:00:00Z&technician_id={worker_id}",
            headers=headers,
        )
        self.assertEqual(events_list.status_code, 200)
        items = events_list.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], event["id"])

        reschedule = self.client.patch(
            f"/api/v1/calendar/events/{event['id']}/schedule",
            json={
                "starts_at": "2026-07-25T11:00:00Z",
                "ends_at": "2026-07-25T13:00:00Z",
            },
            headers=headers,
        )
        self.assertEqual(reschedule.status_code, 200)
        self.assertTrue(reschedule.json()["starts_at"].startswith("2026-07-25T11:00:00"))

        delete_event = self.client.delete(f"/api/v1/calendar/events/{event['id']}", headers=headers)
        self.assertEqual(delete_event.status_code, 204)

        with self.SessionLocal() as db:
            logs = db.query(AuditLog).filter(AuditLog.entity_type == "calendar_event").all()
            self.assertGreaterEqual(len(logs), 3)

    def test_calendar_slots_crud_and_availability(self) -> None:
        headers, _ = self._login_admin()

        create = self.client.post(
            "/api/v1/calendar/slots",
            json={
                "start": "2026-08-10T08:00:00Z",
                "end": "2026-08-10T10:00:00Z",
                "capacity": 2,
                "enabled": True,
                "blocked": False,
                "technician": "Pavel",
                "title": "Montaz rano",
                "location": "Praha",
                "installation_type": "Standard",
            },
            headers=headers,
        )
        self.assertEqual(create.status_code, 201)
        slot_id = create.json()["id"]

        conflict = self.client.post(
            "/api/v1/calendar/slots",
            json={
                "start": "2026-08-10T09:00:00Z",
                "end": "2026-08-10T11:00:00Z",
                "capacity": 1,
                "enabled": True,
                "blocked": False,
                "technician": "Pavel",
                "location": "Brno",
                "installation_type": "Standard",
            },
            headers=headers,
        )
        self.assertEqual(conflict.status_code, 409)

        update = self.client.put(
            f"/api/v1/calendar/slots/{slot_id}",
            json={
                "capacity": 3,
                "location": "Praha 1",
            },
            headers=headers,
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["capacity"], 3)

        available_before_block = self.client.get(
            "/api/v1/calendar/available-slots?start=2026-08-10T07:00:00Z&end=2026-08-10T12:00:00Z&technician=Pavel&required_capacity=1",
            headers=headers,
        )
        self.assertEqual(available_before_block.status_code, 200)
        self.assertEqual(len(available_before_block.json()["items"]), 1)

        block = self.client.patch(
            f"/api/v1/calendar/slots/{slot_id}/block",
            json={"blocked": True, "disable": True},
            headers=headers,
        )
        self.assertEqual(block.status_code, 200)
        self.assertTrue(block.json()["blocked"])
        self.assertFalse(block.json()["enabled"])

        available_after_block = self.client.get(
            "/api/v1/calendar/available-slots?start=2026-08-10T07:00:00Z&end=2026-08-10T12:00:00Z&technician=Pavel&required_capacity=1",
            headers=headers,
        )
        self.assertEqual(available_after_block.status_code, 200)
        self.assertEqual(len(available_after_block.json()["items"]), 0)

    def test_reservation_public_confirm_flow_creates_sms_log(self) -> None:
        headers, _ = self._login_admin()

        customer_create = self.client.post(
            "/api/v1/customers",
            json={
                "customer_number": "C-RES-001",
                "name": "Zakaznik Rezervace",
                "phone": "+420603000111",
                "email": "rezervace@example.com",
                "street": "Ulice 1",
                "city": "Praha",
                "zip": "11000",
            },
            headers=headers,
        )
        self.assertEqual(customer_create.status_code, 200)
        customer_id = customer_create.json()["id"]

        job_create = self.client.post("/api/v1/jobs", json=self._create_job_payload("A-RES-FLOW-1"), headers=headers)
        self.assertEqual(job_create.status_code, 201)
        job_id = job_create.json()["id"]

        slot_create = self.client.post(
            "/api/v1/calendar/slots",
            json={
                "start": "2026-08-20T08:00:00Z",
                "end": "2026-08-20T10:00:00Z",
                "capacity": 2,
                "enabled": True,
                "blocked": False,
                "technician": "Pavel",
                "location": "Praha",
            },
            headers=headers,
        )
        self.assertEqual(slot_create.status_code, 201)
        slot_id = slot_create.json()["id"]

        create_request = self.client.post(
            "/api/v1/reservations",
            json={"job_id": job_id, "customer_id": customer_id},
            headers=headers,
        )
        self.assertEqual(create_request.status_code, 201)
        token = create_request.json()["token"]

        status_check = self.client.get(f"/api/v1/reservations/public/{token}")
        self.assertEqual(status_check.status_code, 200)
        self.assertFalse(status_check.json()["token_used"])

        context_before = self.client.get(f"/api/v1/reservations/public/{token}/context")
        self.assertEqual(context_before.status_code, 200)
        context_body = context_before.json()
        self.assertEqual(context_body["customer_name"], "Zakaznik Rezervace")
        self.assertEqual(context_body["job_number"], "A-RES-FLOW-1")
        self.assertEqual(context_body["reservation_status"], "requested")
        self.assertTrue(context_body["can_confirm"])
        self.assertIsNone(context_body["selected_slot"])

        available = self.client.get(
            "/api/v1/reservations/public/"
            + token
            + "/available-slots?start=2026-08-20T00:00:00Z&end=2026-08-21T00:00:00Z&required_capacity=1"
        )
        self.assertEqual(available.status_code, 200)
        self.assertEqual(len(available.json()["items"]), 1)

        confirm = self.client.post(
            "/api/v1/reservations/public/confirm",
            json={"token": token, "slot_id": slot_id},
        )
        self.assertEqual(confirm.status_code, 200)
        body = confirm.json()
        self.assertEqual(body["status"], "confirmed")
        self.assertTrue(body["token_used"])
        self.assertIsNotNone(body["confirmation_sent_at"])

        context_after = self.client.get(f"/api/v1/reservations/public/{token}/context")
        self.assertEqual(context_after.status_code, 200)
        context_after_body = context_after.json()
        self.assertEqual(context_after_body["reservation_status"], "confirmed")
        self.assertFalse(context_after_body["can_confirm"])
        self.assertTrue(context_after_body["token_used"])
        self.assertIsNotNone(context_after_body["selected_slot"])
        self.assertEqual(context_after_body["selected_slot"]["id"], slot_id)

        with self.SessionLocal() as db:
            logs = db.query(SmsLog).filter(SmsLog.type == "reservation_confirmation").all()
            self.assertGreaterEqual(len(logs), 1)
            self.assertEqual(logs[-1].status, "sent")

    def test_upload_pdf_creates_record_per_page(self) -> None:
        headers, _ = self._login_admin()

        writer = PdfWriter()
        for _ in range(4):
            writer.add_blank_page(width=595, height=842)
        buffer = BytesIO()
        writer.write(buffer)
        pdf_bytes = buffer.getvalue()

        with patch("app.api.v1.endpoints.uploads.settings.uploads_dir", str(self.upload_dir)), patch(
            "app.api.v1.endpoints.uploads.JobCreationService.process_upload", return_value=({}, None)
        ):
            response = self.client.post(
                "/api/v1/uploads/pdf",
                files={"file": ("four-pages.pdf", pdf_bytes, "application/pdf")},
                headers=headers,
            )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["created_count"], 4)
        self.assertEqual(len(body["created_ids"]), 4)
        self.assertEqual(body["total_pages"], 4)
        self.assertEqual(body["source_original_filename"], "four-pages.pdf")
        self.assertTrue(body.get("source_document_id"))

        uploads = self.client.get("/api/v1/uploads/pdf", headers=headers)
        self.assertEqual(uploads.status_code, 200)
        items = uploads.json()
        page_uploads = [item for item in items if item["original_filename"].startswith("four-pages.pdf - strana ")]
        self.assertEqual(len(page_uploads), 4)
        page_numbers = sorted(item.get("page_number") for item in page_uploads)
        self.assertEqual(page_numbers, [1, 2, 3, 4])
        self.assertTrue(all(item.get("total_pages") == 4 for item in page_uploads))

    def test_jobs_list_handles_legacy_invalid_phone(self) -> None:
        headers, _ = self._login_admin()
        with self.SessionLocal() as db:
            job = Job(
                job_number="LEGACY-1",
                status="new",
                priority="medium",
                customer_name="Legacy Customer",
                phone="605041013; Františka Krejčířová",
                email="legacy@example.com",
                street="Test 1",
                city="Brno",
                zip="60200",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                is_deleted=False,
            )
            db.add(job)
            db.commit()

        response = self.client.get("/api/v1/jobs", headers=headers)
        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        legacy = next((item for item in items if item["job_number"] == "LEGACY-1"), None)
        self.assertIsNotNone(legacy)
        self.assertEqual(legacy["phone"], "605041013")

    def test_upload_source_file_download(self) -> None:
        headers, _ = self._login_admin()

        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        buffer = BytesIO()
        writer.write(buffer)
        pdf_bytes = buffer.getvalue()

        with patch("app.api.v1.endpoints.uploads.settings.uploads_dir", str(self.upload_dir)), patch(
            "app.api.v1.endpoints.uploads.JobCreationService.process_upload", return_value=({}, None)
        ):
            response = self.client.post(
                "/api/v1/uploads/pdf",
                files={"file": ("single-page.pdf", pdf_bytes, "application/pdf")},
                headers=headers,
            )

        self.assertEqual(response.status_code, 201)
        upload_id = response.json()["id"]

        source_response = self.client.get(f"/api/v1/uploads/pdf/{upload_id}/source-file", headers=headers)
        self.assertEqual(source_response.status_code, 200)
        self.assertGreater(len(source_response.content), 10)


if __name__ == "__main__":
    unittest.main()
