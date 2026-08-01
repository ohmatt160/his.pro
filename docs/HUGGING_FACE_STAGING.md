# Hugging Face Staging Deployment

Hugging Face Spaces is supported as a single-container staging environment for
synthetic test data. It is not the approved production topology for patient data.
The production topology remains separate web, migration, worker, PostgreSQL,
Redis, malware-scanning, and private-object-storage services.

## Container Startup

The Docker image starts `scripts/start_service.py`. The supervisor can:

1. apply Alembic migrations before accepting traffic;
2. start the durable background-job worker inside the Space container;
3. start Gunicorn on port `7860`;
4. stop the deployment if either Gunicorn or the bundled worker fails; and
5. forward termination signals for a graceful shutdown.

These capabilities are opt-in so Docker Compose and horizontally scaled
deployments can continue using dedicated migration and worker services.

## Required Space Variables

Configure these under **Settings > Variables and secrets > Variables** for
`Ohmatt160/his.pro-staging`:

| Variable | Staging value |
|---|---|
| `APP_ENV` | `production` |
| `FRONTEND_URL` | The exact HTTPS frontend origin |
| `ALLOWED_ORIGINS` | Comma-separated exact HTTPS frontend origins; no localhost, HTTP, or wildcard |
| `COOKIE_SECURE` | `true` |
| `ALLOW_SQLITE_IN_PRODUCTION` | `false` |
| `REALTIME_REDIS_REQUIRED` | `true` |
| `ALLOW_IN_MEMORY_COORDINATION` | `false` |
| `BACKGROUND_JOBS_INLINE` | `false` |
| `BACKGROUND_JOB_WORKER_ENABLED` | `true` |
| `RUN_MIGRATIONS_ON_START` | `true` |
| `BUNDLED_BACKGROUND_WORKER` | `true` |
| `PUBLIC_SIGNUP_ENABLED` | `false` |
| `METRICS_PUBLIC` | `false` |

For a frontend served by this same Space, include
`https://ohmatt160-his-pro-staging.hf.space` in `ALLOWED_ORIGINS`. Add Vercel or
custom frontend origins only when they are actually used.

## Required Space Secrets

Configure these as **Secrets**, never Variables and never committed files:

| Secret | Requirement |
|---|---|
| `DATABASE_URL` | Production-style PostgreSQL URL with TLS required by the provider |
| `REDIS_URL` | Managed Redis TLS URL, normally `rediss://...`; it must be reachable from the Space |
| `JWT_SECRET_KEY` | Independent random value of at least 32 characters |
| `CSRF_SECRET_KEY` | Independent random value, different from the JWT secret |
| `METRICS_TOKEN` | Independent random value of at least 32 characters |
| `ONBOARDING_TOKEN` | Independent invitation token, different from all signing secrets |

Generate each application secret independently. Run this command once per
secret and place the result directly into the Hugging Face secret field:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not paste secret values into tickets, logs, chat, screenshots, or Git.

## Verification

After the Space rebuilds, startup logs should show migration completion, the
background worker starting, Gunicorn starting, and Redis connecting. The health
endpoint should return HTTP 200 with this shape:

```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "background_worker": "connected"
}
```

A missing worker heartbeat, Redis failure, or database failure correctly returns
HTTP 503. Do not bypass this by enabling in-memory coordination in production.

## Staging Limitations

- Use synthetic data only.
- Local `/data` storage is ephemeral unless persistent Space storage is enabled.
- File uploads must remain unavailable unless a reachable ClamAV service and
  private persistent storage are configured.
- A single bundled worker is suitable for staging, not horizontal production.
- Migration and rollback must still be rehearsed against a production-like backup.
- General availability remains subject to `12_LAUNCH_READINESS.md`.
