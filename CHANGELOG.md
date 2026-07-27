# CHANGELOG

## Unreleased

- Fix: Stabilize Vodafone PDF parser to handle OCR garbles and QR extraction.

What was fixed
- Restored reliable OCR fallback for single-page PDFs.
- Improved QR extraction using OpenCV QRCodeDetector and prefer QR job numbers.
- Tightened `customer_name` regexes to avoid capturing service blocks.
- Added explicit patterns to support OCR-garbled labels (e.g. `apiijmeni`, `pfijmeni`, `piijmeni`).

Supported cases now
- `Jméno a příjmení: Name Surname` and common OCR variants
- `Jméno a pfijmeni`, `Jméno a piijmeni`, `Jménoapiijmeni` forms
- Trailing OCR tokens like `i)` or `1D` adjacent to names are recognized in context and not mis-attributed when possible.

Known OCR exceptions
- Some PDFs include stray tokens such as `i)` or `1D` as part of the OCR output adjacent to the name; these are OCR artifacts (not parser bugs) in the provided PDFs. The parser attempts to stop capture before `objednavky` and related markers but will keep tokens that appear inside the raw OCR name token.
- No heuristic trimming (length checks or AI) was added — changes are limited to regex improvements only.

Notes
- Changes are limited to `backend/app/services/pdf_parser_service.py` and related parser helpers.
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.0.0] - 2026-07-25 (Milestone 1)
### Added
- Normalized `Customer` entity and CRUD endpoints.
- Per-page `Upload` model for PDF imports.
- `Job` extended with `customer_id`, `order_number`, `parser_confidence` (0.0–1.0).
- Unified attachment relation: `uploads.job_id` (1:N relationship).
- `Upload.is_primary` flag and `JobDetail.primary_attachment_id` computed field.
- Integration test for 11-page PDF import.
- Alembic migrations: create customers, unify attachment relation, add `is_primary`.
- CI workflow for PR validation (tests, migrations, frontend build, docker build, smoke tests).
- Release notes for Milestone 1 (docs/releases/milestone-1.md).

### Changed
- Parser now always returns `parser_confidence` as float between 0.0 and 1.0.
- README updated with development instructions.

### Fixed
- SQLAlchemy relationships and migrations to support normalized model.

### Known issues
- Some deprecation warnings from dependencies (FastAPI `on_event`, Pydantic config, passlib) remain.

