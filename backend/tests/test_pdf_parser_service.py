import unittest
from unittest.mock import MagicMock, patch

from app.services.pdf_parser_service import PdfParserService


class PdfParserServiceTest(unittest.TestCase):
    def test_parses_job_information_from_text(self) -> None:
        parser = PdfParserService()
        text = """
        Zakázka: A-1001
        Zákazník: Jan Novák
        Telefon: +420 603 111 222
        E-mail: jan.novak@example.com
        Ulice: Hlavní 123
        Město: Praha
        PSČ: 110 00
        """

        result = parser.parse_text(text)

        self.assertEqual(result["job_number"], "A-1001")
        self.assertEqual(result["customer_name"], "Jan Novák")
        self.assertEqual(result["phone"], "+420 603 111 222")
        self.assertEqual(result["email"], "jan.novak@example.com")
        self.assertEqual(result["street"], "Hlavní 123")
        self.assertEqual(result["city"], "Praha")
        self.assertEqual(result["zip"], "110 00")
        self.assertTrue(result["should_create_job"])

    def test_parses_noisy_city_and_zip_labels(self) -> None:
        parser = PdfParserService()
        text = """
        Zakázka: B-2002
        Zákazník: Petra Svobodová
        M■sto: Brno
        PS■: 60200
        """

        result = parser.parse_text(text)

        self.assertEqual(result["job_number"], "B-2002")
        self.assertEqual(result["customer_name"], "Petra Svobodová")
        self.assertEqual(result["city"], "Brno")
        self.assertEqual(result["zip"], "60200")

    def test_fallback_extracts_phone_and_email_without_labels(self) -> None:
        parser = PdfParserService()
        text = "Kontakt: +420 777 555 111, servis@firma.cz"

        result = parser.parse_text(text)

        self.assertEqual(result["phone"], "+420 777 555 111")
        self.assertEqual(result["email"], "servis@firma.cz")
        self.assertFalse(result["should_create_job"])

    def test_extracts_supported_czech_phone_formats_near_contact_labels(self) -> None:
        parser = PdfParserService()
        cases = {
            "Telefon: +420 777 123 456": "+420 777 123 456",
            "Tel. +420777123456": "+420 777 123 456",
            "Mobil: 777 123 456": "777 123 456",
            "Telefonní číslo: 777123456": "777 123 456",
        }

        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parser.parse_text(text)["phone"], expected)

    def test_combines_street_with_house_number_from_following_ocr_line(self) -> None:
        parser = PdfParserService()

        for house_number in ("15", "15/2", "15a"):
            with self.subTest(house_number=house_number):
                result = parser.parse_text(f"Ulice: Novákova\n{house_number}\nMěsto: Praha")
                self.assertEqual(result["street"], f"Novákova {house_number}")

    def test_extract_text_from_pdf_joins_all_pages(self) -> None:
        parser = PdfParserService()
        fake_page_1 = MagicMock()
        fake_page_1.extract_text.return_value = "Page 1"
        fake_page_2 = MagicMock()
        fake_page_2.extract_text.return_value = "Page 2"
        fake_reader = MagicMock()
        fake_reader.pages = [fake_page_1, fake_page_2]

        with patch("app.services.pdf_parser_service.PdfReader", return_value=fake_reader):
            text = parser.extract_text_from_pdf("dummy.pdf")

        self.assertEqual(text, "Page 1\nPage 2")

    def test_uses_ocr_when_pdf_text_is_empty(self) -> None:
        parser = PdfParserService()
        fake_page = MagicMock()
        fake_page.extract_text.return_value = ""
        fake_reader = MagicMock()
        fake_reader.pages = [fake_page]
        fake_image_1 = MagicMock()
        fake_image_2 = MagicMock()
        fake_tesseract = MagicMock()
        fake_tesseract.image_to_string.side_effect = ["Prvni strana", "Druha strana"]

        with patch("app.services.pdf_parser_service.PdfReader", return_value=fake_reader), patch(
            "app.services.pdf_parser_service.convert_from_path", return_value=[fake_image_1, fake_image_2]
        ), patch("app.services.pdf_parser_service.pytesseract", fake_tesseract):
            text = parser.extract_text_from_pdf("dummy.pdf")

        self.assertEqual(text, "Prvni strana\nDruha strana")

    def test_parses_special_order_sheet_fields(self) -> None:
        parser = PdfParserService()
        text = """
        Cislo objednavky: OBJ-2026-100
        Datum vytvoreni: 25.07.2026
        Zakaznicke cislo: C-9001
        Jmeno zakaznika: Jan Novak
        Ulice: Hlavni 12
        Mesto: Brno
        Telefon: +420 777 888 999
        ID objednavky: 123456
        Typ objednavky: Montaz
        """

        result = parser.parse_text(text)

        self.assertEqual(result["order_number"], "OBJ-2026-100")
        self.assertEqual(result["creation_date"], "25.07.2026")
        self.assertEqual(result["customer_number"], "C-9001")
        self.assertEqual(result["customer_name"], "Jan Novak")
        self.assertEqual(result["street"], "Hlavni 12")
        self.assertEqual(result["city"], "Brno")
        self.assertEqual(result["phone"], "+420 777 888 999")
        self.assertEqual(result["order_id"], "123456")
        self.assertEqual(result["order_type"], "Montaz")
        self.assertTrue(result["should_create_job"])

    def test_order_sheet_with_missing_fields_requires_review(self) -> None:
        parser = PdfParserService()
        text = """
        Cislo objednavky: OBJ-2026-101
        Datum vytvoreni: 25.07.2026
        Zakaznicke cislo: C-9002
        Jmeno zakaznika: Petra Nova
        Mesto: Ostrava
        Telefon: +420 601 222 333
        ID objednavky: 78910
        Typ objednavky: Servis
        """

        result = parser.parse_text(text)

        self.assertFalse(result["should_create_job"])
        self.assertIn("street", result.get("missing_fields", []))

    def test_parses_packed_order_labels_on_single_line(self) -> None:
        parser = PdfParserService()
        text = """
        Číslo objednávky: 1780283 Vytvoření objednávky: 22.07.2026 Čas příslibu:
        Zákaznické číslo: 1050206268 Typ objednávky: Nestandard
        Jméno a příjmení: Krejčířová Františka ID objednávky: 1-308280003023
        Ulice (název obce): Štolcova Patro / Přípojný bodě.: 1/2
        Město: BRNO-ČERNOVICE Linka 2:
        Kontaktní telefon: 605041013; Františka Krejčířová
        """

        result = parser.parse_text(text)

        self.assertEqual(result["order_number"], "1780283")
        self.assertEqual(result["creation_date"], "22.07.2026")
        self.assertEqual(result["customer_number"], "1050206268")
        self.assertEqual(result["order_type"], "Nestandard")
        self.assertEqual(result["customer_name"], "Krejčířová Františka")
        self.assertEqual(result["order_id"], "1-308280003023")
        self.assertEqual(result["street"], "Štolcova")
        self.assertEqual(result["city"], "BRNO-ČERNOVICE")
        self.assertEqual(result["phone"], "605041013")
        self.assertTrue(result["should_create_job"])

    def test_split_page_with_multiple_order_headers(self) -> None:
        parser = PdfParserService()
        text = """
        Číslo objednávky: 1001
        Jméno a příjmení: Test A
        Číslo objednávky: 1002
        Jméno a příjmení: Test B
        """

        chunks = parser._split_page_into_order_sheets(text)

        self.assertEqual(len(chunks), 2)
        self.assertIn("1001", chunks[0])
        self.assertIn("1002", chunks[1])

    def test_phone_line_can_fill_missing_customer_name(self) -> None:
        parser = PdfParserService()
        text = """
        Zakázka: A-2026-77
        Telefon: 605041013; Františka Krejčířová
        """

        result = parser.parse_text(text)

        self.assertEqual(result["phone"], "605041013")
        self.assertEqual(result["customer_name"], "Františka Krejčířová")
        self.assertTrue(result["should_create_job"])


if __name__ == "__main__":
    unittest.main()
