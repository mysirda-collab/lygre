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

## Milestone 1: Customers & Jobs (2026-07-25)

- Migrace: `010_create_customers_and_extend_jobs.py` přidána (tabulka `customers`, rozšíření `jobs`).
-- Model `Customer` přidán, `Job` rozšířen o `customer_id`, `order_number`, `parser_confidence`.
213:Customer (id, uuid, customer_number, name, phone, email, ...) 1---N Job (id, job_number, customer_id, order_number, parser_confidence)
215:Upload představuje jednu stránku PDF; vazba mezi Upload a Job se nyní sjednocuje jednosměrně přes `uploads.job_id`.
- API: přidány endpointy `GET/POST/PUT /api/v1/customers`.
- Tests: přidány základní testy pro `Customer` CRUD.

ER diagram (zkráceně):

Customer (id, uuid, customer_number, name, phone, email, ...) 1---N Job (id, job_number, customer_id, order_number, parser_confidence, attachment_id)

Upload představuje přílohu jedné stránky a je na něj linkováno z `jobs.attachment_id`.

Souborová změna (vybrané):
- backend/alembic/versions/010_create_customers_and_extend_jobs.py
- backend/app/models/customer.py
- backend/app/models/job.py
- backend/app/crud/customer.py
- backend/app/services/job_creation_service.py
- backend/app/schemas/customer.py
- backend/app/api/v1/endpoints/customers.py

Další TODO pro Milestone 2:
- End-to-end test importu 11-stránkového PDF v reálném prostředí (frontend+backend).
- UI pro prohlížení/spravování `Customer` a hromadné párování.
- Backfill existujících Jobs do Customers.
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

### Runtime konfigurace frontend API (Codespaces + Proxmox)
- Odstraněn hardcoded `http://localhost:8000` ve frontend helperu.
- Frontend nyní defaultně používá relativní cesty (`/api/...`) a same-origin volání.
- Přidán Next.js proxy rewrite `/api/:path* -> ${NEXT_SERVER_API_URL}/api/:path*`.
- Docker Compose nastavuje `NEXT_SERVER_API_URL=http://backend:8000`, takže není nutné měnit zdrojový kód mezi prostředími.
- Pro nasazení mimo Docker síť stačí změnit environment proměnné, nikoliv kód.

---

## Hotfix: Import PDF autorizace

### Nahlášený problém
- Na stránce Import PDF tlačítko "Nahrát PDF" vracelo backend chybu `Missing access token`.
- Příčina: upload flow používal přímé `fetch` volání bez sdílené autentizační vrstvy.

### Oprava
- `frontend/src/app/import-pdf/page.tsx`:
  - `fetchUploads` změněno z `fetch` na `authFetch`.
  - upload POST `/api/v1/uploads/pdf` změněn z `fetch` na `authFetch`.
- `frontend/src/app/import-pdf/review/[id]/page.tsx`:
  - načtení uploadu a review submit změněny na `authFetch`.
- Ověřeno, že `authFetch` používá `getStoredAccessToken()` z localStorage a přidává header `Authorization: Bearer <token>`.

### Ověření
- Frontend build: `cd frontend && npm run build` -> OK.
- Docker rebuild: `docker compose down && docker compose up -d --build` -> OK.
- Smoke test uploadu přes frontend API proxy:
  - login -> OK,
  - `POST http://localhost:3000/api/v1/uploads/pdf` s Bearer tokenem -> `upload_id` vráceno,
  - následné `GET http://localhost:3000/api/v1/uploads/pdf` obsahuje nahraný soubor (`smoke-upload.pdf`).
- UI smoke test (Playwright, headless Chromium):
  - scénář `login -> /import-pdf -> výběr souboru -> Nahrát PDF` proběhl úspěšně,
  - výsledek: `ui_upload_smoke_ok`,
  - v UI se zobrazí potvrzení `PDF nahráno:` a soubor je v seznamu uploadů.

---

## OCR pipeline pro skenovaná PDF

### Implementováno
- `backend/app/services/pdf_parser_service.py`:
  - extrakce textu běží ve 2 krocích:
    1) `pypdf` extrakce textové vrstvy,
    2) automatický fallback na OCR při prázdném výsledku.
  - OCR používá `pdf2image` + `pytesseract` (jazyk `ces+eng`) na všech stránkách PDF.
  - výsledný text se skládá ze všech stránek do jednoho dokumentu.
  - doplněn specializovaný parser zakázkového listu (včetně případů, kde OCR slije více polí do jedné řádky).
  - extrahovaná pole:
    - číslo objednávky,
    - datum vytvoření,
    - zákaznické číslo,
    - jméno zákazníka,
    - ulice,
    - město,
    - telefon,
    - ID objednávky,
    - typ objednávky.
  - pravidlo: pokud OCR selže nebo chybí povinná pole order-formu, `should_create_job=False` (workflow vyžaduje kontrolu).

- `backend/requirements.txt`:
  - přidáno `pdf2image`, `pytesseract`.

- `backend/Dockerfile`:
  - přidány systémové závislosti `tesseract-ocr`, `tesseract-ocr-ces`, `poppler-utils`.

- `backend/tests/test_pdf_parser_service.py`:
  - test OCR fallbacku při prázdné textové vrstvě,
  - test parseru specializovaného order-formu,
  - test missing-fields -> `should_create_job=False`,
  - regresní test pro „slepované“ labely na jedné řádce.

### Ověření na přiložených PDF
- Byl proveden běh parseru nad 8 PDF soubory v `backend/uploads`.
- Výsledek:
  - textová PDF byla načtena přes `pypdf`,
  - skenovaná/poškozená PDF bez textu zůstala s `should_create_job=False`,
  - order-form PDF (`972b81353be240cf839938cccec90ee3.pdf`) bylo úspěšně rozpoznáno a vyparsováno:
    - `order_number=1780283`
    - `creation_date=22.07.2026`
    - `customer_number=1050206268`
    - `customer_name=Krejčířová Františka`
    - `street=Štolcova`
    - `city=BRNO-ČERNOVICE`
    - `phone=605041013; Františka Krejčířová`
    - `order_id=1-308280003023`
    - `order_type=Nestandard`
    - `missing_fields=[]`, `should_create_job=True`.

### Testy po změně
- `cd backend && PYTHONPATH=. python -m unittest discover -s tests -p 'test_*.py'` -> `Ran 20 tests ... OK`.

---

## Stabilizace: vícestránkové PDF + navigace zakázek + seznam zakázek

### 1) Import vícestránkového PDF (robustní detekce listů)

Implementace byla rozšířena tak, aby jeden upload PDF vytvářel samostatné záznamy podle reálně detekovaných zakázkových listů, bez fixního počtu stran.

- `backend/app/services/pdf_parser_service.py`:
  - přidána metoda `extract_order_sheet_candidates(pdf_bytes)`:
    - zpracování po stránkách,
    - fallback OCR po stránkách,
    - split jedné stránky na více zakázkových listů při opakovaném markeru `Číslo objednávky` / `Cislo objednavky`.
  - OCR předzpracování obrazu:
    - ořez okrajů (potlačení rušivých značek/okrajů),
    - pokus o auto-rotaci přes OSD (`pytesseract.image_to_osd`),
    - převod do grayscale.

- `backend/app/api/v1/endpoints/uploads.py`:
  - endpoint `/api/v1/uploads/pdf` nyní:
    - vytváří 1 upload na každý detekovaný list,
    - ke každému uploadu ukládá vlastní page-PDF,
    - každý upload zpracuje samostatně (`process_upload_text`),
    - vrací `created_ids` a `created_count`.

- `backend/app/schemas/upload.py`:
  - `UploadCreateResponse` rozšířen o:
    - `created_ids: list[int]`
    - `created_count: int`

Výsledek:
- z jednoho PDF vzniká správný počet nezávislých upload záznamů,
- každý má vlastní OCR text, vlastní parsed data, vlastní detail a vlastní `job_id`.

### 2) OCR parser (telefon + zákazník)

- V parseru doplněno oddělení slité hodnoty kontaktu:
  - vstup např. `605041013; Františka Krejčířová`
  - výstup:
    - `phone=605041013`
    - `customer_name=Františka Krejčířová` (pokud jméno chybí jinde).

- Dále přidána OCR-tolerantní pravidla pro šum v labelech (např. poškozené `Zákaznické číslo`) a zpřesněné stop-patterny, aby se hodnoty nepřelévaly mezi poli.

### 3) "Otevřít zakázku" -> "Zakázka nebyla nalezena" (root cause + fix)

Root cause:
- `Job` se sice vytvořil a `upload.job_id` byl vyplněn, ale detail endpoint padal na validační chybu serializace (`phone` ve tvaru `605041013; Jméno` neprošel validátorem `JobRead`).
- Frontend tak viděl neúspěšný response a zobrazil "Zakázka nebyla nalezena".

Fix:
- `backend/app/api/v1/endpoints/jobs.py`:
  - přidána normalizační vrstva pro výstup (`_job_to_read`),
  - sanitace `phone/email/zip` při serializaci,
  - použito v `/jobs`, `/jobs/{id}`, `/jobs/{id}/detail`, dashboard summary.
- `backend/app/services/job_creation_service.py`:
  - normalizace `phone/email/zip` ještě před create,
  - validace přes `JobCreate.model_validate(...)`,
  - při nevalidních datech přepnutí uploadu do `Vyžaduje kontrolu` místo 500.

### 4) "Nepodařilo se načíst seznam zakázek" (root cause + fix)

Root cause:
- request `GET /api/v1/jobs` vracel 500.
- backend log: Pydantic `ValidationError` na `items.0.phone` (nevalidní formát telefonu z OCR dat).

Fix:
- stejná normalizační vrstva v `jobs` endpointu odstranila pád serializace.
- Po fixu:
  - `GET /api/v1/jobs` -> 200,
  - seznam zakázek se načítá správně,
  - detail zakázky je dostupný.

### 5) Kompletní E2E test (přiložené PDF)

Proveden clean run:
- `docker compose down -v`
- `docker compose up -d --build`

Testovací soubor:
- `backend/uploads/972b81353be240cf839938cccec90ee3.pdf`

Ověřený výsledek:
- upload response:
  - `created_count=4`
  - `created_ids=[1,2,3,4]`
- vytvoření zakázek:
  - všechny 4 uploady mají `status=Hotovo`, `processing_status=Hotovo`, vlastní `job_id` (1..4),
  - každá zakázka má vlastní detail (`GET /api/v1/jobs/{id}/detail` -> 200).
- seznam zakázek:
  - `GET /api/v1/jobs` -> 200,
  - `total=4`, všechny nové zakázky viditelné.
- dashboard:
  - `GET /api/v1/jobs/dashboard/summary` -> 200,
  - `status_counts.new=4` (odpovídá vytvořeným zakázkám).
- UI smoke (Playwright):
  - login -> import PDF -> upload -> nalezeny 4 unikátní odkazy "Otevřít zakázku" -> otevření detailu všech 4 zakázek OK,
  - výsledek: `ui_e2e_ok {"linksChecked":4}`.

### 6) Testy a build po opravách

- Backend:
  - `cd backend && PYTHONPATH=. python -m unittest discover -s tests -p 'test_*.py'` -> `Ran 24 tests ... OK`.
- Frontend:
  - `cd frontend && npm run build` -> OK.
- Docker:
  - `docker compose down -v && docker compose up -d --build` -> backend healthy, frontend started.

---

## Sprint 4: Page-based import PDF (1 strana = 1 zakázka)

### Implementováno
- Upload flow je přepsaný na page-based architekturu:
  - po uploadu zdrojového PDF se dokument rozdělí na jednotlivé stránky,
  - pro každou stránku vzniká samostatný upload záznam,
  - nad každou stránkou běží OCR a parser,
  - z každé stránky se vytváří samostatná zakázka.
- Do modelu uploadu byla doplněna source/page metadata:
  - `source_document_id`, `source_original_filename`, `source_stored_filename`, `source_file_path`,
  - `page_number`, `total_pages`.
- Přidán endpoint pro stažení původního zdrojového PDF:
  - `GET /api/v1/uploads/pdf/{upload_id}/source-file`.
- Stabilizace tvorby zakázky z každé stránky:
  - při nekompletním parser výstupu se použije fallback `job_number` a `customer_name`,
  - pokud parser nevrátí plně validní data, zakázka se i tak vytvoří, upload je označen `Vyžaduje kontrolu`.

### Ověření na 11stránkovém PDF
- V čistém prostředí (`docker compose down -v && docker compose up -d --build`) byl proveden E2E test na 11stránkovém PDF `zl2.pdf`.
- Ověřené výsledky:
  - `created_count = 11`,
  - vzniklo 11 upload záznamů,
  - `page_number` pokrývá 1..11,
  - `total_pages = 11` na všech záznamech,
  - `source_original_filename = zl2.pdf` na všech záznamech,
  - vzniklo 11 unikátních zakázek,
  - `GET /api/v1/jobs/{id}/detail` vrací 200 pro všech 11 zakázek,
  - `GET /api/v1/jobs` vrací `total = 11`,
  - `GET /api/v1/jobs/dashboard/summary` vrací `new = 11`,
  - `GET /api/v1/uploads/pdf/{id}/source-file` vrací 200.

### Poznámka k runtime
- Upload 11stránkového dokumentu může přes frontend proxy na portu 3000 timeoutovat kvůli době OCR zpracování.
- Pro technické E2E ověření dlouhých uploadů je stabilní volat backend API přímo na portu 8000.
