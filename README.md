# Lygre

Lygre je informační systém pro správu zakázek montážní firmy.

## Co je nyní implementováno

- FastAPI backend (zakázky, upload PDF, review workflow)
- JWT autentizace (access + refresh token)
- Autorizace podle rolí (admin, manager, worker)
- Seed výchozího admin účtu při prvním startu
- SQLAlchemy 2.0 modely a CRUD vrstva
- Alembic migrace pro schéma jobs/uploads/auth + Sprint 2 indexy + Sprint 3 kalendář
- Automatické vytěžení textových PDF přes pypdf
- OCR fallback pro skenovaná PDF (pdf2image + Tesseract přes pytesseract, jazyky `ces+eng`)
- Next.js frontend (dashboard, seznam zakázek, detail, import PDF, ruční korekce)
- Docker Compose orchestrace (db + backend + frontend)

### Sprint 2: Funkční správa zakázek

- Dashboard metriky:
  - počty zakázek podle stavu,
  - poslední vytvořené zakázky,
  - zakázky po termínu,
  - dnešní montáže.
- Seznam zakázek:
  - server-side stránkování,
  - server-side řazení,
  - fulltext vyhledávání,
  - filtry podle stavu, priority, technika, klienta a data (od/do).
- Detail zakázky:
  - kompletní informace,
  - audit historie změn,
  - přílohy.
- Editace zakázky:
  - stav,
  - priorita,
  - technik,
  - termín,
  - poznámky.
- Frontend UX:
  - loading skeletony,
  - toast notifikace,
  - potvrzení mazání,
  - error boundary,
  - prázdné stavy.

### Sprint 3: Plánování montáží a kalendář techniků

- Backend kalendář:
  - model `calendar_events` (montáž, servis, kontrola),
  - vazba na zakázku (`job_id`) a technika (`technician_id`),
  - CRUD API (`/api/v1/calendar/events`),
  - detekce kolizí termínů na technika,
  - filtrace dle data a technika,
  - audit změn (`create`, `update`, `reschedule`, `delete`).
- Frontend kalendář:
  - FullCalendar (`month`, `week`, `day`),
  - drag & drop přesun termínu,
  - resize událostí,
  - kliknutí na událost otevírá detail zakázky,
  - vytváření události přímo z kalendáře,
  - barevné rozlišení podle stavu zakázky,
  - filtr techniků.
- UX:
  - loading skeletony,
  - toast notifikace,
  - error boundary,
  - prázdné stavy.

## Jak spustit

```bash
docker compose up --build
```

Backend při startu automaticky aplikuje migrace (`alembic upgrade head`).

Výchozí přihlašovací údaje po čistém startu:
- Email: `admin@lygre.local`
- Heslo: `Admin123!`

Po spuštění budou dostupné:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/docs

Volitelné prostředí pro frontend:
- `NEXT_SERVER_API_URL` (server-side proxy target pro `/api/*`, např. `http://backend:8000` v Dockeru)
- `NEXT_PUBLIC_API_BASE_URL` (volitelně veřejná API URL; pokud není nastavena, frontend používá same-origin cesty)

### API konfigurace bez změn zdrojového kódu

Frontend je nastaven tak, aby fungoval napříč prostředími bez úprav kódu:

- Výchozí režim (doporučený):
  - klient volá relativní cesty (`/api/v1/...`),
  - Next.js proxy (`rewrites`) přesměruje `/api/*` na backend podle `NEXT_SERVER_API_URL`.
- Docker / Codespaces:
  - v `docker-compose.yml` je `NEXT_SERVER_API_URL=http://backend:8000`.
- Proxmox:
  - ponechte stejný princip (frontend proxy na interní backend URL),
  - není potřeba měnit frontend kód, pouze environment konfiguraci.
- Externí API doména (volitelné):
  - nastavte `NEXT_PUBLIC_API_BASE_URL` na veřejnou URL backendu.

Volitelné prostředí pro backend:
- `JWT_SECRET_KEY`
- `ACCESS_TOKEN_EXPIRES_MINUTES`
- `REFRESH_TOKEN_EXPIRES_DAYS`
- `SEED_ADMIN_EMAIL`
- `SEED_ADMIN_NAME`
- `SEED_ADMIN_PASSWORD`

## OCR pipeline pro PDF import

Import PDF nyní používá dvoukrokové vytěžení textu:

1. Nejprve se zkusí extrakce textu přes `pypdf`.
2. Pokud je výsledek prázdný (typicky sken), automaticky se spustí OCR přes `pdf2image` + `pytesseract`.
3. OCR běží nad všemi stránkami a výsledný text se skládá do jednoho dokumentu.

Speciální parser pro zakázkové listy extrahuje tato pole:
- číslo objednávky,
- datum vytvoření,
- zákaznické číslo,
- jméno zákazníka,
- ulici,
- město,
- telefon,
- ID objednávky,
- typ objednávky.

Pokud OCR selže nebo chybí povinná pole, dokument se neztratí: vznikne dohledatelný upload, zákazník a zakázka ve stavu `Vyžaduje kontrolu` s validačními varováními v parsovaném payloadu.

Volitelnou provider-neutrální AI extrakci lze zapnout pomocí `AI_EXTRACTION_ENABLED=true` a `AI_EXTRACTION_ENDPOINT`. Tajný token lze předat přes `AI_EXTRACTION_API_KEY`; ve výchozím stavu je AI vypnutá a její výpadek import nezastaví.

Zakázky podporují český produkční workflow stavů, auditovanou historii změn a samostatné časované poznámky. Detail zakázky zobrazuje zákazníka, historii, poznámky, zdrojové PDF a uložená parsovaná data.

### OCR závislosti

V backend image jsou nainstalované systémové balíky:
- `tesseract-ocr`
- `tesseract-ocr-ces`
- `poppler-utils`

Python balíky:
- `pdf2image`
- `pytesseract`

### Customers & Jobs (Milestone 1)

Backend nyní obsahuje normalizovanou entitu `Customer` a rozšířenou entitu `Job`.
- `Customer` slouží jako dlouhodobá evidence zákazníků (přidáno `customer_number`, `uuid`, kontaktní pole).
- `Job` obsahuje odkaz `customer_id`, `order_number` a `parser_confidence`. Vazba na `Upload` je reprezentována jednosměrně přes `Upload.job_id`.

Import workflow zůstává stejný, ale po importu už systém pracuje s `Customer` a `Job` jako primárními entitami.

## Testy a build

Backend testy:

```bash
cd backend
PYTHONPATH=. pytest -q
```

Frontend build:

```bash
cd frontend
npm run build
```

Docker E2E smoke check:

```bash
docker compose down -v
docker compose up --build -d
```

## Development workflow

Jak spustit projekt lokálně:

1. Sestavte a spusťte kontejnery:

```bash
docker compose up --build -d
```

2. Backend bude dostupný na `http://localhost:8000`, frontend na `http://localhost:3000`.

Jak spustit Alembic migrace lokálně:

```bash
cd backend
alembic upgrade head
```

Jak spustit backend testy lokálně:

```bash
cd backend
PYTHONPATH=. pytest -q
```

Jak funguje CI:

- CI pipeline je definována v `.github/workflows/ci.yml` a spouští se pro každé `pull_request`.
- Pipeline provede: instalaci backend závislostí, spuštění Alembic migrací, backend testy, instalaci a build frontendu, Docker image build, spuštění docker compose a smoke testy (health, login, create customer, import PDF, create job, job detail).
- Pokud CI běh selže, PR nebude považován za bezpečný ke sloučení.


## Struktura projektu

```text
backend/
  app/
    api/
    core/
    models/
    schemas/
    services/
    crud/
    dependencies/
    middleware/
frontend/
  src/
    app/
    components/
docs/
```
