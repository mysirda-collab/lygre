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


if __name__ == "__main__":
    unittest.main()
