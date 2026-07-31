# Folder Structure

## Repository Root

| Path | Responsibility |
|---|---|
| `app/` | FastAPI application, domain models, services, routes, middleware, and served static files |
| `migrations/` | Alembic configuration and ordered schema revisions |
| `scripts/` | Migration runner, background/outbox workers, and documentation generation |
| `tests/` | Backend unit/integration, tenant isolation, security, schema, worker, and routing tests |
| `docs/` | Technical, operational, launch, migration, and integration documentation |
| `Dockerfile` | Multi-stage non-root production image |
| `docker-compose.yml` | Reference PostgreSQL, Redis, ClamAV, migration, API, and worker topology |
| `.env.production.example` | Canonical production environment variable template without real secrets |
| `requirements.txt` | Pinned Python runtime dependencies |
| `run.py` | Local application entry point |
| `config.py` | Legacy configuration compatibility; production settings are primarily environment-driven |

`BACKEND_DOCUMENTATION.md`, `DEPLOYMENT.md`, and `HIS_PRO_SYSTEM_OVERVIEW.md`
are older root-level documents. This `/docs` set supersedes them where they differ.

## Backend Application

| Path | Responsibility |
|---|---|
| `app/main.py` | App factory, lifespan, middleware registration, routers, health, metrics, static mount |
| `app/extensions.py` | SQLAlchemy engine, pooling, scoped session, query timing, SQLite compatibility |
| `app/models/` | SQLAlchemy entities, relationships, constraints, and indexes |
| `app/schemas/` | Pydantic request and response contracts |
| `app/routes/` | FastAPI endpoint modules grouped by hospital capability |
| `app/services/` | Domain logic, external clients, workers, uploads, audit, sessions, realtime |
| `app/middleware/` | CORS, JWT parsing, CSRF, security headers, validation, rate limiting, metrics, audit |
| `app/utils/` | Dependencies, role checks, tenant/branch scope, idempotency, pagination, validation, errors |
| `app/resources/` | Legacy resource compatibility code; not the primary FastAPI routing layer |
| `app/private_uploads/` | Development-only private upload location; not a source asset folder |
| `app/static/` | Built SPA and public static assets served by FastAPI |
| `app/static/tenants/` | Legacy/public tenant media area; private clinical files must not be placed here |

`app/routes/files_new.py` is a duplicate, unregistered route module. `app/main.py`
mounts `app/routes/files.py`; the duplicate should be removed after confirming no
deployment imports it.

## Frontends

| Path | Responsibility |
|---|---|
| `app/templates/initial frontend/src/` | Current React source: pages, components, contexts, API client, role/module rules |
| `app/templates/initial frontend/tests/` | Playwright browser tests |
| `app/templates/frontend-v2/src/` | Independent future React UI/UX source |
| `app/templates/frontend-v2/tests/` | V2 browser tests |
| `app/templates/healthsuite-pro copy/` | Separate nested working tree/submodule; not modified by this documentation sprint |

Within each React source tree:

| Folder | Responsibility |
|---|---|
| `api/` | Fetch wrapper, token refresh, CSRF, idempotency, normalized errors |
| `components/` | App shell, guards, reusable controls, landing sections |
| `context/` | Authentication and tenant-routing context |
| `hooks/` | Reusable React behavior |
| `lib/` | Facility, role, module, tenant URL, idempotency, and data mapping helpers |
| `pages/` | Route-level application screens |
| `test/` | Vitest unit/component tests |

## Database Migrations

`migrations/alembic.ini` and `migrations/env.py` configure Alembic. Revisions in
`migrations/versions/` form one linear chain. `scripts/migrate.py` bootstraps a
legacy database once, stamps the compatibility baseline, then runs `upgrade head`.
Production API containers do not call `create_all`; migration runs as a separate
deployment step.

## Generated And Runtime Files

- `app.db`, `hispro.db`, `instance/`, caches, uploads, build output, and rendered
  documentation are runtime/generated artifacts, not domain source.
- Never commit populated `.env` files, private keys, access tokens, patient data,
  receipts, chat files, or migration source exports.
- Regenerate `docs/04_DATABASE_REFERENCE.md` and `docs/05_API_REFERENCE.md` with
  `python scripts/generate_code_reference_docs.py` after model or route changes.
