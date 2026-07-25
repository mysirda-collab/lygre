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

