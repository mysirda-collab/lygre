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
- `NEXT_PUBLIC_API_BASE_URL` (default: `http://localhost:8000`)

Volitelné prostředí pro backend:
- `JWT_SECRET_KEY`
- `ACCESS_TOKEN_EXPIRES_MINUTES`
- `REFRESH_TOKEN_EXPIRES_DAYS`
- `SEED_ADMIN_EMAIL`
- `SEED_ADMIN_NAME`
- `SEED_ADMIN_PASSWORD`

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
