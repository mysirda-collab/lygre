# AGENTS.md

## Project

Lygre is a CRM system for installation companies.

Technology stack:

- Backend: FastAPI + SQLAlchemy 2 + PostgreSQL
- Frontend: Next.js + React + TypeScript
- Docker Compose
- JWT authentication

---

## General Rules

Before making any changes:

1. Read this file.
2. Read `README.md`.
3. Read `docs/PROJECT_CONTEXT.md`.
4. Understand the existing code before modifying it.

---

## Coding Rules

- Preserve existing functionality.
- Keep backward compatibility.
- Prefer small and safe changes.
- Do not rewrite unrelated code.
- Update all affected files.
- Use SQLAlchemy 2 style.
- Use type hints.
- Keep backend and frontend consistent.
- Never change the database schema without creating a migration.

---

## Development Workflow

When implementing a feature:

1. Analyze the existing implementation.
2. Create a plan.
3. Modify the required files.
4. Check for side effects.
5. Summarize the changes.

---

## Current Priorities

1. PDF upload progress
2. OCR improvements
3. Dashboard improvements
4. Reservation improvements

---

## Important

If a requested change could affect other parts of the project, identify all impacted files and update them together.

Never guess how the project works—inspect the relevant code first.
