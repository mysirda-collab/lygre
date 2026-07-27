from pathlib import Path
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
# import all models to ensure registries
from app.models import audit_log, calendar_event, customer, job, refresh_token, reservation, sms_log, sms_template, time_slot, upload, user  # noqa: F401
from app.crud.upload import create_upload, get_uploads
from app.services.job_creation_service import JobCreationService
from pypdf import PdfReader, PdfWriter

# prepare clean DB
tmpdir = Path('tmp_integration')
if tmpdir.exists():
    shutil.rmtree(tmpdir)
tmpdir.mkdir()
DB = tmpdir / 'test.db'
engine = create_engine(f'sqlite:///{DB}', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# prepare uploads dir
uploads_dir = tmpdir / 'uploads'
uploads_dir.mkdir()
# copy source pdf
src = Path('backend/uploads/zl2.pdf')
if not src.exists():
    raise SystemExit('backend/uploads/zl2.pdf missing')
shutil.copy(src, uploads_dir / 'zl2.pdf')
reader = PdfReader(str(src))
total = len(reader.pages)

with SessionLocal() as db:
    service = JobCreationService(db)
    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        page_file = uploads_dir / f'page_{i}.pdf'
        with page_file.open('wb') as f:
            writer.write(f)
        upload = create_upload(
            db=db,
            original_filename=f'zl2.pdf - strana {i}/{total}',
            stored_filename=page_file.name,
            file_path=str(page_file),
            content_type='application/pdf',
            file_size=page_file.stat().st_size,
            status='Zpracovává se',
            processing_status='Zpracovává se',
            source_document_id='testsrc',
            source_original_filename='zl2.pdf',
            source_stored_filename='zl2.pdf',
            source_file_path=str(uploads_dir/'zl2.pdf'),
            page_number=i,
            total_pages=total,
        )
        try:
            service.process_upload(upload, str(page_file))
        except Exception as e:
            print('process_upload error on page', i, e)
    uploads = get_uploads(db)
    from sqlalchemy import text
    customers = db.execute(text('SELECT id, name, phone FROM customers')).fetchall()
    jobs = db.execute(text('SELECT id, job_number, customer_name, phone, status FROM jobs')).fetchall()

print('Uploads count', len(uploads))
print('Customers count', len(customers))
print('Jobs count', len(jobs))
print('\nUploads:')
for u in uploads:
    print(u.id, u.original_filename, u.status, u.job_id)
print('\nCustomers:')
for c in customers:
    print(c)
print('\nJobs:')
for j in jobs:
    print(j)
print('\n| Job Number | Customer | Phone | Status |')
for j in jobs:
    print(f"| {j[1] or ''} | {j[2] or ''} | {j[3] or ''} | {j[4] or ''} |")
