---
title: HIS.Pro
sdk: docker
app_port: 7860
pinned: false
---

# HIS.Pro

HIS.Pro is a multi-tenant hospital information system built with FastAPI,
SQLAlchemy, PostgreSQL/Redis, and React/TypeScript. It covers patient registration,
appointments, queue, consultations, records, laboratory, radiology, pharmacy,
wards, billing, inventory, staffing, alerts/chat, reports, audit, and legacy-data
migration.

The product priorities are tenant/branch isolation, security, duplicate-write and
concurrency safety, responsive workflows, and horizontal scalability.

## Status

The repository is in pre-launch hardening. Core workflows are implemented, but
general availability remains **NO-GO** until the evidence in
[Launch Readiness](docs/12_LAUNCH_READINESS.md) is complete. Invitation-only
controlled pilots require explicit security and hospital approval.

Hugging Face staging operators should follow the
[Space deployment checklist](docs/HUGGING_FACE_STAGING.md); production security
checks intentionally fail closed when required secrets or shared services are
missing.

## Stack

- FastAPI 0.104.1 and Pydantic 2
- SQLAlchemy 2 and Alembic
- PostgreSQL 16 production database; SQLite for tests/development only
- Redis for realtime fanout and shared coordination
- Durable database background jobs and OhmattOS integration outbox
- React 18, TypeScript, Vite, TanStack Query, Tailwind, and Radix UI
- ClamAV-gated private uploads in production
- Non-root Docker/Gunicorn/Uvicorn deployment

## Local Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\migrate.py
python run.py
```

The FastAPI development server normally listens on `http://127.0.0.1:8000`.

## Current Frontend

```powershell
Set-Location 'app\templates\initial frontend'
npm ci
npm run dev
```

The independent future UI is in `app/templates/frontend-v2` and uses the same
commands. Do not overwrite the current frontend when developing V2.

## Verification

```powershell
python -m compileall -q app scripts migrations tests
python -m unittest discover -s tests
```

Run `npm test` and `npm run build` in each selected frontend. Production release
also requires PostgreSQL/Redis/ClamAV/object-storage integration, migration/restore,
browser role, dependency, isolation, concurrency, load, and security evidence.

## Documentation

Start at [docs/index.md](docs/index.md). The database and API references are
generated from the live SQLAlchemy/FastAPI registry:

```powershell
python scripts\generate_code_reference_docs.py
```

Key documents:

- [System Architecture](docs/02_SYSTEM_ARCHITECTURE.md)
- [Database Reference](docs/04_DATABASE_REFERENCE.md)
- [API Reference](docs/05_API_REFERENCE.md)
- [Backend and Security](docs/08_BACKEND_AND_SECURITY.md)
- [Configuration and Deployment](docs/09_CONFIGURATION_INSTALLATION_DEPLOYMENT.md)
- [Hospital Operations Manual](docs/13_HOSPITAL_OPERATIONS_MANUAL.md)
- [Hospital Operations Manual (Word)](docs/HIS_PRO_HOSPITAL_OPERATIONS_MANUAL.docx)
- [Hospital Operations Manual (PDF)](output/pdf/HIS_PRO_HOSPITAL_OPERATIONS_MANUAL.pdf)
- [Launch Readiness](docs/12_LAUNCH_READINESS.md)

## Production Rules

- Use PostgreSQL, Redis, private encrypted object storage/shared volume, and ClamAV.
- Store independent secrets/private keys in a secret manager; never commit `.env`.
- Keep public signup and every OhmattOS feature flag off until its launch gate closes.
- Run `python scripts/migrate.py` as a one-shot deployment step before API/workers.
- Configure `TENANT_BASE_DOMAIN` for a wildcard domain you control, then use
  canonical tenant hosts such as `https://<hospital>.<tenant-base-domain>`.
- Do not claim compliance certification based on this application alone.
