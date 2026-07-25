# REPORT

## Shrnutí auditu
Audit byl proveden nad backendem, frontendem, migracemi, Docker orchestrací a testy. Cíl byl stabilizovat aplikaci bez přidávání nové business funkcionality.

## 1) Nalezené chyby

### TODO/FIXME a dead code
- V kódu nebyly nalezeny aktivní TODO/FIXME/HACK poznámky (mimo závislostní lock soubor).
- Byl nalezen dead code v legacy example vrstvách:
  - `backend/app/models/example.py`
  - `backend/app/crud/example.py`
  - `backend/app/schemas/example.py`
- Byl nalezen dead state ve frontend review stránce (nevyužitý `parsedData` state).

### Backend architektura a runtime
- Upload endpoint vracel 500 při chybě parseru PDF místo kontrolovaného stavu zpracování.
- `JobCreationService` měl riziko `KeyError` při chybějících údajích (`phone`, `email`, ...).
- Validace `Job` dat byla nedostatečná:
  - `job_number` a `customer_name` mohly projít jako prázdné po trimu.
  - chyběla validace formátu `email`, `phone`, `zip`.

### Migrace
- Revize Alembic měla příliš dlouhý identifikátor (`version_num` v Alembic tabulce je standardně 32 znaků).
- Historicky byl nesoulad mezi modelem `jobs.is_deleted` a schématem DB.

### Frontend architektura
- API URL byly hardcoded v několika stránkách (`http://localhost:8000`), což komplikovalo provoz v různých prostředích.

### Docker Compose / clean startup
- Nebyla garantována automatická aplikace migrací při startu backendu.
- Frontend neměl vazbu na health backendu.

## 2) Provedené opravy

### Odstranění dead code
- Smazány soubory:
  - `backend/app/models/example.py`
  - `backend/app/crud/example.py`
  - `backend/app/schemas/example.py`
- Uklizen nevyužitý state v `frontend/src/app/import-pdf/review/[id]/page.tsx`.

### Stabilizace backendu
- Zpevněn upload flow v `backend/app/api/v1/endpoints/uploads.py`:
  - při selhání parseru už endpoint nekončí 500,
  - upload se označí `status=Chyba`, `processing_status=Chyba`, vyplní se `error_message`.
- Zpevněn `backend/app/services/job_creation_service.py`:
  - bezpečný přístup přes `.get()` pro částečně vyplněná data,
  - fallback automatického čísla zakázky při chybějícím `job_number`.
- Rozšířena validace `backend/app/schemas/job.py`:
  - neprázdný `job_number`, `customer_name` po trimu,
  - validace `email`, `phone`, `zip`,
  - normalizace volitelných textových polí.
- Upraven parser `backend/app/services/pdf_parser_service.py`:
  - robustnější rozpoznání město/PSČ i při poškozené diakritice,
  - fallback detekce `email`, `phone`, `zip` z celého textu.
- Nahrazeno deprecated `datetime.utcnow()` za timezone-aware UTC v modelech/CRUD.

### Migrace
- Revize 005 přejmenována na bezpečný identifikátor:
  - `005_jobs_softdel_json`
- Potvrzena migrační řada v běžícím containeru:
  - `001_init -> 002_add_jobs -> 003_add_uploads -> 004_add_pdf_parsing_fields -> 005_jobs_softdel_json`
- `parsed_data` je ukládáno jako JSON objekt.

### Frontend architektura
- Přidána centralizace API URL:
  - `frontend/src/lib/api.ts`
- Všechny relevantní stránky přepnuty z hardcoded URL na `apiUrl(...)`:
  - `frontend/src/app/import-pdf/page.tsx`
  - `frontend/src/app/import-pdf/review/[id]/page.tsx`
  - `frontend/src/app/orders/page.tsx`
  - `frontend/src/app/orders/[id]/page.tsx`
- Po uložení review se přechází přímo na detail zakázky (`/orders/{id}`).

### Docker Compose a clean startup
- Backend startuje s migracemi automaticky:
  - `alembic upgrade head && uvicorn ...`
- Přidán healthcheck backendu.
- Frontend čeká na healthy backend.
- Compose ověřen čistým spuštěním:
  - `docker compose down -v`
  - `docker compose up --build -d`

### Dokumentace
- Aktualizován `README.md` (aktuální stav, testy, build, runtime).

## 3) Doplňené testy

### Unit testy parseru
- Rozšířen `backend/tests/test_pdf_parser_service.py`:
  - parsing standardního textu,
  - parsing s poškozenými labely město/PSČ,
  - fallback detekce email/telefon,
  - test extrakce textu přes mock `PdfReader`.

### Integrační testy API
- Přidán `backend/tests/test_api_integration.py`:
  - `/`, `/api/v1/health`, `/api/v1/modules`,
  - CRUD `/api/v1/jobs`,
  - validační chyba pro neplatný email,
  - upload invalid type,
  - upload runtime failure -> status `Chyba`,
  - review endpoint vytvoření zakázky,
  - download chybějícího souboru -> 404.

## 4) Ověření funkčnosti

### Backend
- `python -m unittest discover -s tests -p 'test_*.py'` -> zelené
- `python -m compileall app` -> bez chyb

### Frontend
- `npm run build` -> úspěšný build bez typových chyb

### Migrace
- `docker compose exec -T backend alembic current` -> `005_jobs_softdel_json (head)`
- `docker compose exec -T backend alembic history` -> konzistentní řetězec

### Endpointy (live)
- Ověřeny endpointy:
  - `GET /api/v1/health`
  - `GET /api/v1/modules`
  - `GET /api/v1/jobs`
  - `GET /api/v1/uploads/pdf`
  - `POST /api/v1/uploads/pdf`
  - `POST /api/v1/uploads/pdf/{id}/review`

### One-command startup
- Ověřeno, že čistý projekt nastartuje jedním příkazem:
  - `docker compose up --build -d`

## 5) Zbývající technický dluh
- Legacy migrace `001_init` stále zakládá tabulku `examples` (historický artefakt).
- Chybí autentizace/autorizace endpointů.
- Chybí CI pipeline pro automatické spuštění testů a buildů při každém PR.
- Frontend zatím nemá jednotnou vrstvu pro handling API chyb (např. globální toast/error boundary).

## 6) Doporučení pro další fázi
1. Přidat CI (backend tests + frontend build + migration check).
2. Zavést autentizaci (JWT/session) a role-based autorizaci.
3. Odstranit historický `examples` artefakt řízenou datovou migrací.
4. Přidat observabilitu (strukturované logy, metriky, alerty).
5. Rozšířit e2e testy frontendu (upload + review workflow v prohlížeči).

---

## Sprint 1: Autentizace a autorizace

### Co bylo vytvořeno
- Backend auth vrstva:
  - JWT access token + refresh token
  - hashování hesel (argon2 přes passlib)
  - endpointy: `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/refresh`, `/api/v1/auth/me`
- RBAC role model:
  - role: `admin`, `manager`, `worker`
  - ochrana endpointů dle role (`jobs`, `uploads`, `modules`)
- Seed admin účtu při startupu backendu.
- Frontend auth vrstva:
  - funkční login stránka
  - uložení tokenů
  - automatické obnovení access tokenu při 401
  - route guard + middleware ochrana rout
  - odhlášení
  - zobrazení jména přihlášeného uživatele

### Jaké soubory byly změněny
- Backend:
  - `backend/app/api/v1/api.py`
  - `backend/app/api/v1/endpoints/auth.py`
  - `backend/app/api/v1/endpoints/jobs.py`
  - `backend/app/api/v1/endpoints/modules.py`
  - `backend/app/api/v1/endpoints/uploads.py`
  - `backend/app/core/config.py`
  - `backend/app/core/security.py`
  - `backend/app/crud/refresh_token.py`
  - `backend/app/crud/user.py`
  - `backend/app/dependencies/auth.py`
  - `backend/app/main.py`
  - `backend/app/models/refresh_token.py`
  - `backend/app/models/user.py`
  - `backend/app/schemas/auth.py`
  - `backend/app/services/auth_service.py`
  - `backend/alembic/env.py`
  - `backend/alembic/versions/006_auth_users_tokens.py`
  - `backend/tests/test_api_integration.py`
  - `backend/requirements.txt`
- Frontend:
  - `frontend/src/app/layout.tsx`
  - `frontend/src/app/login/page.tsx`
  - `frontend/src/app/page.tsx`
  - `frontend/src/components/AuthGate.tsx`
  - `frontend/src/components/Sidebar.tsx`
  - `frontend/src/components/UserMenu.tsx`
  - `frontend/src/lib/auth.ts`
  - `frontend/middleware.ts`

### Ověření Sprintu 1
- Backend testy: zelené (`python -m unittest discover -s tests -p 'test_*.py'`).
- Frontend build: úspěšný (`npm run build`).
- Docker Compose: clean start úspěšný (`docker compose down -v && docker compose up --build -d`).
- Migrace: head potvrzen (`006_auth_users_tokens`).
- E2E auth ověřeno:
  - login vrací access+refresh
  - `/auth/me` vrací přihlášeného uživatele
  - refresh vrací nový access token
  - logout invaliduje refresh token

### Co zbývá do dalšího sprintu
- Zavést jemnější RBAC mapu po jednotlivých operacích a entitách.
- Přidat audit trail pro auth akce (login/logout/refresh fail).
- Přidat frontend e2e browser testy login flow.

---

## Sprint 2: Funkční správa zakázek

### Implementováno
- Backend:
  - Rozšířen model zakázky o prioritu (`low`, `medium`, `high`, `urgent`).
  - Přidán endpoint dashboardu: `GET /api/v1/jobs/dashboard/summary`.
  - Přidán endpoint detailu zakázky: `GET /api/v1/jobs/{id}/detail` (zakázka + přílohy + audit log).
  - Rozšířen seznam zakázek (`GET /api/v1/jobs`) o filtry:
    - `status`, `priority`, `technician`, `customer`,
    - `installation_date_from`, `installation_date_to`,
    - fulltext `search`,
    - server-side řazení a stránkování.
  - Přidány DB indexy pro výkon filtrování a třídění.
  - Migrační revize `007_jobs_priority_indexes` včetně doplnění `audit_logs` tabulky v prostředích, kde chyběla.

- Frontend:
  - Dashboard napojen na backend metriky (stavy, poslední, po termínu, dnešní montáže).
  - Seznam zakázek rozšířen o Sprint 2 filtry a prioritu.
  - Detail zakázky zobrazuje audit historii a přílohy.
  - Editační modal pokrývá změnu stavu, priority, technika, termínu a poznámek.
  - Přidány loading skeletony, empty states a segmentové error boundary:
    - `frontend/src/app/orders/error.tsx`
    - `frontend/src/app/orders/loading.tsx`
    - `frontend/src/app/orders/[id]/error.tsx`
    - `frontend/src/app/orders/[id]/loading.tsx`

### Ověření Sprintu 2
- Backend testy:
  - `cd backend && PYTHONPATH=. pytest -q` -> `15 passed`.
- Frontend build:
  - `cd frontend && npm run build` -> úspěšný build.
- Docker E2E:
  - `docker compose down -v && docker compose up --build -d` -> backend i frontend healthy/start.
  - Ověřen login admin účtem (`/api/v1/auth/login`).
  - Ověřen dashboard endpoint (`/api/v1/jobs/dashboard/summary`).
  - Ověřen create + filtrování zakázek přes nové parametry.

### Poznámky
- V prostředí testů je potřeba pro `pytest` spouštět backend s `PYTHONPATH=.`.
- `GET /health` nebyl v runtime dostupný; systémové health endpointy projektu zůstávají pod API namespace.

---

## Sprint 3: Plánování montáží a kalendář techniků

### Implementováno
- Backend:
  - nový model `calendar_events` (typ události, čas od/do, vazba na zakázku a technika),
  - nová migrace `008_calendar_events` včetně indexů pro časové dotazy a filtraci technika,
  - nové endpointy:
    - `GET /api/v1/calendar/technicians`
    - `GET /api/v1/calendar/events`
    - `POST /api/v1/calendar/events`
    - `GET /api/v1/calendar/events/{id}`
    - `PUT /api/v1/calendar/events/{id}`
    - `PATCH /api/v1/calendar/events/{id}/schedule`
    - `DELETE /api/v1/calendar/events/{id}`
  - kontrola kolizí termínů (overlap) na technika,
  - audit log pro `create`, `update`, `reschedule`, `delete`.

- Frontend:
  - plná stránka kalendáře přes FullCalendar (`month/week/day`),
  - drag & drop přesun termínů,
  - resize událostí,
  - kliknutí na událost přesměruje na detail zakázky,
  - tvorba události z výběru slotu nebo tlačítkem,
  - barevné rozlišení událostí podle stavu zakázky,
  - filtr techniků,
  - loading skeletony, toasty, error boundary, empty state.

- Testy:
  - rozšířen integrační test `test_calendar_events_crud_collision_and_filter`
  - ověřuje CRUD, kolize, filtry, reschedule i audit stopy.

### Ověření Sprintu 3
- Backend testy:
  - `cd backend && PYTHONPATH=. pytest -q` -> `16 passed`.
- Frontend build:
  - `cd frontend && npm run build` -> úspěšný build.
- Docker E2E:
  - `docker compose down -v && docker compose up --build -d` -> backend healthy, frontend started.
  - Ověřen auth login a API dostupnost po clean startu.

### Poznámky Sprintu 3
- V tomto prostředí je `pytest` bez `PYTHONPATH=.` očekávaně neúspěšný (import `app`).
- FullCalendar byl integrován bez přímých CSS importů z package exportů (nejsou dostupné přes `exports` v použité verzi balíku).
