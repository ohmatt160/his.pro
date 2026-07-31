# Launch Readiness

## Current Decision

**General availability: NO-GO.**  
**Controlled non-production or tightly supervised pilot: conditional.**

The core product is substantial, but a healthcare launch cannot be approved from
code completion alone. Identity recovery/verification, dependency risk, production
infrastructure, restore/migration evidence, branch-domain semantics, full role
testing, and independent security review remain open.

## Completed Or Implemented Controls

| Area | Current evidence in code |
|---|---|
| Tenant routing | Canonical subdomain model, resolver, backfill migration, legacy redirects |
| Tenant authorization | Facility-scoped dependencies/routes/models and isolation tests |
| Branch authorization | Shared branch helpers and branch-aware clinical/financial models |
| Sessions | Access/refresh JWTs, durable sessions, refresh rotation, revocation |
| CSRF/CORS | Unsafe cookie checks, strict origin/header allow-lists |
| Duplicate writes | Domain and generic durable idempotency, frontend submit locks |
| Concurrency | Payment, stock, dispensing, lab, queue, admission row locks/invariants |
| Patient lifecycle | View, edit, archive; linked history retained |
| Clinical record lifecycle | View, edit, void with reason/actor/time |
| Billing role | Billing Officer creation, route/UI access, payment/receipt flow |
| Uploads | Private roots, limits, signature checks, ClamAV requirement, scoped downloads |
| Audit | Middleware plus explicit transactional business/security events |
| Background work | Durable job queue, retries, leases, heartbeat health |
| Integrations | Transactional outbox; OhmattOS defaults off |
| Deployment guardrails | Non-root image, production config validation, health and metrics token |
| Migration bootstrap | Fresh, legacy-baseline, current-schema, and interrupted local rehearsals reach Alembic head; production PostgreSQL proof remains open |
| Documentation | Generated API/database references and hospital operations package |

Implementation is necessary evidence, not sufficient production proof.

## Mandatory Go-Live Gates

| Gate | Status | Required evidence | Owner |
|---|---|---|---|
| Owner email verification | Open | Verified-email flow, resend/expiry/rate-limit tests | Identity lead |
| Durable password reset | Open | Hashed single-use store, multi-replica test, session revocation | Identity lead |
| Dependency remediation | Open | Backend/npm audit reports, reviewed exceptions, SBOM | Security lead |
| Production PostgreSQL migration | Open | Restore rehearsal, migration duration/locks, row reconciliation | Data/SRE |
| Backup and restore | Open | Successful timed restore meeting approved RPO/RTO | SRE |
| Redis/worker resilience | Open | Fail/restart/lease/heartbeat/retry tests | SRE/backend |
| ClamAV and private object storage | Open | Clean/malicious upload tests and multi-host access test | SRE/security |
| Wildcard DNS/TLS/legacy redirects | Open | Certificate, host validation, redirect matrix, reserved host test | SRE |
| Branch-domain decision | Open | Approved wards/stock/referral policy and enforced migration | Product/security |
| Role model reconciliation | Open | Radiologist/storekeeper added end-to-end or removed from routes | Product/backend |
| Browser workflow suite | Open | Every supported role/button/action at desktop/mobile viewports | QA |
| Isolation/concurrency suite on PostgreSQL | Open | Cross-tenant/branch and parallel-write results | Security/QA |
| Load and soak | Open | p95/p99, error, pool, queue, lock, WebSocket results at target load | SRE/performance |
| Observability/on-call | Open | Dashboards, alerts, runbooks, escalation test | SRE |
| Penetration test/threat model | Open | Independent findings closed or risk-accepted | Security |
| Hospital acceptance/training | Open | UAT, migration reconciliation, role/training sign-off | Hospital sponsor |
| Legal/privacy/compliance review | Open | DPA, retention, incident, processor/subprocessor approvals | Legal/DPO |

No single owner may self-approve a gate they implemented. Evidence should reference
the release candidate image digest and migration revision.

## Conditional Pilot Restrictions

A pilot may proceed only after the security lead and hospital sponsor explicitly
approve these restrictions:

- invitation-only onboarding;
- one named facility and a limited trained user cohort;
- no multi-branch inpatient bed allocation;
- no legacy insurance workflow;
- no OhmattOS feature flag unless separately approved;
- monitored business hours with immediate rollback/support;
- verified backup before data entry and daily restore-ready snapshots;
- manual account recovery by an authorized administrator until durable reset ships;
- no claim of regulatory certification;
- documented downtime forms and reconciliation owner.

Real patient data should not enter a pilot until identity recovery, backup restore,
private file storage/scanning, isolation tests, and incident response are complete.

## Pre-Release Test Matrix

### Security And Isolation

- Cross-facility ID guessing for every detail/update/delete/download endpoint.
- Cross-branch ID guessing for patients, appointments, records, orders, invoices,
  receipts, queues, admissions, files, alerts, chat, reports, and migration jobs.
- Role escalation through forged frontend payloads and direct API calls.
- Disabled module access through route and API.
- Cookie requests with missing/wrong CSRF, missing Origin, and hostile preflight headers.
- Token expiry, refresh replay, revoked session, inactive user, tenant mismatch.
- Upload extension/MIME/signature mismatch, oversized body, malware, traversal, and
  unauthorized tenant/branch download.
- Host header/subdomain confusion and legacy redirect open-redirect tests.
- Metrics/debug/OpenAPI exposure review.

### Duplicate And Concurrent Writes

- Triple-click patient, appointment, record, order, queue, invoice, payment, stock,
  admission, observation, alert, referral, supplier, radiology, and chat actions.
- Same key/same payload replay and same key/different payload/actor conflict.
- Parallel partial/full payments cannot overpay.
- Parallel dispenses cannot create negative pharmacy stock.
- Parallel stock reductions cannot create negative inventory.
- Parallel lab completion preserves one consistent result.
- Parallel admission prevents two active admissions or two patients in one bed.

### Operational Failure

- API killed during commit, after commit, and before response.
- Worker killed while holding a lease; job/outbox reclaimed only after expiry.
- Redis unavailable/restarted; API health and reconnect behavior.
- ClamAV unavailable; production upload fails closed.
- PostgreSQL failover/connection exhaustion/slow query behavior.
- Object store delay/failure and authorized retry.
- Roll forward/back of frontend with compatible API schema.

## Go-Live Checklist

- [ ] Release candidate commit/image digest frozen.
- [ ] Alembic head recorded and rehearsed on production-like backup.
- [ ] All automated suites green against PostgreSQL/Redis/ClamAV/object storage.
- [ ] Dependency/SAST/secret/container scans reviewed and signed.
- [ ] Wildcard tenant DNS/TLS and legacy redirect matrix verified.
- [ ] Production secrets generated independently in KMS/secret manager.
- [ ] Database/Redis are private, encrypted, backed up, and monitored.
- [ ] Object storage is private, encrypted, tenant-prefixed, and lifecycle managed.
- [ ] Worker heartbeat, queue age, outbox lag, error rate, p95/p99 alerts active.
- [ ] Backup restore and rollback completed within target.
- [ ] Staff role matrix and least-privilege accounts approved.
- [ ] Hospital migration validated, reconciled, and signed off.
- [ ] Downtime, incident, breach, escalation, and support runbooks rehearsed.
- [ ] UAT and clinical/financial workflow acceptance signed.
- [ ] Security, SRE, product, legal/DPO, and hospital sponsor approve GO.

## First 72 Hours

- Freeze non-emergency changes.
- Staff security/SRE/support coverage continuously during hospital operating hours.
- Review authentication failures, 403/404 spikes, 5xx, slow queries, pool waits,
  queue depth/age, WebSocket reconnects, upload scans, payments, and audit anomalies.
- Reconcile patients, invoices/payments, prescriptions/stock, lab results, and
  migration totals at agreed intervals.
- Take and verify scheduled backups.
- Use rollback criteria agreed before launch; do not improvise around data integrity.

## Sign-Off Record

| Function | Name | Decision | Date | Evidence link |
|---|---|---|---|---|
| Product owner |  |  |  |  |
| Security lead |  |  |  |  |
| SRE/platform lead |  |  |  |  |
| Clinical safety owner |  |  |  |  |
| Finance workflow owner |  |  |  |  |
| Legal/privacy officer |  |  |  |  |
| Hospital sponsor |  |  |  |  |
