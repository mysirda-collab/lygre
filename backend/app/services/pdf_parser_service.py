from dataclasses import dataclass
from io import BytesIO
import re
from pathlib import Path
from typing import Any, Callable

try:
    from pdf2image import convert_from_bytes, convert_from_path
except Exception:
    convert_from_bytes = None
    convert_from_path = None

try:
    import pytesseract
except Exception:
    pytesseract = None

from pypdf import PdfReader
from pypdf import PdfWriter
import numpy as np
try:
    import cv2
except Exception:
    cv2 = None


@dataclass
class OrderSheetCandidate:
    page_number: int
    sheet_index: int
    text: str
    page_pdf_bytes: bytes


class PdfParserService:
    MIN_TEXT_LAYER_CHARACTERS = 80

    def _text_layer_is_sufficient(self, text: str) -> bool:
        return len(re.sub(r"\s+", "", text or "")) >= self.MIN_TEXT_LAYER_CHARACTERS

    def extract_order_sheet_candidates(self, pdf_bytes: bytes) -> list[OrderSheetCandidate]:
        if not pdf_bytes:
            return []

        try:
            reader = PdfReader(BytesIO(pdf_bytes))
        except Exception:
            return [OrderSheetCandidate(page_number=1, sheet_index=1, text="", page_pdf_bytes=pdf_bytes)]

        candidates: list[OrderSheetCandidate] = []
        for page_index, page in enumerate(reader.pages, start=1):
            page_pdf_bytes = self._build_single_page_pdf_bytes(page)
            page_text = (page.extract_text() or "").strip()

            if not self._text_layer_is_sufficient(page_text):
                ocr_text = self._extract_page_text_with_ocr(page_pdf_bytes, page_index)
                if self._text_layer_is_sufficient(ocr_text) or not page_text:
                    page_text = ocr_text

            # Try to extract QR job number from the single-page PDF bytes.
            # If found and is a 7-digit number, prepend a canonical label so
            # existing regex parser will pick it up as job_number.
            try:
                qr_job = self._extract_qr_job_number(page_pdf_bytes)
                if qr_job:
                    page_text = f"Číslo objednávky: {qr_job}\n" + (page_text or "")
            except Exception:
                pass

            sheet_texts = self._split_page_into_order_sheets(page_text)
            if not sheet_texts:
                sheet_texts = [page_text.strip()]
            if not sheet_texts:
                sheet_texts = [""]

            for sheet_index, sheet_text in enumerate(sheet_texts, start=1):
                candidates.append(
                    OrderSheetCandidate(
                        page_number=page_index,
                        sheet_index=sheet_index,
                        text=sheet_text.strip(),
                        page_pdf_bytes=page_pdf_bytes,
                    )
                )

        return candidates

    def extract_text_from_pdf(
        self,
        file_path: str | Path,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> str:
        file_path_str = str(file_path)
        if progress_callback:
            progress_callback(10, "Načítám PDF dokument")
        reader = PdfReader(file_path_str)
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text:
                pages.append(text)
        extracted = "\n".join(pages).strip()
        if self._text_layer_is_sufficient(extracted):
            return extracted
        ocr_text = self._extract_text_with_ocr(file_path_str, progress_callback=progress_callback)
        return ocr_text or extracted

    def _build_single_page_pdf_bytes(self, page: Any) -> bytes:
        writer = PdfWriter()
        writer.add_page(page)
        output = BytesIO()
        writer.write(output)
        return output.getvalue()

    def _extract_page_text_with_ocr(self, pdf_bytes: bytes, page_number: int) -> str:
        if convert_from_bytes is None or pytesseract is None:
            return ""
        try:
            # pdf_bytes is expected to be a single-page PDF when called from
            # _build_single_page_pdf_bytes(). In that case convert_from_bytes
            # must be invoked with first_page=1, last_page=1. Passing the
            # original page_number (absolute in the source PDF) here caused
            # convert_from_bytes to return no images for many pages.
            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)
        except Exception:
            return ""
        if not images:
            return ""

        image = self._prepare_image_for_ocr(images[0])
        try:
            text = pytesseract.image_to_string(image, lang="ces+eng")
        except Exception:
            return ""
        return text.strip()

    def _prepare_image_for_ocr(self, image: Any) -> Any:
        width, height = image.size
        margin_x = max(8, int(width * 0.02))
        margin_y = max(8, int(height * 0.02))
        if width > margin_x * 2 and height > margin_y * 2:
            image = image.crop((margin_x, margin_y, width - margin_x, height - margin_y))

        if pytesseract is not None:
            try:
                osd = pytesseract.image_to_osd(image, output_type="string")
                match = re.search(r"Rotate:\s*(\d+)", osd)
                if match:
                    rotation = int(match.group(1)) % 360
                    if rotation in {90, 180, 270}:
                        image = image.rotate(360 - rotation, expand=True)
            except Exception:
                pass

        try:
            return image.convert("L")
        except Exception:
            return image

    def _split_page_into_order_sheets(self, text: str) -> list[str]:
        normalized = (text or "").strip()
        if not normalized:
            return []

        markers = list(re.finditer(r"(?:číslo\s*objednávky|cislo\s*objednavky)\s*[:\-]", normalized, flags=re.IGNORECASE))
        if len(markers) <= 1:
            return [normalized]

        chunks: list[str] = []
        for index, marker in enumerate(markers):
            start = marker.start()
            end = markers[index + 1].start() if index + 1 < len(markers) else len(normalized)
            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)
        return chunks or [normalized]

    def _extract_text_with_ocr(
        self,
        file_path: str,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> str:
        if convert_from_path is None or pytesseract is None:
            return ""

        try:
            images = convert_from_path(file_path)
        except Exception:
            return ""

        pages: list[str] = []
        total_pages = max(len(images), 1)
        for index, image in enumerate(images, start=1):
            if progress_callback:
                progress = 20 + int(((index - 1) / total_pages) * 30)
                progress_callback(progress, f"Provádím OCR stránky {index}/{total_pages}")
            try:
                text = pytesseract.image_to_string(image, lang="ces+eng")
            except Exception:
                text = ""
            normalized = re.sub(r"\s+", " ", text).strip()
            if normalized:
                pages.append(text.strip())
            if progress_callback:
                progress = 20 + int((index / total_pages) * 30)
                progress_callback(min(progress, 50), f"OCR stránky {index}/{total_pages} dokončeno")
        return "\n".join(pages).strip()

    def _extract_qr_job_number(self, page_pdf_bytes: bytes) -> str | None:
        """Decode QR from single-page PDF bytes and return 7-digit job number if present."""
        if cv2 is None:
            return None
        try:
            images = convert_from_bytes(page_pdf_bytes, first_page=1, last_page=1)
            if not images:
                return None
            img = images[0]
            arr = np.array(img.convert('RGB'))
            img_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            detector = cv2.QRCodeDetector()
            data, pts, _ = detector.detectAndDecode(img_cv)
            if not data:
                return None
            # find a 7-digit number in data
            m = re.search(r"\b(\d{7})\b", data)
            if m:
                return m.group(1)
        except Exception:
            return None
        return None

    def parse_text(self, text: str) -> dict[str, Any]:
        normalized_lines = [re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines() if re.sub(r"\s+", " ", line).strip()]
        full_text = "\n".join(normalized_lines)

        debug_run = False
        if "hrubes" in full_text.lower():
            debug_run = True
            print("--- PDF PARSE DEBUG START (trigger: 'hrubes') ---")
            print("full_text:\n", full_text)

        order_form_detected = self._is_order_form(full_text)
        order_form = self._parse_order_form_text(full_text) if order_form_detected else {}

        values: dict[str, str] = {}
        for index, line in enumerate(normalized_lines):
            lowered = line.lower()
            if debug_run:
                print(f"\n[LINE {index}] '{line}'")
            # accept both diacritic and ascii variants, and common merged tokens
            if re.search(r"(?:^|\s)(zakázka|job|objednávka|číslo\s*zakázky|cislo\s*objednavky|číslo\s*objednávky)", lowered):
                if "job_number" not in values:
                    if debug_run:
                        print("  matched regex for job_number")
                    extracted = self._extract_value(line, index, normalized_lines)
                    if debug_run:
                        print("  _extract_value returned:", repr(extracted))
                    values["job_number"] = extracted
            elif re.search(r"(?:^|\s)(zákazník|jméno\s*zákazníka|jménoa\b|jmenoa\b|jménoa\s*prijmeni|jmeno\s*a\s*prijmeni|jmenoa\s*prijmeni|customer|name)", lowered):
                if "customer_name" not in values:
                    if debug_run:
                        print("  matched regex for customer_name (line-based)")
                    extracted = self._extract_value(line, index, normalized_lines)
                    if debug_run:
                        print("  _extract_value returned:", repr(extracted))
                        print("  setting customer_name first time")
                    values["customer_name"] = extracted
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

        if debug_run:
            print("\n-- order_form detected values before merge:", order_form)
        for key, value in order_form.items():
            cleaned_value = self._clean_value(value)
            # prefer existing line-based parsed values; only fill missing
            if debug_run and cleaned_value:
                print(f"  order_form provides {key}: {repr(cleaned_value)}")
            if cleaned_value and not cleaned.get(key):
                if debug_run:
                    print(f"  merging {key} into cleaned (was missing)")
                cleaned[key] = cleaned_value

        if debug_run:
            if 'customer_name' in cleaned:
                print(f"\n[DEBUG] customer_name in cleaned BEFORE phone/name split: {repr(cleaned.get('customer_name'))}")

        phone_name = self._split_phone_and_name(cleaned.get("phone"))
        if phone_name[0]:
            cleaned["phone"] = phone_name[0]
        if phone_name[1] and not cleaned.get("customer_name"):
            cleaned["customer_name"] = phone_name[1]

        if "job_number" not in cleaned:
            cleaned["job_number"] = cleaned.get("order_number") or cleaned.get("order_id")
        if "customer_name" not in cleaned:
            cleaned["customer_name"] = cleaned.get("customer_name")

        if debug_run:
            print(f"\n[DEBUG FINAL] cleaned customer_name: {repr(cleaned.get('customer_name'))}")
            print("--- PDF PARSE DEBUG END ---")

        required_order_fields = [
            "order_number",
            "creation_date",
            "customer_number",
            "customer_name",
            "street",
            "city",
            "phone",
            "order_id",
            "order_type",
        ]

        if order_form_detected:
            missing_fields = [field for field in required_order_fields if not cleaned.get(field)]
            cleaned["missing_fields"] = missing_fields
            # For detected order forms require all required order fields to be
            # present to consider automatic job creation. Do not allow a
            # shortcut based on only job_number+customer_name since order
            # forms must be complete for reliable creation.
            cleaned["should_create_job"] = (len(missing_fields) == 0)
        else:
            cleaned["should_create_job"] = bool(cleaned.get("job_number") and cleaned.get("customer_name"))
        # extract notes block heuristically
        notes_match = re.search(r"(instrukc[eí]|poznámk|poznámka|informace pro technika|popis závad|popis zavady)(?:[:\-\s]+)(.+)$", full_text, flags=re.IGNORECASE | re.DOTALL)
        if notes_match:
            notes = re.sub(r"\s+", " ", notes_match.group(2)).strip()
            if notes:
                cleaned["notes"] = notes

        # split customer_name into first/last when possible
        if cleaned.get("customer_name") and ("first_name" not in cleaned or "last_name" not in cleaned):
            parts = cleaned["customer_name"].split()
            if len(parts) >= 2:
                cleaned["first_name"] = parts[0]
                cleaned["last_name"] = " ".join(parts[1:])
            else:
                cleaned["first_name"] = cleaned["customer_name"]
                cleaned["last_name"] = None

        # build combined address
        if cleaned.get("street") and cleaned.get("city") and not cleaned.get("address"):
            addr = f"{cleaned.get('street')}, {cleaned.get('city')}"
            cleaned["address"] = addr

        # normalize street value globally to remove OCR noise
        if cleaned.get("street"):
            cleaned["street"] = self._normalize_street(cleaned.get("street"))
        # normalize city to remove trailing tokens like 'Linka 2' or similar noise
        if cleaned.get("city"):
            city = cleaned.get("city")
            city = re.split(r"\bLinka\b|/|:|;|,|\.|\\n", city, flags=re.IGNORECASE)[0].strip()
            cleaned["city"] = city

        return cleaned

    def _parse_order_form_text(self, full_text: str) -> dict[str, str]:
        data = {
            "order_number": self._extract_by_patterns(
                full_text,
                [
                    r"číslo\s*objednávky\s*[:\-]?\s*(.+?)(?=\s+(?:vytvoření\s*objednávky|datum\s*vytvoření|čas\s*příslibu|informace\s*o\s*uživateli)\b|$)",
                    r"cislo\s*objednavky\s*[:\-]?\s*(.+?)(?=\s+(?:vytvoreni\s*objednavky|datum\s*vytvoreni|cas\s*prislibu|informace\s*o\s*uzivateli)\b|$)",
                ],
            ),
            "creation_date": self._extract_by_patterns(
                full_text,
                [
                    r"(?:datum\s*vytvoření|vytvoření\s*objednávky)\s*[:\-]?\s*(.+?)(?=\s+(?:čas\s*příslibu|informace\s*o\s*uživateli|zákaznické\s*číslo)\b|$)",
                    r"(?:datum\s*vytvoreni|vytvoreni\s*objednavky)\s*[:\-]?\s*(.+?)(?=\s+(?:cas\s*prislibu|informace\s*o\s*uzivateli|zakaznicke\s*cislo)\b|$)",
                ],
            ),
            "customer_number": self._extract_by_patterns(
                full_text,
                [
                    r"zákaznické\s*číslo\s*[:\-]?\s*(.+?)(?=\s+(?:typ\s*objednávky|jméno\s*a\s*příjmení|jméno\s*zákazníka|id\s*objednávky|ulice)\b|$)",
                    r"zakaznicke\s*cislo\s*[:\-]?\s*(.+?)(?=\s+(?:typ\s*objednavky|jmeno\s*a\s*prijmeni|jmeno\s*zakaznika|id\s*objednavky|ulice)\b|$)",
                    r"zakaznick\w*\s*(?:č[ií]slo|cislo|lo)?\s*[:\-]?\s*(\d{6,})(?=\s+(?:typ\s*objedn|jméno|jmeno|id\s*objedn)|$)",
                ],
            ),
            "customer_name": self._extract_by_patterns(
                full_text,
                [
                    r"jméno\s*a\s*příjmení\s*[:\-]?\s*(.+?)(?=\s+(?:objednavky|id\s*objednávky|id\s*objednavky|číslo\s*objednávky|cislo\s*objednavky|kontaktní\s*telefon|kontaktni\s*telefon|ulice|město|mesto|asistovaná\s*instalace|\b[iI]\)|\b\d+D)\b|$)",
                    r"jmeno\s*a\s*prijmeni\s*[:\-]?\s*(.+?)(?=\s+(?:objednavky|id\s*objednavky|id\s*objednávky|cislo\s*objednavky|číslo\s*objednávky|kontaktni\s*telefon|kontaktní\s*telefon|ulice|mesto|město|asistovana\s*instalace|\b[iI]\)|\b\d+D)\b|$)",
                    # OCR sometimes merges tokens: e.g. 'Jménoapiijmeni: Name Surname'
                    r"jméno\W*apiijmeni\s*[:\-]?\s*(.+?)(?=\s+(?:id\s*objednavky|id\s*objednávky|číslo\s*objednávky|cislo\s*objednavky|kontaktní\s*telefon|kontaktni\s*telefon|ulice|město|mesto|asistovaná\s*instalace)\b|$)",
                    r"jmeno\W*apiijmeni\s*[:\-]?\s*(.+?)(?=\s+(?:id\s*objednavky|id\s*objednávky|cislo\s*objednavky|číslo\s*objednávky|kontaktni\s*telefon|kontaktní\s*telefon|ulice|mesto|město|asistovana\s*instalace)\b|$)",
                    # capture name when followed by ASCII 'ID objednavky' marker
                    r"jméno\W*apiijmeni\s*[:\-]?\s*(.+?)(?=\s+(?:objednavky|id\s*objednavky|id\s*objednávky|číslo\s*objednávky|cislo\s*objednavky|kontaktní\s*telefon|kontaktni\s*telefon|ulice|město|mesto|asistovaná\s*instalace|\b[iI]\)|\b\d+D)\b|$)",
                    r"jmeno\W*apiijmeni\s*[:\-]?\s*(.+?)(?=\s+(?:objednavky|id\s*objednavky|id\s*objednávky|číslo\s*objednávky|cislo\s*objednavky|kontaktni\s*telefon|kontaktní\s*telefon|ulice|mesto|město|asistovana\s*instalace|\b[iI]\)|\b\d+D)\b|$)",
                    # common OCR garbles seen in real PDFs
                    r"jméno\s*a\s*pfijmeni\s*[:\-]?\s*(.+?)(?=\s+(?:objednavky|id\s*objednavky|id\s*objednávky|číslo\s*objednávky|cislo\s*objednavky|kontaktní\s*telefon|kontaktni\s*telefon|ulice|město|mesto|asistovaná\s*instalace|\b[iI]\)|\b\d+D)\b|$)",
                    r"jmeno\s*a\s*piijmeni\s*[:\-]?\s*(.+?)(?=\s+(?:objednavky|id\s*objednavky|id\s*objednávky|číslo\s*objednávky|cislo\s*objednavky|kontaktni\s*telefon|kontaktní\s*telefon|ulice|mesto|město|asistovana\s*instalace|\b[iI]\)|\b\d+D)\b|$)",
                    # handle leading underscore/misc between name and 'objednavky'
                    r"jméno\s*a\s*piijmeni\s*[:\-]?\s*[_\s]*(.+?)(?=\s+\d*\s*objednavky\b|\s+objednavky\b|$)",
                    r"jméno\s*zákazníka\s*[:\-]?\s*(.+?)(?=\s+id\s*objednávky\b|\s+asistovaná\s*instalace\b|\s+typ\s*objednávky\b|$)",
                    r"jmeno\s*zakaznika\s*[:\-]?\s*(.+?)(?=\s+id\s*objednavky\b|\s+asistovana\s*instalace\b|\s+typ\s*objednavky\b|\s+ulice\b|\s+mesto\b|\s+telefon\b|$)",
                    r"(?:^|\n)zákazník\s*[:\-]?\s*(.+?)(?=\s+id\s*objednávky\b|\s+asistovaná\s*instalace\b|$)",
                    r"(?:^|\n)zakaznik\s*[:\-]?\s*(.+?)(?=\s+id\s*objednavky\b|\s+asistovana\s*instalace\b|$)",
                ],
            ),
            "street": self._extract_by_patterns(
                full_text,
                [
                    r"ulice(?:\s*\(název\s*obce\))?\s*[:\-]?\s*(.+?)(?=\s+(?:patro|č\.?\s*pop|cpop|město|mesto|linka)\b|$)",
                    r"ulice(?:\s*\(nazev\s*obce\))?\s*[:\-]?\s*(.+?)(?=\s+(?:patro|c\.?\s*pop|cpop|mesto|linka)\b|$)",
                    r"adresa\s*[:\-]?\s*(.+?)(?=\s+(?:patro|č\.?\s*pop|cpop|město|mesto|linka)\b|$)",
                ],
            ),
            "city": self._extract_by_patterns(
                full_text,
                [
                    r"město\s*[:\-]?\s*(.+?)(?=\s+(?:linka|kontaktní\s*telefon|telefon|instrukce|informace\s*o\s*službách)\b|$)",
                    r"mesto\s*[:\-]?\s*(.+?)(?=\s+(?:linka|kontaktni\s*telefon|telefon|instrukce|informace\s*o\s*sluzbach)\b|$)",
                ],
            ),
            "phone": self._extract_by_patterns(
                full_text,
                [
                    r"kontaktní\s*telefon\s*[:\-]?\s*(.+?)(?=\s+(?:instrukce|jméno\s*zákazníka|asistovaná\s*instalace|id\s*objednávky|id\s*objednavky|typ\s*objednávky|typ\s*objednavky|informace\s*o\s*službách)\b|$)",
                    r"kontaktni\s*telefon\s*[:\-]?\s*(.+?)(?=\s+(?:instrukce|jmeno\s*zakaznika|asistovana\s*instalace|id\s*objednavky|typ\s*objednavky|informace\s*o\s*sluzbach)\b|$)",
                    r"telefon\s*[:\-]?\s*(.+?)(?=\s+(?:instrukce|jméno\s*zákazníka|asistovaná\s*instalace|id\s*objednávky|id\s*objednavky|typ\s*objednávky|typ\s*objednavky|informace\s*o\s*službách)\b|$)",
                    r"tel\.?\s*[:\-]?\s*(.+?)(?=\s+(?:instrukce|jmeno\s*zakaznika|asistovana\s*instalace|id\s*objednavky|typ\s*objednavky|informace\s*o\s*sluzbach)\b|$)",
                ],
            ),
            "order_id": self._extract_by_patterns(
                full_text,
                [
                    r"id\s*objednávky\s*[:\-]?\s*(.+?)(?=\s+(?:ulice|patro|č\.?\s*pop|město|mesto|linka)\b|$)",
                    r"id\s*objednavky\s*[:\-]?\s*(.+?)(?=\s+(?:ulice|patro|c\.?\s*pop|mesto|linka|typ\s*objednavky)\b|$)",
                ],
            ),
            "order_type": self._extract_by_patterns(
                full_text,
                [
                    r"typ\s*objednávky\s*[:\-]?\s*(.+?)(?=\n|\s+(?:jméno|id\s*objednávky|ulice)\b|$)",
                    r"typ\s*objednavky\s*[:\-]?\s*(.+?)(?=\n|\s+(?:jmeno|id\s*objednavky|ulice)\b|$)",
                ],
            ),
        }
        # normalize street when OCR returns packed values like 'Štolcova Patro / Přípojný bodě.: 1/2'
        if data.get("street"):
            data["street"] = self._normalize_street(data["street"])
        return data

    def _normalize_street(self, street: str) -> str:
        if not street:
            return street
        s = street
        # cut at common noise markers from OCR/PDF merges
        s = re.split(r"\bPatro\b|/|:|;|,|\.|\(|\\n", s, flags=re.IGNORECASE)[0]
        s = s.strip()
        # if contains more than two words, prefer first two (street name + optional number)
        parts = s.split()
        if len(parts) > 2:
            # keep the first token which is typically the street name in these samples
            return parts[0]
        return s

    def _extract_by_patterns(self, full_text: str, patterns: list[str]) -> str:
        for pattern in patterns:
            match = re.search(pattern, full_text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return ""

    def _is_order_form(self, full_text: str) -> bool:
        normalized = full_text.lower()
        markers = ["číslo objednávky", "datum vytvoření", "zákaznické číslo", "id objednávky", "typ objednávky"]
        hits = sum(1 for marker in markers if marker in normalized)
        if hits >= 2:
            return True
        ascii_markers = ["cislo objednavky", "datum vytvoreni", "zakaznicke cislo", "id objednavky", "typ objednavky"]
        hits_ascii = sum(1 for marker in ascii_markers if marker in normalized)
        if hits_ascii >= 2:
            return True
        # tolerate heavily corrupted OCR: if common order-form anchors appear
        # e.g. 'jméno' together with 'objedn' or 'zakaz', treat as order form
        if ("jméno" in normalized or "jmeno" in normalized or "jm" in normalized) and (
            "objedn" in normalized or "zakaz" in normalized
        ):
            return True
        return False

    def _extract_value(self, line: str, index: int, lines: list[str]) -> str:
        if ":" in line:
            _, value = line.split(":", 1)
            # OCR/PDF extraction can merge multiple labeled fields into one line.
            # Keep only the value before the next known label.
            next_label_patterns = [
                r"\bzakázka\s*[:\-]",
                r"\bobjednávka\s*[:\-]",
                r"\bid\s*objednávky\s*[:\-]",
                r"\bid\s*objednavky\s*[:\-]",
                r"\btyp\s*objednávky\s*[:\-]",
                r"\btyp\s*objednavky\s*[:\-]",
                r"\bčíslo\s*zakázky\s*[:\-]",
                r"\bzákazník\s*[:\-]",
                r"\bjméno\s*zákazníka\s*[:\-]",
                r"\bcustomer\s*[:\-]",
                r"\bname\s*[:\-]",
                r"\btelefon\s*[:\-]",
                r"\bphone\s*[:\-]",
                r"\btel\.?\s*[:\-]",
                r"\be-mail\s*[:\-]",
                r"\bemail\s*[:\-]",
                r"\bmail\s*[:\-]",
                r"\bulice\s*[:\-]",
                r"\bstreet\s*[:\-]",
                r"\badresa\s*[:\-]",
                r"\bměsto\s*[:\-]",
                r"\bm\.?sto\s*[:\-]",
                r"\bcity\s*[:\-]",
                r"\bpsč\s*[:\-]",
                r"\bps\.?\s*[:\-]",
                r"\bpsc\s*[:\-]",
                r"\bzip\s*[:\-]",
                # common following labels present in Vodafone PDFs (ascii/diacritics)
                r"vytvo[řr]ení\s*objednávky", r"vytvoreni\s*objednavky", r"cas\s*p[řr]islibu", r"cas\s*prislibu",
            ]
            cut_at = len(value)
            for pattern in next_label_patterns:
                match = re.search(pattern, value, flags=re.IGNORECASE)
                if match and match.start() < cut_at:
                    cut_at = match.start()
            return value[:cut_at].strip()
        if index + 1 < len(lines):
            return lines[index + 1].strip()
        return ""

    def _clean_value(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = re.sub(r"\s+", " ", value).strip(" -:;,")
        return cleaned or None

    def _split_phone_and_name(self, value: str | None) -> tuple[str | None, str | None]:
        if not value:
            return None, None
        raw = value.strip()
        if not raw:
            return None, None

        parts = [part.strip() for part in re.split(r"[;,]\s*", raw) if part.strip()]
        for part in parts:
            if re.fullmatch(r"(?:\+?\d[\d\s()\-]{6,}\d)", part):
                name = next((candidate for candidate in parts if candidate != part and re.search(r"[A-Za-zÁ-ž]", candidate)), None)
                return re.sub(r"\s+", " ", part).strip(), name

        match = re.search(r"(?:\+?\d[\d\s()\-]{6,}\d)", raw)
        if not match:
            return raw, None
        phone = re.sub(r"\s+", " ", match.group(0)).strip(" ;,")
        tail = raw[match.end():].strip(" ;,")
        name = tail if tail and re.search(r"[A-Za-zÁ-ž]", tail) else None
        return phone or None, name

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
            "order_number": parsed.get("order_number"),
            "creation_date": parsed.get("creation_date"),
            "customer_number": parsed.get("customer_number"),
            "order_id": parsed.get("order_id"),
            "order_type": parsed.get("order_type"),
            "missing_fields": parsed.get("missing_fields", []),
        }
