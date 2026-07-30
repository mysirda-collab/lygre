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


def test_extract_phone_supports_czech_formats_with_and_without_prefix():
    parser = VodafoneParser()

    assert parser.extract_phone("Kontaktni telefon: +420 603 111 222 Instrukce") == "+420 603 111 222"
    assert parser.extract_phone("Kontaktní telefon: 420603111222 Instrukce") == "+420 603 111 222"
    assert parser.extract_phone("Kontaktni telefon 603-111-222 Instrukce") == "603 111 222"
    assert parser.extract_phone("Mobil: 777123456") == "777 123 456"
    assert parser.extract_phone("Tel. +420777123456") == "+420 777 123 456"


def test_extract_address_combines_ocr_split_street_and_house_number():
    parser = VodafoneParser()
    text = "Ulice (nazev obce): Hlavní\nČ. popisné: 123\nPatro: 2 Město: Praha"

    assert parser.extract_address(parser.normalize_text(text)) == "Hlavní 123, Praha"

    suffix_text = "Ulice (nazev obce): Novákova\nČ. popisné: 15a\nPatro: 1 Město: Brno"
    assert parser.extract_address(parser.normalize_text(suffix_text)) == "Novákova 15a, Brno"
