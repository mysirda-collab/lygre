# Milestone 1 — Montážní ERP (PDF → Customers/Jobs)

Datum: 2026-07-25

## Hlavní změny
- Normalizace datového modelu: přidán entita `Customer`.
- Transformace importního toku: PDF import rozděluje do per-page `Upload` záznamů.
- Job model rozšířen o `customer_id`, `order_number`, `parser_confidence` (nenullable, 0.0–1.0).
- Vazba mezi `Job` a přílohami sjednocena: `Upload.job_id` (1:N) — každý `Upload` ukazuje na `Job`.
- Přidáno `is_primary` boolean do `Upload` a `primary_attachment_id` v `JobDetail` (computed) pro jednoznačné určení primární přílohy.
- Parser garantuje `parser_confidence` v rozsahu 0.0–1.0.
- Automatizovaný integrační test importu 11‑stránkového PDF přidán do backend testů.

## Databázové změny (Alembic)
- `010_create_customers` — vytvoření tabulky `customers` a rozšíření `jobs`.
- `011_unify_attachment_relation` — odstranění sloupce `jobs.attachment_id` a nastavení `jobs.parser_confidence` na NOT NULL (backfill NULL→0.0).
- `012_add_upload_is_primary` — přidání `uploads.is_primary` boolean (default false).

## Nové endpointy / schema změny
- `POST /api/v1/customers` — vytvoření zákazníka.
- `GET /api/v1/jobs/{job_id}/detail` — vrací `JobDetailResponse` obsahující:
  - `job`: `JobRead`
  - `attachments`: pole `JobAttachmentRead` (obsahuje `is_primary`)
  - `primary_attachment_id`: id `Upload` označeného jako `is_primary`, nebo `null`

## Breaking changes
- Odebrán/sloučen sloupec `jobs.attachment_id`. Pokud frontend nebo integrace očekávaly přímé `attachment_id` v `JobRead`, musí číst `primary_attachment_id` nebo `attachments` a vybrat příslušnou přílohu podle `is_primary`.
- `parser_confidence` je nyní vždy nenulové (default 0.0) — migrace backfilluje existující NULL hodnoty.

## Migrace
- Po nasazení spusťte `alembic upgrade head` (CI / entrypoint to provádí automaticky v tomto repu).
- Migrace `011` provádí backfill: `UPDATE jobs SET parser_confidence = 0.0 WHERE parser_confidence IS NULL`.

## Známá omezení
- Parser zatím nemusí z syntetických PDF spolehlivě extrahovat `customer_number` nebo `phone`; proto některé Jobs budou vytvořeny bez `customer_id` a s `parser_confidence = 0.0`.
- Několik deprekačních warnings (FastAPI `on_event`, Pydantic class Config) existuje v projektu; nejsou kritické, ale doporučený refaktor v Milestone 2.

## Doporučení pro Milestone 2
- Vylepšit parser tak, aby testní PDF obsahovalo jasně parsovatelný `customer_number` a `parser_confidence` > 0.7 pro E2E scénáře.
- Přidat API pro nastavení `is_primary` (markovat primární přílohu) a endpoint pro upload/attach více příloh k existujícím Jobům.
- Refaktor `app/main.py` na FastAPI lifespan handlers a aktualizace Pydantic `ConfigDict` pro snížení varování.
- Přidat CI job spouštějící docker-compose pro smoke testy (migrace + zdraví služeb + základní API flow).

---

Milestone 1: připraveno k nasazení.
