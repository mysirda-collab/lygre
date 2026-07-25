import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader


class PdfParserService:
    def extract_text_from_pdf(self, file_path: str | Path) -> str:
        reader = PdfReader(str(file_path))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text:
                pages.append(text)
        return "\n".join(pages).strip()

    def parse_text(self, text: str) -> dict[str, Any]:
        normalized_lines = [re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines() if re.sub(r"\s+", " ", line).strip()]

        values: dict[str, str] = {}
        for index, line in enumerate(normalized_lines):
            lowered = line.lower()
            if re.search(r"(?:^|\s)(zakázka|job|objednávka|číslo zakázky)", lowered):
                values["job_number"] = self._extract_value(line, index, normalized_lines)
            elif re.search(r"(?:^|\s)(zákazník|jméno zákazníka|customer|name)", lowered):
                values["customer_name"] = self._extract_value(line, index, normalized_lines)
            elif re.search(r"(?:^|\s)(telefon|phone|tel)", lowered):
                values["phone"] = self._extract_value(line, index, normalized_lines)
            elif re.search(r"(?:^|\s)(e-mail|email|mail)", lowered):
                values["email"] = self._extract_value(line, index, normalized_lines)
            elif re.search(r"(?:^|\s)(ulice|street|adresa)", lowered):
                values["street"] = self._extract_value(line, index, normalized_lines)
            elif re.search(r"(?:^|\s)(město|m.sto|city|obec)", lowered):
                values["city"] = self._extract_value(line, index, normalized_lines)
            elif re.search(r"(?:^|\s)(psč|ps.|psc|zip|postal)", lowered):
                values["zip"] = self._extract_value(line, index, normalized_lines)

        full_text = "\n".join(normalized_lines)
        if "email" not in values:
            email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", full_text)
            if email_match:
                values["email"] = email_match.group(0)
        if "phone" not in values:
            phone_match = re.search(r"(?:\+\d{1,3}\s?)?(?:\d[\s-]?){7,}", full_text)
            if phone_match:
                values["phone"] = phone_match.group(0)
        if "zip" not in values:
            zip_match = re.search(r"\b\d{3}\s?\d{2}\b", full_text)
            if zip_match:
                values["zip"] = zip_match.group(0)

        cleaned = {key: self._clean_value(value) for key, value in values.items() if self._clean_value(value)}
        cleaned["should_create_job"] = bool(cleaned.get("job_number") or cleaned.get("customer_name"))
        return cleaned

    def _extract_value(self, line: str, index: int, lines: list[str]) -> str:
        if ":" in line:
            _, value = line.split(":", 1)
            return value.strip()
        if index + 1 < len(lines):
            return lines[index + 1].strip()
        return ""

    def _clean_value(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = re.sub(r"\s+", " ", value).strip(" -:;,")
        return cleaned or None

    def build_parsed_payload(self, text: str) -> dict[str, Any]:
        parsed = self.parse_text(text)
        return {
            "extracted_text": text,
            "parsed_data": parsed,
            "should_create_job": parsed.get("should_create_job", False),
            "job_number": parsed.get("job_number"),
            "customer_name": parsed.get("customer_name"),
            "phone": parsed.get("phone"),
            "email": parsed.get("email"),
            "street": parsed.get("street"),
            "city": parsed.get("city"),
            "zip": parsed.get("zip"),
        }
