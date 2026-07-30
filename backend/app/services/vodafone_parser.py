import re
from typing import Dict


class VodafoneParser:
    """Very small, focused parser for Vodafone PDFs.

    Input: page text as a single string.
    Output: dict with exactly four keys: customer_name, address, phone, job_number.
    """

    PHONE_RE = re.compile(r"(?:\+?\d[\d\s/().-]{6,}\d)")
    # prefer common Vodafone Czech labels
    JOB_RE = re.compile(r"\b(?:Zak[aá]zka|Zakazka|Zakázka|id\s*objedn|id\s*objednávky|objednávka)[:\s-]*([0-9A-Za-z\-_/]+)", re.I)
    NAME_LABEL_RE = re.compile(r"(?:Zákazník|Zakaznik|Zákazník:|Zákazník\b|jméno|jmeno|jm[eé]no)[:\s-]*", re.I)
    ADDRESS_LABEL_RE = re.compile(r"(?:Ulice|ulice|Adresa|adresa|M[eě]sto|mesto|Město)[:\s-]*", re.I)

    def build_parsed_payload(self, text: str) -> Dict[str, str | None]:
        normalized = (text or "").replace('\r', '')
        normalized = self.normalize_text(normalized)

        job_number = self.extract_job_number(normalized)
        customer_name = self.extract_customer_name(normalized)
        phone = self.extract_phone(normalized)
        address = self.extract_address(normalized)

        return {
            "customer_name": customer_name or "",
            "address": address or "",
            "phone": phone or "",
            "job_number": job_number or "",
        }

    def normalize_text(self, text: str) -> str:
        """Normalize common OCR mistakes into canonical Vodafone/simple labels.

        Examples:
        - Jménoapiijmeni, Jménoa piijmeni, apiijmeni, pfijmeni -> Jméno a příjmení
        - Kontaktni telefon / kontaktní telefon variants -> Kontaktni telefon
        - ID objednavky / ID objednávky variants -> ID objednavky
        - Ulice (nazev obce) variants -> Ulice (nazev obce)
        - Zakázka / Zakazka -> Zakázka
        - Zákazník / Zakaznik -> Zákazník
        - M■sto / Mesto -> Město
        """
        s = text
        # common OCR garbles for the name label
        s = re.sub(r"Jm[eé]no\s*apiijmeni|Jm[eé]noa\s*piijmeni|apiijmeni|pfijmeni|a\s*pfijmeni|piijmeni",
                   "Jméno a příjmení", s, flags=re.IGNORECASE)
        # normalize Kontaktni telefon label
        s = re.sub(r"kontaktni\s*telefon|kontak.tni\s*telefon|kontaktní\s*telefon",
                   "Kontaktni telefon", s, flags=re.IGNORECASE)
        # normalize ID objednavky label
        s = re.sub(r"id\s*objednavk[yií]|id\s*objednávky",
               "ID objednavky", s, flags=re.IGNORECASE)
        # common OCR variants for 'Číslo objednávky' (Cislo/Cisto/Cislo objedndvky etc.)
        s = re.sub(r"\bCislo\b|\bCisto\b|\bCislo\b", "Číslo", s, flags=re.IGNORECASE)
        s = re.sub(r"Číslo\s*objedn[aá]vky|Cislo\s*objednavky|Cislo\s*objedndvky|Cisto\s*objednavky",
               "Číslo objednávky", s, flags=re.IGNORECASE)
        # normalize Ulice label variants
        s = re.sub(r"ulice\s*\(nazev\s*obce\)|ulice\s*\(název\s*obce\)",
                   "Ulice (nazev obce)", s, flags=re.IGNORECASE)
        # simple labels
        s = re.sub(r"\bZakazka\b|\bZak[aá]zka\b", "Zakázka", s, flags=re.IGNORECASE)
        s = re.sub(r"\bZakaznik\b|\bZ[aá]kazn[ií]k\b", "Zákazník", s, flags=re.IGNORECASE)
        s = re.sub(r"M\W*sto|M[eě]sto|m[eě]sto", "Město", s, flags=re.IGNORECASE)
        # collapse multiple spaces introduced
        s = re.sub(r"\s+", " ", s)
        return s

    def extract_job_number(self, text: str) -> str | None:
        # Only accept explicit label 'Číslo objednávky:' (case-insensitive, ascii variants)
        m = re.search(r"(?:číslo\s*objednávky|cislo\s*objednavky)\s*[:\-]\s*([0-9A-Za-z\-_/]+)", text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    def extract_customer_name(self, text: str) -> str | None:
        # Deterministic: extract content between 'Jméno'/'Jméno a příjmení' label and 'ID objednavky'
        # Match label variants and capture until 'ID objednavky'
        m = re.search(r"(?:jm[eé]no(?:\s*a\s*příjmení)?|jmeno(?:\s*a\s*prijmeni)?|zákazník|zakaznik)[:\s-]*(.+?)\s+(?:id\s*objednavky|čísl[oó]\s*objednávky|číslo\s*objednávky)", text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            val = m.group(1).strip()
            # strip any leading label remnants like 'Jméno a příjmení:' if present
            val = re.sub(r"^(?:Jméno a příjmení[:\s-]*|Jméno[:\s-]*|jmeno[:\s-]*)","", val, flags=re.IGNORECASE)
            return re.sub(r"\s+", " ", val)
        return None

    def extract_phone(self, text: str) -> str | None:
        label = re.search(
            r"(?:kontaktni\s*telefon|telefonní\s*číslo|telefon|tel\.?|mobil)\s*[:\-]?",
            text,
            flags=re.IGNORECASE,
        )
        if not label:
            return None

        phone_match = re.search(
            r"(?<!\d)(?P<phone>(?:\+?420[\s/().-]*)?(?:\d[\s/().-]*){9})(?!\d)",
            text[label.end():label.end() + 80],
        )
        if phone_match:
            raw_phone = phone_match.group("phone").strip()
            digits = re.sub(r"\D", "", raw_phone)
            has_czech_prefix = len(digits) == 12 and digits.startswith("420")
            local_number = digits[-9:]
            grouped = " ".join(local_number[index:index + 3] for index in range(0, 9, 3))
            return f"+420 {grouped}" if has_czech_prefix else grouped
        return None

    def extract_address(self, text: str) -> str | None:
        m = re.search(
            r"ulice\s*\(nazev\s*obce\)\s*[:\-]\s*(.+?)(?=\b(?:patro|město|mesto|kontaktni\s*telefon)\b|$)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if m:
            street_part = m.group(1).strip()
            house_number = re.search(
                r"\b(?:č(?:íslo)?\.?\s*(?:popisné|pop\.?|p\.?)|c(?:islo)?\.?\s*(?:popisne|pop\.?|p\.?))\s*[:\-]?\s*(\d+(?:/\d+)?[A-Za-z]?)",
                street_part,
                flags=re.IGNORECASE,
            )
            if house_number:
                street_name = street_part[:house_number.start()].strip(" ,;:-")
                street_part = f"{street_name} {house_number.group(1)}".strip()
            street_part = re.sub(r"\s+", " ", street_part)
            street_part = re.sub(r"\|$", "", street_part).strip()
            after = text[m.end():m.end()+200]
            city_m = re.search(r"(?:M[eě]sto|M\W*sto|mesto)\s*[:\-]\s*([^\n\r]+)", after, flags=re.IGNORECASE)
            if city_m:
                city = city_m.group(1).strip()
                city = re.sub(r"\s+", " ", city)
                return f"{street_part}, {city}"
            return street_part
        return None
