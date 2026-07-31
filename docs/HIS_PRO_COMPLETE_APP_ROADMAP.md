# HIS.Pro Complete-App Roadmap

**Last reviewed:** 31 July 2026

This is the tickable product and release roadmap. A checked item means the current
implementation exists and its focused automated tests have passed. It does not by
itself mean the production launch gate is approved; production evidence is tracked
in [Launch Readiness](12_LAUNCH_READINESS.md).

## Ownership Labels

- `[HIS]`: HIS.Pro owns the data, authorization, and workflow.
- `[OS]`: OhmattOS may provide a generic platform capability.
- `[SHARED]`: both products require a versioned tenant-aware contract.

## Product Boundary

HIS.Pro always owns patient/clinical/financial data, facility and branch
membership, role/permission decisions, browser sessions, identity challenge state,
clinical notification intent, migration rules, and the authoritative audit trail.

OhmattOS may provide outbound email/SMS/push/webhook adapters, generic durable jobs,
identity federation protocol brokering, private storage primitives, product
analytics/log aggregation, and subscription billing only after its own composite
`application_id + tenant_id` isolation is verified.

OhmattOS never decides who may view a HIS.Pro patient. HIS.Pro sends the immutable
hospital UUID using a short-lived tenant-permitted client-credentials token and a
transactional outbox. All feature flags stay off until their individual gates close.

## Completed Foundation

### Tenant, Branch, And URLs

- [x] **[HIS] Canonical tenant subdomains** with immutable facility mapping.
- [x] **[HIS] Existing-facility subdomain backfill** and unique database index.
- [x] **[HIS] Legacy URL preservation** with validated fixed-domain redirects.
- [x] **[HIS] Host/path mismatch failure** in frontend tenant routing.
- [x] **[HIS] Shared facility/branch scope helpers** on exposed core resources.
- [x] **[HIS] Cross-tenant and cross-branch focused tests** for current core paths.
- [ ] **P0 [HIS] Wildcard DNS/TLS and production redirect rollout evidence.**
- [ ] **P0 [HIS] Explicit branch ownership/shared policy for wards, stock, and referrals.**
- [ ] **P1 [HIS] Immutable `TenantContext`/repository policy across every tenant table.**
- [ ] **P1 [HIS] PostgreSQL row-level/composite tenant defense where practical.**

### Authentication And Sessions

- [x] **[HIS] Password login** with generic credential failure.
- [x] **[HIS] Access/refresh JWT types** with JTI, session ID, and tenant claim.
- [x] **[HIS] Durable session rows, refresh rotation, logout, and logout-everywhere.**
- [x] **[HIS] Secure cookie and double-submit CSRF flow.**
- [x] **[HIS] CSRF enforcement with missing Origin/Referer.**
- [x] **[HIS] Frontend refresh retry preserves CSRF and idempotency headers.**
- [x] **[HIS] Atomic owner + facility onboarding** with invitation-only production gate.
- [x] **[HIS] Public owner DTO/role restrictions** and hostile facility takeover protection.
- [ ] **P0 [HIS] Verified owner email before public signup.**
- [ ] **P0 [HIS] Durable hashed single-use password reset and session revocation.**
- [ ] **P1 [HIS] Administrator/privileged MFA and passkeys.**
- [ ] **P1 [HIS] Password hash policy review and rehash-on-login migration.**
- [ ] **P1 [HIS] Account/IP abuse controls and security notifications.**

### Authorization And Staff

- [x] **[HIS] Backend route role dependencies and frontend role/module guards.**
- [x] **[HIS] Billing Officer role** in staff creation, frontend access, API, and reports.
- [x] **[HIS] Branch Admin/Administration hidden and rejected until multi-branch.**
- [x] **[HIS] Required-module validation for staff roles.**
- [ ] **P0 [HIS] Reconcile Radiologist and Store Keeper across backend/UI/staff API.**
- [ ] **P1 [HIS] One declarative role/permission catalogue.**
- [ ] **P1 [HIS] Named permissions and step-up authorization for privileged actions.**
- [ ] **P1 [HIS] Membership invite/accept/suspend/transfer/remove lifecycle.**
- [ ] **P1 [HIS] Complete role x module x tenant x branch browser/API matrix.**

### Security Hardening

- [x] **[HIS] Exact credentialed CORS allow-list and strict preflight headers.**
- [x] **[HIS] Normalized errors without SQL/traceback/file path leakage.**
- [x] **[HIS] Security headers, input validation, rate limiting, timing, and metrics middleware.**
- [x] **[HIS] Production fail-fast secrets/database/Redis/signup/upload validation.**
- [x] **[HIS] Metrics header token with constant-time comparison.**
- [x] **[HIS] Private general/chat/receipt storage paths and scoped downloads.**
- [x] **[HIS] Size, extension, MIME/signature, path, and ClamAV upload checks.**
- [x] **[HIS] Broad mutation audit plus explicit transactional audit on sensitive paths.**
- [ ] **P0 [HIS] Current dependency/SAST/secret/container scan evidence and remediation.**
- [ ] **P0 [HIS] External penetration test and threat-model sign-off.**
- [ ] **P1 [HIS] KMS/secret-manager rotation and emergency revocation drill.**
- [ ] **P1 [HIS] Append-only retained audit export and anomaly alerting.**

## Core Product Workflows

### Patient And Clinical

- [x] **[HIS] Patient create with server idempotency and immediate UI lock.**
- [x] **[HIS] Patient view, timeline, edit, and archive.**
- [x] **[HIS] Appointment create/update and pagination.**
- [x] **[HIS] Queue create/transitions with active-entry invariants.**
- [x] **[HIS] Medical record create/view/edit/void; no physical deletion.**
- [x] **[HIS] Clinical order workflow timeline events.**
- [ ] **P1 [HIS] Patient duplicate candidate review and safe merge/unmerge.**
- [ ] **P1 [HIS] Signed encounter lifecycle, amendments, and optimistic locking.**
- [ ] **P1 [HIS] Consent, allergies, problem list, identifiers, and access restrictions.**
- [ ] **P2 [HIS] Approved patient self-service identity/portal.**

### Laboratory, Radiology, And Pharmacy

- [x] **[HIS] Tenant-scoped lab and medication catalogues.**
- [x] **[HIS] Idempotent lab/radiology/prescription creation.**
- [x] **[HIS] Lab completion and result concurrency safeguards.**
- [x] **[HIS] Prescription dispense under stock/prescription locks.**
- [x] **[HIS] Pharmacy stock receipt idempotency and serialization.**
- [ ] **P1 [HIS] Formal lab result verification/release/correction/critical acknowledgment.**
- [ ] **P1 [HIS] Radiology report draft/sign/amend and dedicated role completion.**
- [ ] **P1 [HIS] Lot/branch stock ledger, partial dispense, returns, substitutions.**
- [ ] **P1 [HIS] Medication allergy/interaction/dose warning governance.**

### Billing

- [x] **[HIS] Invoice line-item calculation and tenant/branch validation.**
- [x] **[HIS] Invoice and payment idempotency.**
- [x] **[HIS] Invoice row lock, positive payment, and overpayment prevention.**
- [x] **[HIS] Partial payments, paid status, private receipt upload/download.**
- [x] **[HIS] Billing Officer UI and reporting access.**
- [ ] **P1 [HIS] Refund, credit note, write-off, void-with-reason, and cashier close.**
- [ ] **P1 [HIS] Tenant-scoped insurance provider/claim redesign.**
- [ ] **P2 [HIS] Payment provider webhook and settlement reconciliation.**

### Wards, Inventory, Suppliers

- [x] **[HIS] Admission, observation, discharge, bed release, follow-up notification.**
- [x] **[HIS] Active patient/bed uniqueness, locks, and idempotency.**
- [x] **[HIS] Inventory item/list/low-stock/update/deactivate.**
- [x] **[HIS] Non-negative locked/idempotent stock adjustments.**
- [x] **[HIS] Idempotent tenant supplier creation and active-name uniqueness.**
- [ ] **P0 [HIS] Branch-owned ward beds before multi-branch inpatient launch.**
- [ ] **P1 [HIS] Stock movement ledger, reason, lot/expiry, transfer, and reconciliation.**
- [ ] **P1 [HIS] Persisted reorder/purchase order/goods receipt workflow.**

### Communication, Reports, And Files

- [x] **[HIS] Tenant alerts, role fanout, read/unread, bulk read update.**
- [x] **[HIS] Idempotent referrals and recipient alerts.**
- [x] **[HIS] Tenant participant-scoped staff chat and private scanned attachments.**
- [x] **[HIS] Idempotent chat send.**
- [x] **[HIS] Tenant/role report and audit routes with pagination.**
- [ ] **P1 [HIS] Durable large-facility alert/referral fanout jobs.**
- [ ] **P1 [HIS] Cursor pagination and asynchronous exports for high-volume data.**
- [ ] **P1 [HIS] Remove request-time legacy chat conversation repair.**

## Data Migration

- [x] **[HIS] CSV/JSON validation and source alias mapping.**
- [x] **[HIS] 25 MB and 50,000-row limits.**
- [x] **[HIS] Patients/staff/appointments/inventory/full-archive modes.**
- [x] **[HIS] Tenant/requester-bound durable background job and status.**
- [x] **[HIS] Idempotent queueing, audit, retries, leases, and worker heartbeat.**
- [ ] **P0 [HIS] Production migration rehearsal and hospital reconciliation sign-off.**
- [ ] **P1 [HIS] Encrypted migration source object storage and disposal workflow.**
- [ ] **P1 [HIS] Resumable checkpoints, reject export, and rollback/compensation plan.**
- [ ] **P2 [HIS] Native `.xlsx` parser or remove the `excel` source label.**

## Realtime, Performance, And Scale

- [x] **[HIS] Authenticated tenant/branch/user/role/module WebSocket filtering.**
- [x] **[HIS] Redis cross-replica realtime fanout and production requirement.**
- [x] **[HIS] Frontend query caching and realtime invalidation bridge.**
- [x] **[HIS] Pagination on primary lists and hot-path database indexes.**
- [x] **[HIS] Slow request/query logging and API/realtime/job metrics.**
- [x] **[HIS] Durable database jobs and transactional integration outbox.**
- [ ] **P0 [HIS] PostgreSQL/Redis/ClamAV/object storage integration and load/soak evidence.**
- [ ] **P1 [HIS] Resolve synchronous SQLAlchemy in async route workers.**
- [ ] **P1 [HIS] Cursor pagination, dashboard/report projections, bounded exports.**
- [ ] **P1 [HIS] OpenTelemetry traces and production SLO dashboards/alerts.**

## OhmattOS

- [x] **[SHARED] HIS.Pro `private_key_jwt` client-credentials design.**
- [x] **[SHARED] Short-lived tenant UUID, audience, scope, JTI token request.**
- [x] **[HIS] Secret-file private key, key ID, TTL/cache/timeout controls.**
- [x] **[HIS] Transactional tenant-scoped outbox and optional worker profile.**
- [x] **[HIS] Every production OhmattOS feature flag defaults off.**
- [ ] **P0 [OS] Composite application/tenant isolation for notifications, jobs,
  analytics, logs, storage, exports, idempotency, and delivery status.**
- [ ] **P0 [SHARED] Real key registration, tenant grants, scope matrix, revocation,
  rotation, callback signing, replay, and outage tests.**
- [ ] **P1 [OS] Production email/SMS provider adapters, delivery callbacks, suppression,
  failover, abuse/cost controls, and regional sender compliance.**
- [ ] **P1 [SHARED] Enable one capability at a time with rollback and metrics.**

## Identity Verification, MFA, And Enterprise SSO

- [ ] **P0 [HIS] Email verification challenge model and endpoints.**
- [ ] **P1 [OS] Verification email delivery; HIS.Pro retains challenge authority.**
- [ ] **P1 [HIS] Normalized verified phone and hashed OTP challenge state.**
- [ ] **P1 [OS] SMS provider delivery, callbacks, failover, pumping/budget controls.**
- [ ] **P1 [HIS] TOTP, recovery codes, passkeys, and tenant MFA policy.**
- [ ] **P1 [OS] Tenant OIDC federation broker with PKCE, issuer/JWKS validation.**
- [ ] **P1 [OS] Hardened tenant SAML service provider and certificate rollover.**
- [ ] **P1 [SHARED] Short-lived single-use authorization-code handoff to HIS.Pro.**
- [ ] **P1 [HIS] External identity mapping to approved facility membership; never email-only.**
- [ ] **P2 [OS/HIS] Tenant SCIM provisioning/deprovisioning and session revocation.**
- [ ] **P1 [HIS] Break-glass local admin and SSO outage procedure.**

## Production Infrastructure And Operations

- [x] **[HIS] Multi-stage non-root Docker image and Gunicorn/Uvicorn worker config.**
- [x] **[HIS] Reference PostgreSQL/Redis/ClamAV/migrate/API/worker Compose topology.**
- [x] **[HIS] Health includes required Redis and background worker heartbeat.**
- [ ] **P0 [HIS] Docker config/build/migration verified in CI/staging.**
- [ ] **P0 [HIS] Managed PostgreSQL and Redis HA/private networking/encryption.**
- [ ] **P0 [HIS] Private multi-host object storage and lifecycle/retention.**
- [ ] **P0 [HIS] Encrypted backup, point-in-time recovery, and timed restore drill.**
- [ ] **P0 [HIS] Wildcard DNS/TLS, WAF, WebSocket proxy, and host validation.**
- [ ] **P0 [HIS] Monitoring, on-call, incident, downtime, rollback, and key rotation drills.**
- [ ] **P1 [HIS] SBOM, signed images, vulnerability policy, and release provenance.**

## Documentation, QA, And Launch

- [x] **[HIS] Generated every-table database reference and ERD.**
- [x] **[HIS] Generated every-registered-endpoint API reference.**
- [x] **[HIS] Architecture, folder, frontend, backend/security, config/deploy docs.**
- [x] **[HIS] Business workflows and hospital operations manual source.**
- [x] **[HIS] Evidence-based launch readiness checklist.**
- [ ] **P0 [HIS] Final Word/PDF manual rendered, visually inspected, and hospital approved.**
- [ ] **P0 [HIS] Full backend/current frontend/V2 regression green.**
- [ ] **P0 [HIS] Playwright every-button/role/module/tenant/branch workflow green.**
- [ ] **P0 [HIS] Production-like migration/isolation/concurrency/load/restore suites green.**
- [ ] **P0 [HIS] Security, SRE, clinical, finance, legal/DPO, and hospital sponsor GO sign-off.**

## Launch Rule

General availability remains **NO-GO** while any P0 item is unchecked. A controlled
pilot must follow the restrictions and approvals in
[Launch Readiness](12_LAUNCH_READINESS.md); real patient data cannot be justified by
screen completeness alone.
