# Implementation Notes And Roadmap

## Executive Assessment

HIS.Pro has a broad, coherent FastAPI/React domain surface and meaningful recent
hardening: tenant-aware routes, canonical subdomains, branch filters, durable
sessions, CSRF, upload scanning, idempotency, row locking, pagination, workers,
outbox, metrics, and audit. The main risk is not missing screens; it is proving
security and operability under production identity, infrastructure, concurrency,
failure, and recovery conditions.

## Code Quality Review

### Strengths

- Routes are grouped by domain with Pydantic contracts and reusable services.
- Tenant and branch helpers reduce repeated authorization logic.
- Critical retry-sensitive writes have server-side idempotency, not only disabled buttons.
- Database indexes cover many tenant/status/date hot paths.
- Clinical records are voided and patients are archived rather than silently erased.
- Billing and pharmacy use locks and invariants around money/stock.
- Background jobs and integration delivery are durable database records.
- Production config fails closed for weak secrets, SQLite, Redis, signup, and upload scanning.
- Both current and V2 frontends share clear role/module/tenant routing concepts.
- Generated API/database docs reduce long-term drift.

### Maintainability Concerns

1. `BaseModel.save/update/delete` commits internally. This makes multi-record
   transactions harder to reason about and can separate audit/idempotency from the
   business write. Prefer explicit unit-of-work commits at route/service boundaries.
2. Many `async def` routes call synchronous SQLAlchemy. Convert them to synchronous
   handlers or adopt an async engine/session after load testing and migration design.
3. `facility_id`, `facility_slug`, `branch_id`, and legacy `department_id` coexist.
   Define one canonical scope object and phase out security decisions based on slugs.
4. Current and V2 frontends duplicate API/domain mapping code. Share a versioned
   internal package only after behavior is stable and tested.
5. Root-level legacy docs and comments still describe Flask/Hugging Face/SQLite.
   This documentation set and the updated README should become authoritative.
6. `app/routes/files_new.py` is dead duplicate code and creates review ambiguity.
7. Some services import Flask-era compatibility patterns (`Model.query`, direct
   commits), increasing hidden transaction behavior.

### Performance Concerns

- Report aggregation and a few legacy `.all()` paths can grow without bound.
- Alert/referral fanout runs in the request and should become a durable job for
  large staff populations.
- Staff chat legacy-conversation repair scans nullable participant keys and should
  be completed by migration rather than request-time fallback.
- List endpoints often return arrays without total/cursor metadata. Pagination
  limits memory, but clients cannot navigate exact totals consistently.
- Offset pagination becomes expensive at deep pages; high-volume timelines, audit,
  chat, and events should use `(created_at, id)` cursors.
- Facility dashboard/report aggregates should move to projections/materialized
  views when production volume proves the need.

### Security Concerns

- In-memory password reset is a critical launch blocker.
- Owner email is not verified; public signup must remain disabled.
- No MFA/passkeys or tenant-specific OIDC/SAML/SCIM.
- Insurance models lack tenant scope and must remain unexposed.
- Ward beds and stock do not have complete branch ownership semantics.
- Upload storage is local-volume based in the reference topology.
- OpenAPI remains available in production at `/api/v1/openapi.json` even while UI
  docs are disabled; decide and enforce edge policy.
- Dependency vulnerability evidence is incomplete, especially V2 npm advisories.
- Formal retention, legal hold, export, erasure, and key management procedures are
  outside the current code.

## Known Limitations

### Launch Blockers

- Durable, hashed, one-use password reset with session revocation is not implemented.
- Verified owner email is not enforced; email/SMS verification is absent.
- Production PostgreSQL migration, backup restore, rollback, Redis, ClamAV, object
  storage, wildcard DNS/TLS, and worker evidence has not been recorded.
- Full browser tests for every supported role/button/workflow are not complete.
- Current dependency advisories have not been triaged and remediated.
- No independent penetration test or launch threat-model sign-off.
- Multi-branch wards cannot safely allocate branch-owned beds.

### Partial Features

- OhmattOS notification, analytics, logs, jobs, and storage integrations are
  feature-flagged and must remain off until both systems enforce tenant scope.
- Data migration accepts CSV/JSON; native Excel parsing is not implemented despite
  an `excel` source label.
- Inventory reorder reports success but does not create purchase orders.
- Pharmacy stock is one facility row per medication, not a lot/branch ledger.
- Insurance models exist but have no tenant-safe API workflow.
- Public hospital profile exists; patient self-service/portal identity does not.
- Patient notification records exist, but verified email/SMS delivery depends on
  unfinished identity/contact/platform work.
- Metrics are JSON operational metrics, not a complete Prometheus/OpenTelemetry stack.
- `RADIOLOGIST` and `STORE_KEEPER` route permissions are not matched by staff creation/UI.

### Not Implemented

- SAML 2.0, tenant OIDC discovery/configuration, SCIM provisioning.
- MFA, passkeys/WebAuthn, recovery codes, device/risk policies.
- Formal refund, credit note, insurance claim, and reconciliation accounting.
- Native mobile applications and offline-first clinical synchronization.
- Purchase orders, goods-received notes, supplier payments, batch stock ledger.
- AI assistant, clinical model, or automated diagnosis.
- Certified interoperability profiles such as FHIR/HL7 integrations.

## Recommended Roadmap

### Phase 0: Release Freeze And Evidence

- Freeze unrelated feature work.
- Create a release candidate and immutable dependency lock evidence.
- Run all backend, frontend, Playwright, migration, isolation, and concurrency tests.
- Build/deploy the exact Docker images in staging.

### Phase 1: Identity Completion

- Add email verification records with hashed tokens, expiry, single use, resend
  limits, generic responses, and audit.
- Replace password reset with durable hashed tokens and revoke every user session
  after reset.
- Add MFA/passkeys for administrators and optionally privileged clinical/financial roles.
- Add an identity-provider configuration model per tenant, metadata/certificate
  rotation, safe domain discovery, and break-glass local admin.
- Implement OIDC first; add SAML only for hospital customers that require it; add
  SCIM after account linking/deprovisioning rules are stable.

### Phase 2: Branch And Inventory Domain Completion

- Add explicit branch ownership/shared-policy fields for ward beds, inventory,
  pharmacy locations/lots, and referrals.
- Backfill and reconcile existing facility-level records before enforcing non-null scope.
- Add stock movement, lot, expiry, adjustment reason, and reconciliation ledgers.
- Expose or remove `RADIOLOGIST`/`STORE_KEEPER` consistently across backend and UI.

### Phase 3: Production Operations

- Adopt managed PostgreSQL/Redis and private encrypted object storage.
- Add OpenTelemetry traces/metrics/log correlation and actionable SLO alerts.
- Run recurring backup restores, failover, worker crash, Redis loss, and deployment rollback drills.
- Add WAF/edge rate limits and centralized append-only audit export.
- Establish incident, vulnerability, key rotation, access review, and retention processes.

### Phase 4: Scale And Data Products

- Convert blocking database endpoints or move to async SQLAlchemy deliberately.
- Add cursor pagination and asynchronous exports.
- Build aggregate projections for dashboard/report hot paths.
- Move large notification/referral/alert fanout to durable jobs.
- Partition/archive high-volume audit, event, notification, and idempotency history
  according to approved retention policy.

### Phase 5: Platform And Interoperability

- Enable OhmattOS capabilities one at a time after contract/isolation tests.
- Add signed webhooks, replay windows, dead-letter operations, and tenant delivery metrics.
- Add FHIR/HL7 only against named customer requirements and tested profiles.
- Consider AI only after clinical safety, privacy, model governance, human review,
  and non-diagnostic product boundaries are approved.

## Recommended Ownership

| Area | Accountable owner |
|---|---|
| Tenant/branch authorization | Security lead + backend lead |
| Identity/email/MFA/SSO | Identity lead |
| Clinical workflow safety | Clinical product owner + hospital safety officer |
| Billing integrity | Finance product owner + hospital finance representative |
| Migration/reconciliation | Data migration lead + hospital data owner |
| Infrastructure/backup/restore | Platform/SRE lead |
| Dependency and application security | Security lead |
| Go/no-go | Product owner, security lead, SRE, and hospital sponsor jointly |
