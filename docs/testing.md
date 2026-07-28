# Testing Infrastructure for External Proprietary Resources

Tento dokument popisuje, jak provozovat testy, ktere zavisi na proprietarnich souborech, bez commitovani techto souboru do repozitare.

## Scope

Cilem je oddelit testovaci data od zdrojoveho kodu a drzet je v privatnim ulozisti nebo artifact storage.

## Proprietarni soubory a pozadovane cesty

| Resource ID | Pozadovana cesta ve workspace | Pouziti |
| --- | --- | --- |
| vodafone-sample-zl2 | backend/uploads/zl2.pdf | backend/tests/test_pdf_parser.py, backend/tests/test_parsers/test_vodafone_parser.py, tmp_integration_run.py |
| smoke-import-11-pages | backend/test_11.pdf | .github/workflows/ci.yml (Smoke tests, upload PDF krok) |

Poznamka: testy v backend/tests/test_api_integration.py generuji PDF in-memory a na proprietarnich souborech nezavisi.

## Lokalni nacteni test resources

1. Vyvojar ziska archiv resources z privatniho uloziste (napr. S3, Azure Blob, privatni GitHub release asset).
2. Archiv musi obsahovat minimalne tyto soubory:
   - zl2.pdf
   - test_11.pdf
3. Ve workspace je ulozi presne na pozadovane cesty.

Priklad (tar.gz bundle):

```bash
cd /workspaces/lygre
mkdir -p backend/uploads
# po stazeni archivu napr. do /tmp/lygre-test-resources.tar.gz
tar -xzf /tmp/lygre-test-resources.tar.gz -C /tmp
cp /tmp/lygre-test-resources/zl2.pdf backend/uploads/zl2.pdf
cp /tmp/lygre-test-resources/test_11.pdf backend/test_11.pdf
```

Overeni:

```bash
cd /workspaces/lygre
test -f backend/uploads/zl2.pdf && echo "OK zl2.pdf"
test -f backend/test_11.pdf && echo "OK test_11.pdf"
```

Spusteni zavislych testu:

```bash
cd /workspaces/lygre/backend
PYTHONPATH=. pytest -q tests/test_pdf_parser.py tests/test_parsers/test_vodafone_parser.py
```

## CI nacteni test resources

Doporuceny pristup je distribuovat resources jako jediny archiv a stahovat ho v CI pred testy.

### Pozadovane CI secrets

- TEST_RESOURCES_URL: privatni URL na archiv (kratkodoba signed URL nebo interni endpoint).
- TEST_RESOURCES_SHA256: checksum archivu pro integritni kontrolu.

### CI kroky (obecne)

1. Stahnout archiv do runneru.
2. Overit SHA256.
3. Rozbalit archiv.
4. Zkopirovat soubory na:
   - backend/uploads/zl2.pdf
   - backend/test_11.pdf
5. Spustit backend testy a smoke testy.

## Navrh GitHub Actions workflow

Projekt pouziva GitHub Actions. Nize je navrh workflow, ktery nacte externi resources z privatniho uloziste pred testy.

```yaml
name: CI with External Test Resources

on:
  pull_request:
  workflow_dispatch:

jobs:
  ci:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: lygre
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres -d lygre"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10

    env:
      DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5432/lygre
      PYTHONUNBUFFERED: 1

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Fetch external proprietary test resources
        env:
          TEST_RESOURCES_URL: ${{ secrets.TEST_RESOURCES_URL }}
          TEST_RESOURCES_SHA256: ${{ secrets.TEST_RESOURCES_SHA256 }}
        run: |
          set -euo pipefail
          curl -fsSL "$TEST_RESOURCES_URL" -o /tmp/lygre-test-resources.tar.gz
          echo "$TEST_RESOURCES_SHA256  /tmp/lygre-test-resources.tar.gz" | sha256sum -c -
          rm -rf /tmp/lygre-test-resources
          mkdir -p /tmp/lygre-test-resources
          tar -xzf /tmp/lygre-test-resources.tar.gz -C /tmp/lygre-test-resources

          mkdir -p backend/uploads
          cp /tmp/lygre-test-resources/zl2.pdf backend/uploads/zl2.pdf
          cp /tmp/lygre-test-resources/test_11.pdf backend/test_11.pdf

      - name: Validate resources are present
        run: |
          test -f backend/uploads/zl2.pdf
          test -f backend/test_11.pdf

      # navazat stavajicimi kroky: setup python, install deps, migrations,
      # backend tests, frontend build, docker compose smoke tests
```

## Test dependency matrix

| Test nebo krok | Zavislost |
| --- | --- |
| backend/tests/test_pdf_parser.py::test_parse_sample_page | backend/uploads/zl2.pdf |
| backend/tests/test_parsers/test_vodafone_parser.py::test_vodafone_parser_page2 | backend/uploads/zl2.pdf |
| tmp_integration_run.py | backend/uploads/zl2.pdf |
| .github/workflows/ci.yml -> Smoke tests -> import test PDF | backend/test_11.pdf |

## Release status

READY FOR RC1

Open item: External proprietary test resources required.
