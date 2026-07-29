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
6. AI parser extracts structured data.
7. Existing customer is searched.
8. Customer is created if necessary.
9. Job is created.
10. Upload is marked as completed.

---

# Current Development

The current task is to implement upload progress reporting.

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
