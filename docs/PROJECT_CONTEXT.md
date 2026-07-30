# PROJECT_CONTEXT.md

# Project Overview

Lygre is a CRM system for installation and service companies.

The project manages:

- Customers
- Jobs
- Reservations
- PDF document import
- Dashboard
- Authentication

---

# Technology Stack

Backend

- FastAPI
- SQLAlchemy 2
- PostgreSQL
- Alembic

Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

Infrastructure

- Docker Compose

---

# Architecture

Frontend

↓

REST API

↓

FastAPI

↓

Services

↓

CRUD

↓

SQLAlchemy

↓

PostgreSQL

---

# PDF Import Workflow

1. User uploads a PDF.
2. Upload is processed in the background.
3. PDF text is extracted.
4. OCR is used if needed.
5. QR codes are detected.
6. Deterministic parser extracts structured data; optional provider-neutral AI can only fill missing values.
7. Existing customer is searched.
8. Customer is created if necessary.
9. Job is created.
10. Incomplete data creates a linked job with status `Vyžaduje kontrolu`; reliable data creates `Nová`.
11. Upload is marked as completed and remains linked to the job.

---

# Current Development

The first production PDF-to-customer-to-job workflow is implemented, including duplicate prevention, review jobs, status history and timestamped notes.

Database fields:

- uploads.processing_progress
- uploads.processing_message

The frontend polls the upload status until processing reaches 100%.

---

# Development Principles

- Keep backward compatibility.
- Preserve the existing architecture.
- Prefer small changes over large rewrites.
- Modify all affected files together.
- Do not change the database schema without a migration.
