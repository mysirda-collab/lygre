from pathlib import Path
from app.services.pdf_parser_service import PdfParserService


def test_parse_sample_page():
    svc = PdfParserService()
    sample_path = Path("uploads/zl2.pdf")
    assert sample_path.exists(), "uploads/zl2.pdf must exist for test"
    # parse second page text only
    from pypdf import PdfReader
    reader = PdfReader(str(sample_path))
    page = reader.pages[1]
    text = page.extract_text() or ""
    parsed = svc.build_parsed_payload(text)
    # basic assertions: customer_name and order_id should be present for page 2
    assert parsed.get("customer_name") is not None
    assert parsed.get("order_id") is not None or parsed.get("order_number") is not None
    # phone should be present or None but key exists
    assert "phone" in parsed
