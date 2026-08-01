# HIS Pro Tenant URL Migration Runbook

Status: path-based Vercel mode implemented; custom-domain DNS/TLS rollout remains.

## Goal

Keep every existing facility reachable before a custom domain exists at:

```text
https://<vercel-project>.vercel.app/<facility-slug>/login
```

Then, after wildcard DNS/TLS is available, move generated links to:

```text
https://<canonical-subdomain>.<tenant-base-domain>
```

without changing the facility's account, users, branches, records, or immutable
tenant identity. Existing path URLs remain compatibility entry points throughout
the migration.

## Identity Invariants

- `Facility.id` remains the tenant identifier. It is never replaced by a hostname.
- `Facility.canonical_subdomain` is an additive, unique, immutable routing label.
- Existing facility, user, branch, clinical, billing, and audit rows are not copied
  or deleted by the URL migration.
- A hostname selects a candidate tenant; authenticated tenant and branch policy
  still authorizes every protected request.
- Reserved, malformed, inactive, unknown, and identity-mismatched tenants fail
  closed and never receive a permanent redirect.

## Existing Facility Backfill

Alembic revision `c42e7a9d5f11` adds `facilities.canonical_subdomain`, backfills all
existing rows, enforces non-null values, and creates a unique index. A normal,
DNS-safe facility slug is retained. Reserved or oversized slugs receive a stable
label derived from the immutable facility UUID.

The application compatibility sync also performs an additive backfill for legacy
SQLite development databases. Production deployments must use Alembic.

## Path URL Behavior

The current frontend and V2 support tenant paths on the Vercel project hostname.
Examples:

```text
https://his-pro.vercel.app/sunrise-medical/login
https://his-pro.vercel.app/dashboard/sunrise-medical/patients
```

These routes are served by the SPA and resolve the facility through the backend.
They do not depend on `TENANT_BASE_DOMAIN`. After a custom wildcard is configured,
newly generated links use:

```text
https://sunrise-medical.his.pro/login
https://sunrise-medical.his.pro/dashboard/patients
```

Path links remain available rather than redirecting to an unsupported nested
`vercel.app` hostname. Unknown facilities show the unavailable-workspace state.
The backend resolves the immutable facility row, while authenticated operations
verify the token's facility and branch scope. A route slug is never sufficient
authorization for data access.

## Session Behavior

Accounts and data remain intact. A user may need to sign in once on the new
hostname because secure host-only cookies must not be shared across every
`*.his.pro` tenant. Do not set authentication cookies with `Domain=.his.pro` and
do not place access or refresh tokens in redirect URLs.

If seamless session migration becomes necessary, implement a server-generated,
single-use authorization code with a very short expiry, fixed destination tenant,
audience and nonce checks, and server-to-server exchange. It must not be a bearer
token embedded in the URL.

## Production Rollout

### Phase 1: No Custom Domain

1. Take a verified database backup and rehearse restore.
2. Deploy the backend code and run `alembic upgrade head` before serving the new frontend.
3. Verify every active facility has one unique, valid canonical subdomain.
4. Leave `TENANT_BASE_DOMAIN` unset and deploy the current frontend or V2 artifact.
5. Ensure Vercel system environment variables are exposed, or set the exact
   `PUBLIC_APP_ORIGIN` explicitly.
6. Smoke-test login, refresh, logout, dashboard, branch routes, patient portal,
   WebSocket authorization, and cross-tenant denial using path URLs.

### Phase 2: Custom Wildcard Domain

1. Acquire the domain and configure wildcard DNS and TLS on the frontend platform.
2. Set `TENANT_BASE_DOMAIN` to that verified suffix and set `PUBLIC_APP_ORIGIN` to
   the generic product origin.
3. Deploy and test canonical login, dashboard, branches, cookies, CORS, WebSockets,
   and representative path compatibility links.
4. Announce the new links while keeping path routes available during migration.
5. Monitor resolver latency, lookup failures, loops, and tenant mismatch denials
   without placing PHI in logs or metric labels.

The generated `his-pro.vercel.app` project hostname is a deployment entry point,
not a wildcard domain owned by HIS.Pro. A hostname such as
`sunrise-medical.his-pro.vercel.app` must not be launched unless the hosting
provider explicitly assigns that wildcard. Until a custom wildcard exists, use
`his-pro.vercel.app/sunrise-medical/login`.

## Rollback

- Do not reverse or rewrite facility IDs.
- Keep the additive canonical column during application rollback.
- Keep path routes served by the SPA if custom-domain routing is rolled back.
- Correct routing data with an audited migration; never silently reassign a
  canonical hostname from one facility UUID to another.
