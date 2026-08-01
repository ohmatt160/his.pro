# HIS Pro Tenant URL Migration Runbook

Status: implementation verified; production DNS, TLS, deployment, and smoke tests remain.

## Goal

Move every existing facility to:

```text
https://<canonical-subdomain>.<tenant-base-domain>
```

without changing the facility's account, users, branches, records, or immutable
tenant identity. Existing URLs remain compatibility entry points and redirect to
the canonical hostname after server-side facility validation.

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

## Legacy URL Behavior

The current frontend and V2 support legacy path forms on the configured product
frontend hostnames. Examples:

```text
https://his.pro/login/sunrise-medical
https://his.pro/dashboard/sunrise-medical/patients
```

After validating the facility through the backend, they redirect to:

```text
https://sunrise-medical.his.pro/login
https://sunrise-medical.his.pro/dashboard/patients
```

Valid existing path-based facilities receive `308 Permanent Redirect`. Unknown facilities
receive a non-cacheable `307` to the generic workspace login instead of a `404`.
This prevents a temporary lookup failure or typo from becoming a permanently
cached negative redirect.

The redirect destination is constructed only under the validated
`TENANT_BASE_DOMAIN` suffix. The request `Host` header cannot select or alter the
destination. The backend resolves the immutable facility row while returning
only its slug and canonical routing label. The handler verifies both values,
route segments, and HTTP method. Internal routing parameters are stripped. This
prevents open redirects, tenant substitution, and configuration leakage.

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

1. Take a verified database backup and rehearse restore.
2. Deploy the backend code and run `alembic upgrade head` before serving the new frontend.
3. Verify every active facility has one unique, valid canonical subdomain.
4. Configure wildcard DNS and TLS for the tenant domain on the frontend platform,
   for example `*.his.pro`.
5. Configure `TENANT_BASE_DOMAIN=his.pro`, `PUBLIC_APP_ORIGIN`, and the private
   backend proxy credentials in the Vercel project. The Vite build receives the
   validated tenant suffix from this same server-side setting.
6. Deploy the current frontend and V2 artifacts as applicable.
7. Smoke-test login, refresh, logout, dashboard, branch routes, patient portal,
   WebSocket authorization, and a cross-tenant denial on canonical hostnames.
8. Test representative legacy path URLs and verify the exact canonical `Location` header.
9. Keep the old domains and path routes online as long-lived redirect entry points.
10. Monitor redirect status, resolver latency, lookup failures, loops, and tenant
    mismatch denials without placing PHI in logs or metric labels.

The generated `his-pro.vercel.app` project hostname is a deployment entry point,
not a wildcard domain owned by HIS.Pro. A hostname such as
`sunrise-medical.his-pro.vercel.app` must not be launched unless the hosting
provider explicitly assigns that wildcard. Use a custom wildcard domain for
production tenant URLs.

## Rollback

- Do not reverse or rewrite facility IDs.
- Keep the additive canonical column during application rollback.
- Disable legacy rewrite rules if they misroute, while leaving old paths served by
  the previous frontend release.
- Correct routing data with an audited migration; never silently reassign a
  canonical hostname from one facility UUID to another.
