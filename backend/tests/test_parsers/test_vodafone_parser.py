from pathlib import Path
import sys
from pathlib import Path as _P
# ensure backend folder is on sys.path
sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
from app.services.vodafone_parser import VodafoneParser
from pypdf import PdfReader


def test_vodafone_parser_page2():
    p = VodafoneParser()
    pdf = Path("uploads/zl2.pdf")
    assert pdf.exists(), "uploads/zl2.pdf must exist"
    reader = PdfReader(str(pdf))
    # use page 6 which contains the sample Vodafone fields
    text = reader.pages[5].extract_text() or ""
    out = p.build_parsed_payload(text)
    assert set(out.keys()) == {"customer_name", "address", "phone", "job_number"}
    # expected exact values for this sample page
    assert out["customer_name"] == "Jan Novák"
    assert out["job_number"] == "A-1001"
    assert out["phone"] == "+420 603 111 222"
    assert out["address"] == "Hlavní 123, Praha"
