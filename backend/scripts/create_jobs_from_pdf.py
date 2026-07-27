from pathlib import Path
from pypdf import PdfReader
from app.services.pdf_parser_service import PdfParserService
from app.services.vodafone_parser import VodafoneParser
from app.dependencies.database import SessionLocal
from app.crud.customer import find_or_create
from app.crud.job import create_job, get_job_by_number


def main(pdf_path: str):
    p = Path(pdf_path)
    reader = PdfReader(str(p))
    svc = PdfParserService()
    vp = VodafoneParser()

    with SessionLocal() as db:
        for i, page in enumerate(reader.pages, start=1):
            page_bytes = svc._build_single_page_pdf_bytes(page)
            text = page.extract_text() or ''
            if not text:
                text = svc._extract_page_text_with_ocr(page_bytes, i) or ''
            # allow QR-prepend as in service
            qr = svc._extract_qr_job_number(page_pdf_bytes)
            if qr:
                text = f"Číslo objednávky: {qr}\n" + text
            parsed = vp.build_parsed_payload(text)

            phone = parsed.get('phone') or None
            name = parsed.get('customer_name') or None
            job_number = parsed.get('job_number') or None
            street = parsed.get('address') or None

            if not job_number:
                continue

            # avoid duplicate job_number
            existing = get_job_by_number(db, job_number)
            if existing:
                print(f"Stránka {i}: job {job_number} already exists (id={existing.id})")
                continue

            customer = find_or_create(db, uuid=None, customer_number=None, name=name, phone=phone, street=street)

            job_data = {
                'job_number': job_number,
                'status': 'scheduled',
                'customer_name': name or '',
                'phone': phone,
                'street': street,
                'city': None,
                'customer_id': customer.id,
            }
            job = create_job(db, job_data)
            print(f"Stránka {i}: created job {job.job_number} id={job.id} for customer id={customer.id}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: create_jobs_from_pdf.py <pdf_path>')
        sys.exit(1)
    main(sys.argv[1])
