# Test Resources README

Tento adresar obsahuje testy, ktere mohou vyzadovat externi proprietarni resources.

## Minimalni proprietarni resources

- backend/uploads/zl2.pdf
- backend/test_11.pdf

## Kdo je potrebuje

- backend/tests/test_pdf_parser.py
- backend/tests/test_parsers/test_vodafone_parser.py
- CI smoke krok v .github/workflows/ci.yml (import PDF)

## Lokalni setup

```bash
cd /workspaces/lygre
mkdir -p backend/uploads
# po ziskani souboru z privatniho uloziste:
cp <source>/zl2.pdf backend/uploads/zl2.pdf
cp <source>/test_11.pdf backend/test_11.pdf
```

## Lokalni overeni

```bash
cd /workspaces/lygre/backend
test -f uploads/zl2.pdf
test -f test_11.pdf
PYTHONPATH=. pytest -q tests/test_pdf_parser.py tests/test_parsers/test_vodafone_parser.py
```

## CI

CI ma resources stahnout pred backend testy a smoke testy.
Detailni navrh je v docs/testing.md.

## RC1 status

READY FOR RC1

Open item: External proprietary test resources required.
