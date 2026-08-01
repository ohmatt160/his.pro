# Configuration, Installation, And Deployment

## Prerequisites

- Python 3.11
- Node.js compatible with Vite 8 and `npm ci`
- PostgreSQL 16 for production
- Redis 7.4 for production coordination/realtime
- ClamAV 1.5 for required upload scanning
- Optional wildcard DNS/TLS when `TENANT_BASE_DOMAIN` is configured
- Docker/Compose for the reference container topology

SQLite is supported for development and tests only. Production validation rejects
SQLite unless an explicit unsafe override is set; that override is not an approved
launch configuration.

## Local Backend Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\migrate.py
python run.py
```

`run.py`/the FastAPI app serves the API on the configured local port (normally
`8000`). API docs are available in non-production at `/docs`; the application
OpenAPI document is `/api/v1/openapi.json`.

Use a local `.env` with development-only values. Never reuse production secrets or
import real patient data into a developer workstation.

## Local Frontend Installation

Current frontend:

```powershell
Set-Location 'app\templates\initial frontend'
npm ci
npm run dev
```

Future V2 frontend:

```powershell
Set-Location 'app\templates\frontend-v2'
npm ci
npm run dev
```

Set `VITE_API_BASE_URL` only when the API is not served under the same origin. The
backend CORS allow-list must include the exact development origin.

## Build And Test

```powershell
python -m compileall -q app scripts migrations tests
python -m unittest discover -s tests

Set-Location 'app\templates\initial frontend'
npm test
npm run build

Set-Location '..\frontend-v2'
npm test
npm run build
```

Run Playwright role/workflow tests against the selected build and production-like
API. Package vulnerability scans, secret scans, and static analysis are separate
release evidence and must not be inferred from a successful build.

## Environment Variables

`.env.production.example` is the canonical template. Important groups are below.

### Application And Secrets

| Variable | Purpose |
|---|---|
| `APP_ENV` | `production`, `staging`, or development behavior |
| `PORT` | HTTP listen port; container default `7860` |
| `WEB_CONCURRENCY` | Gunicorn API worker count per container |
| `JWT_SECRET_KEY` | JWT signing secret, at least 32 random characters |
| `CSRF_SECRET_KEY` | Independent CSRF signing secret |
| `PUBLIC_SIGNUP_ENABLED` | Must remain `false` until owner email verification exists |
| `ONBOARDING_TOKEN` | Independent invitation secret while signup is closed |
| `COOKIE_SECURE` | Must be `true` behind production HTTPS |
| `JWT_ACCESS_TOKEN_EXPIRES` | Access-token seconds; default 1,800 |
| `JWT_REFRESH_TOKEN_EXPIRES` | Refresh-token seconds; default seven days |

### Origins And Tenant Hosts

| Variable | Purpose |
|---|---|
| `FRONTEND_URL` | Primary exact frontend origin |
| `ALLOWED_ORIGINS` | Comma-separated exact credentialed origins |
| `ALLOWED_ORIGIN_REGEX` | Optional tightly reviewed tenant origin pattern |
| `TENANT_BASE_DOMAIN` | Optional DNS suffix for canonical facility hosts; no scheme or path |
| `PUBLIC_APP_ORIGIN` | Optional exact HTTPS origin for generic product/login pages; Vercel system URL is the fallback |

Never use `*` for credentialed production CORS. Without a custom domain, tenant
workspaces use the Vercel origin with a slug path such as
`/sunrise-medical/login`. Tenant identity still comes from the immutable facility
record and every protected API query remains tenant-scoped. If a wildcard domain
is later enabled, CORS needs a bounded tenant-origin policy and reserved-subdomain
protection. The Vercel build injects the optional `TENANT_BASE_DOMAIN` into the
browser bundle so generated links use one validated value.

### Database And Pooling

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL |
| `DB_POOL_SIZE` | Persistent connections per API process; default 20 |
| `DB_MAX_OVERFLOW` | Temporary connections per process; default 40 |
| `DB_POOL_TIMEOUT` | Pool wait timeout seconds; default 10 |
| `DB_POOL_RECYCLE` | Connection recycle seconds; default 3,600 |
| `DB_CONNECT_TIMEOUT` | PostgreSQL connect timeout |
| `DB_APPLICATION_NAME` | Database connection attribution |
| `SLOW_QUERY_SECONDS` | Query warning threshold; default 0.5 |
| `ALLOW_SQLITE_IN_PRODUCTION` | Emergency compatibility only; approved value is `false` |

Pool sizing is per worker and per replica. Ensure
`replicas * workers * (pool + overflow)` cannot exhaust PostgreSQL. Start smaller,
measure wait time, and place a connection pooler in front of PostgreSQL when needed.

### Redis, Realtime, And Workers

| Variable | Purpose |
|---|---|
| `REDIS_URL` | Authenticated Redis URL |
| `REALTIME_REDIS_REQUIRED` | Fail production startup/health without Redis |
| `ALLOW_IN_MEMORY_COORDINATION` | Must remain `false` for multiple replicas |
| `BACKGROUND_JOBS_INLINE` | Must remain `false` in production |
| `BACKGROUND_JOB_WORKER_ENABLED` | Enables worker heartbeat health requirement |
| `INTEGRATION_OUTBOX_BATCH_SIZE` | Events claimed per outbox cycle |
| `INTEGRATION_OUTBOX_LEASE_SECONDS` | Outbox claim lease |
| `INTEGRATION_OUTBOX_POLL_SECONDS` | Outbox poll interval |

### Files And Malware Scanning

| Variable | Purpose |
|---|---|
| `FILE_UPLOAD_DIR` | Private general upload root |
| `CHAT_UPLOAD_DIR` | Private chat attachment root |
| `RECEIPT_UPLOAD_DIR` | Private payment receipt root |
| `MAX_UPLOAD_BYTES` | General upload maximum |
| `MAX_CHAT_FILE_BYTES` | Chat attachment maximum |
| `MAX_RECEIPT_BYTES` | Receipt maximum |
| `MALWARE_SCAN_REQUIRED` | Must be `true` for launch |
| `CLAMAV_HOST`, `CLAMAV_PORT` | ClamAV daemon endpoint |

### Operations

| Variable | Purpose |
|---|---|
| `METRICS_PUBLIC` | Approved value is `false` |
| `METRICS_TOKEN` | Independent header token for `/metrics` |
| `SLOW_REQUEST_MS` | Slow HTTP request warning threshold |
| `RATE_LIMIT_NAMESPACE` | Deployment-specific shared rate-limit key namespace |

### OhmattOS

Keep all `OHMATTOS_*_ENABLED` flags false until the production client key,
permitted tenant UUIDs, audience, scopes, outbox worker, and OhmattOS composite
tenant isolation are verified. Full variables and token contract are documented in
[OhmattOS Integration](ohmattos_integration.md).

## Database Migration

For a new or legacy database:

```powershell
python scripts\migrate.py
```

For an empty database, the script applies the full Alembic chain and then adds
the small set of older module tables that predate Alembic coverage. For a
recognized pre-Alembic HIS.Pro database, it verifies the core legacy tables,
stamps the compatibility baseline, applies every later migration and backfill,
then performs conservative additive schema repair. It refuses to stamp an
unrecognized database. Before production:

1. restore a recent production-like backup into staging;
2. run migration and record duration/locks;
3. reconcile row counts and constraints;
4. test application rollback strategy;
5. take and verify a production backup;
6. run the one-shot migration before API/worker rollout.

Do not let every API replica race to migrate at startup.

## Docker Reference Topology

`docker-compose.yml` defines:

- `db`: private PostgreSQL 16 service with persistent data;
- `redis`: private authenticated Redis 7.4 service;
- `clamav`: private ClamAV service;
- `migrate`: one-shot schema migration;
- `backend`: non-root, read-only API container with private upload volume;
- `background-worker`: durable job processor;
- `integration-outbox-worker`: optional `ohmattos` profile.

The API image uses Python 3.11 slim, a build-stage virtual environment, UID/GID
10001, read-only-friendly data paths, Gunicorn/Uvicorn workers, graceful timeout,
and max-request recycling. Database, Redis, and ClamAV ports are not exposed to the
public host by the reference file.

```powershell
docker compose config
docker compose build
docker compose run --rm migrate
docker compose up -d db redis clamav backend background-worker
```

Enable the outbox worker only after configuration verification:

```powershell
docker compose --profile ohmattos up -d integration-outbox-worker
```

## Reverse Proxy, DNS, And TLS

1. Provision an A/AAAA or CNAME target for the edge/load balancer.
2. Add wildcard DNS for `*.<tenant-base-domain>` and the root/product domains.
3. Issue/rotate a wildcard or automated per-host certificate.
4. Forward the original host and trusted client IP headers.
5. Redirect HTTP to HTTPS and legacy HIS.Pro paths to canonical tenant hosts.
6. Apply request/body limits, connection limits, WAF rules, and WebSocket upgrade.
7. Reserve `www`, `api`, `admin`, `status`, and other platform subdomains.

The API must resolve the host to a registered active facility before accepting a
tenant request. A host header alone cannot grant tenant authority.

## Scaling Guidance

- Scale API and workers independently.
- Use PostgreSQL/Redis managed high availability and encrypted backups.
- Keep API replicas stateless; move files to private object storage for multi-host.
- Tune Gunicorn workers based on blocking database time and CPU, not a fixed formula.
- Bound every list/export and send large imports/reports/fanout to workers.
- Instrument p50/p95/p99 latency, error rate, pool waits, slow queries, lock waits,
  queue depth/age, job retries, WebSocket connections, and outbox delivery lag.
- Use idempotency keys across proxy/client retries and preserve them end-to-end.
- Load test tenant isolation as well as throughput.

## Backup And Disaster Recovery

Minimum production evidence:

- encrypted automatic PostgreSQL backups and point-in-time recovery;
- encrypted versioned object/file backups with tenant retention rules;
- Redis treated as reconstructible coordination state unless durability is required;
- documented RPO/RTO approved by hospital leadership;
- quarterly restore exercise with recorded timings and integrity checks;
- key/secrets recovery and emergency rotation procedure;
- downtime mode and reconciliation process for clinical operations.

## Deployment Gate

This repository's Docker tooling was not validated on the current workstation
because Docker is unavailable there. A CI or staging host must successfully run
`docker compose config`, image build, migration, health, worker heartbeat, upload
scan, WebSocket, backup, restore, and rollback exercises before release.
