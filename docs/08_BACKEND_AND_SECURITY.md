# Backend And Security

## Application Factory And Lifespan

`app/main.py` validates production configuration before constructing FastAPI.
Development may create/repair compatible tables; production and staging expect
`scripts/migrate.py` to complete before API startup. Lifespan starts Redis-backed
realtime, configures email, validates OhmattOS flags, and closes clients on shutdown.

The app registers 29 API router groups under `/api/v1`, plus `/health`, protected
`/metrics`, development-only debug routes, and the built SPA static mount.

## Request Pipeline

The middleware stack provides these controls:

| Control | Implementation |
|---|---|
| CORS edge handling | Exact configured origins; strict allowed request headers; credential support |
| JWT parsing | Verifies signature/type/expiry/JTI/session and attaches identity to request state |
| Module access | Rejects routes for disabled facility modules |
| Audit | Captures state-changing request context and normalized outcomes |
| CSRF | Double-submit token check for unsafe cookie-authenticated requests |
| Security headers | Browser security and cache-related response headers |
| Input validation | Rejects suspicious/oversized request patterns before route logic |
| Rate limiting | Redis-aware or explicitly permitted local coordination |
| Metrics/timing | Request metrics, `Server-Timing`, and slow request/query logging |
| Database boundary | Commits on success, rolls back on error, removes scoped session |

`ForceCORSHeadersMiddleware` is the outer edge so even early authentication errors
receive valid CORS headers. It does not reflect arbitrary preflight headers.

## Authentication

### Passwords

`User.set_password` uses Werkzeug password hashing and `check_password` verifies it.
Password inputs are validated before creation/change. Password hashes are never
returned by response schemas. Temporary staff passwords set `must_change_password`.

### JWT And Sessions

- Algorithm: HS256.
- Access token default: 1,800 seconds.
- Refresh token default: seven days.
- Claims include subject, issued/expiry time, JTI, token type, optional session ID,
  and immutable tenant ID.
- Refresh JTI is stored in `user_sessions` and rotated on every refresh.
- A revoked, expired, wrong-type, inactive, or mismatched session is rejected.
- Access and refresh tokens can be accepted through headers/cookies; refresh is
  intended to remain in an HttpOnly cookie.

Production refuses the built-in placeholder JWT secret. JWT, CSRF, onboarding,
metrics, database, Redis, and OhmattOS credentials must be independent values.

### Cookies And CSRF

Authentication cookies use `HttpOnly`, `Secure` in production, an environment-
appropriate SameSite policy, and root path. The readable CSRF cookie is compared
with `X-CSRF-Token` for unsafe browser requests. CSRF enforcement does not disappear
merely because an `Origin` or `Referer` header is absent.

### Registration And Recovery

Production onboarding is invitation-only while `PUBLIC_SIGNUP_ENABLED=false`.
The invitation is a constant-time compared header secret. Atomic `/auth/onboard`
creates the owner, facility, tenant attachment, and audit event in one transaction.

**Critical limitation:** forgot-password tokens live in a process dictionary.
They disappear on restart and are not shared across replicas. This is unsuitable
for launch and must move to a hashed, one-time, expiring database or Redis record.
Email verification is not implemented, and production validation intentionally
refuses public signup because of that gap.

## Authorization And Tenant Isolation

`role_required` loads the user from the verified token/session, confirms activity,
and compares the uppercase backend role. Tenant helpers derive the authenticated
facility; callers cannot override it with query/body slugs. Branch helpers compute
the effective branch and apply predicates to branch-aware rows.

Isolation rules:

- Use immutable `facility_id` as the security identity where available.
- Treat slugs/subdomains as routing aliases, not authority.
- Query records with facility scope before evaluating an identifier.
- Apply branch scope for non-facility administrators on branch-aware resources.
- Return `404` for cross-tenant/cross-branch identifiers where practical.
- Validate referenced users, patients, tests, medications, invoices, and files in
  the same tenant before mutation.
- Never trust frontend guards or a tenant ID supplied by a browser.

`register_tenant_hooks` adds ORM protections to reduce accidental unscoped tenant
access. Route/service filters remain required; hooks are defense in depth.

### Known Isolation Gaps

- Legacy insurance providers/claims have no tenant columns and must stay unexposed.
- Ward beds are facility-level; branch users cannot assign them until branch
  ownership exists.
- Facility-level pharmacy/inventory stock is not a branch ledger. Confirm this is
  the intended hospital policy before enabling these modules across branches.
- Referrals are department-scoped with legacy department fields and need explicit
  branch semantics for multi-branch hospitals.
- No route may expose `files_new.py`; it is an unregistered duplicate module.

## Idempotency And Concurrency

Patient registration, appointments, records, lab orders, prescriptions, queues,
invoices, payments, migration jobs, and other critical creates persist operation
keys on the domain row or durable job. `write_idempotency_records` covers remaining
retry-sensitive mutations such as stock, admissions, radiology, suppliers,
referrals, alerts, and chat.

The durable claim is unique on facility, operation, and key; it stores a payload
hash, actor, and resulting resource ID. Reusing a key with different input or user
returns `409`. Claims and mutations commit in the same transaction. Row locks and
partial unique indexes protect invoice payment, stock, dispensing, lab completion,
active queues, and active admissions under concurrent workers.

## Validation And Error Handling

Pydantic validates request types, required fields, ranges, enums, email formats,
and string lengths. Domain services validate status transitions, totals, stock,
tenant references, and enabled modules. Text fields are sanitized before storage.

Global handlers normalize failures to an error envelope and avoid returning SQL,
traceback, filesystem, or secret details. The frontend further filters unsafe
messages. Validation is layered; sanitization never replaces output encoding or
authorization.

## File Upload Security

General files, chat attachments, and receipts have separate limits and private
roots. The implementation checks:

1. declared type and extension allow-list;
2. content signature/magic bytes;
3. configured byte limit;
4. normalized generated filename/path containment;
5. ClamAV result when malware scanning is required;
6. tenant and, where applicable, branch/record ownership on download.

Files are returned with private/no-store behavior and safe download names. A local
volume is not sufficient for multi-host replicas; object storage must use private
buckets, tenant-prefixed keys, server-side encryption, short-lived signed reads,
and lifecycle/retention policy.

## Audit Logging

`audit_logs` stores actor, action, resource type/ID, facility UUID/slug, details,
IP, user agent, and timestamps. Sensitive create/update/delete workflows add
explicit audit records; middleware adds broad mutation coverage. For actions where
audit is part of the security contract, the record is flushed in the same database
transaction and failure aborts the action.

Audit logs are admin-only and paginated. Production should export them through the
outbox to append-only retained storage and alert on privilege, staff, migration,
payment, authentication, and bulk-access events.

## Rate Limiting And Abuse Controls

Rate limiting uses shared Redis coordination in production. Production validation
rejects unsafe in-memory coordination unless explicitly allowed for a controlled
single-process environment. Login, password recovery, onboarding, uploads, and
expensive reports need route-specific limits at both the API and edge/WAF.

## Realtime Security

WebSocket connections authenticate before subscription. Events carry tenant and
optional branch, role, module, user, and resource filters. Redis provides
cross-replica fanout. Events should contain identifiers and minimal status only,
not full clinical payloads. A missed event causes query refetch; it must never cause
loss of authoritative state.

## Background Jobs And Outbox

Workers claim rows with lease owner/time, increment attempts, retry after failure,
and store bounded results/errors. A Redis heartbeat is required by production
health when the background worker is enabled. The OhmattOS outbox preserves local
commit first and retries external delivery with tenant and idempotency context.

Workers must use the same tenant authorization helpers as request handlers. Job,
analytics, log, export, storage, notification, and idempotency rows require
application/tenant scope in both HIS.Pro and OhmattOS.

## Health And Metrics

`/health` checks database, Redis, and configured background-worker heartbeat; it
returns `503` when a required production dependency is unhealthy. `/metrics` is
hidden behind a constant-time header token unless deliberately public. Metrics
include request, realtime, and background-job queue state. Do not put metrics
tokens in URLs or logs.

## Security Launch Gaps

1. Implement email verification before public owner signup.
2. Replace in-memory password reset and revoke sessions after reset.
3. Add MFA/passkeys and tenant-specific OIDC/SAML/SCIM where required.
4. Resolve frontend dependency advisories and run SAST/secret/dependency scans.
5. Prove PostgreSQL migrations, backup restore, Redis failure behavior, and ClamAV.
6. Complete multi-role browser tests and external penetration testing.
7. Reconcile branch semantics for wards, stock, and referrals.
8. Move multi-host files to private object storage.

HIS.Pro currently makes no claim of HIPAA, GDPR, NDPA, ISO 27001, SOC 2, or other
certification. Compliance requires legal, organizational, infrastructure, and
operational evidence in addition to application controls.
