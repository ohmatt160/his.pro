# HIS Pro Complete-App Roadmap

Last reviewed: 2026-07-13

This is the living implementation and release checklist for HIS Pro. It covers the work required to move from the current functional product baseline to a secure, isolated, scalable, supportable healthcare application. It also defines which work belongs in HIS Pro and which platform capabilities may be delegated to OhmattOS.

## How To Use This Roadmap

- `[x]` means the item met its full definition of done.
- `[ ]` means missing, partial, blocked, or not re-verified.
- `P0` blocks use with real patient data or a production launch.
- `P1` is required for the first production-ready release.
- `P2` is required for enterprise completeness or the stated module.
- `[HIS]` is owned by HIS Pro.
- `[OS]` is owned by OhmattOS.
- `[SHARED]` requires a versioned contract and work in both applications.

Do not tick an item merely because a route, model, or screen exists. An item is complete only when:

1. The production implementation and database migration exist.
2. Authorization, tenant isolation, validation, and failure behavior are defined.
3. Automated positive, negative, cross-tenant, and cross-branch tests pass.
4. Metrics, audit events, alerts, and operator runbooks exist where applicable.
5. It has passed a production-like staging test and has a rollback plan.

## Product Boundary

### HIS Pro Always Owns

- Clinical records, patient identity, consent, encounters, orders, prescriptions, results, invoices, and clinical audit history.
- Facility, branch, department, staff membership, role, permission, and module authorization.
- The final mapping from an authenticated person to a facility membership and branch scope.
- HIS Pro browser sessions, access/refresh tokens, session revocation, and step-up authorization.
- Verification and password-reset challenge state, including token hashes, expiry, attempts, and single-use enforcement.
- Decisions about who may view or change protected health information.
- Clinical notification intent and the minimum data needed to render it.
- Data migration validation, tenant ownership, reconciliation, and clinical import rules.

### OhmattOS May Own After Its Readiness Gate

- Durable generic job queues, retry orchestration, dead-letter handling, and worker health.
- Email, SMS, push, and webhook provider adapters, delivery queues, status callbacks, suppression, and provider failover.
- A shared enterprise identity federation broker for OIDC, SAML, and SCIM protocol handling.
- Private object-storage primitives after app isolation, encryption, malware scanning, and access grants are complete.
- Product analytics, feature flags, error aggregation, platform metrics, app subscription billing, and provider webhooks.
- Generic export orchestration, provided raw clinical datasets are not exposed outside an approved protected-data boundary.

### Shared Contract Rules

- OhmattOS never decides a HIS Pro user's clinical role, branch, or record access.
- HIS Pro never trusts a browser-supplied `app_id`, `facility_id`, role, or SSO claim without server-side binding.
- Analytics and logs contain no raw patient record, clinical note, access token, password, verification code, or provider secret.
- External side effects are emitted from a transactional outbox only after the HIS Pro transaction commits.
- Every request and callback is authenticated, encrypted in transit, tenant-bound, replay-resistant, idempotent, versioned, and observable.
- Critical hospital workflows continue when OhmattOS is unavailable. Delivery may queue, but clinical writes must not disappear.

## Current Baseline Snapshot

| Domain | Current state | Notes |
| --- | --- | --- |
| FastAPI and React application | BASELINE | Main application, routers, modules, and role-specific screens exist. |
| Core clinical workflows | PARTIAL | Patients, queue, appointments, consultations, lab, radiology, pharmacy, wards, billing, inventory, reports, alerts, referrals, and chat have baseline implementations but are not all production-complete. |
| Password authentication | PARTIAL | Access/refresh JWTs, session tracking, rotation, logout, and logout-everywhere exist. Public onboarding remains unsafe and reset tokens are process-local. |
| Email and phone verification | MISSING | No verified-email/verified-phone identity lifecycle exists. |
| MFA and passkeys | MISSING | A settings control is visible, but no production MFA implementation exists. |
| Tenant-specific OIDC/SAML/SCIM | MISSING | Neither HIS Pro nor OhmattOS currently implements these protocols. |
| Tenant and branch isolation | BLOCKED | Helpers and tests exist, but policy is not centralized and several fail-open or manual query paths remain. |
| File security | BLOCKED | Tenant uploads are currently reachable through the public static mount. |
| Database concurrency | BLOCKED | Thread-local synchronous SQLAlchemy sessions are used from async request handlers. |
| Realtime updates | PARTIAL | Authenticated tenant/branch WebSockets and a frontend bridge exist; module filtering, distributed limits, cleanup, and duplicate refetch control remain. |
| Data migration | PARTIAL | Validation/import scaffolding and settings UI exist; jobs are in-process and job ownership, resumability, rollback, and production storage remain. |
| OhmattOS integration | PARTIAL | Best-effort jobs, notifications, analytics, and log calls exist behind flags, but calls are synchronous and not outbox-driven. |
| OhmattOS platform | BLOCKED | Worker and Twilio/SendGrid adapters exist, but authenticated app isolation is not enforced consistently and identity federation is absent. |
| Automated verification | PARTIAL | On 2026-07-12 the frontend had 45 passing tests; backend had 19 passing and 1 failing audit-noise test. Full browser role/button coverage is still missing. |
| Production infrastructure | BLOCKED | SQLite and one worker are still defaults; deployment, durable jobs, object storage, metrics, backup, and restore gates are incomplete. |

## Phase 0: Security Containment

No real patient data and no production SSO should be enabled until every P0 item is complete.

- [ ] **P0 [HIS] Remove public onboarding privilege escalation.** Public registration must not accept a client-selected privileged role or attach a new account to an existing facility by guessed name/slug. Use a signed, expiring, single-purpose bootstrap transaction or an admin invitation. Existing facility collisions must return `409` without membership changes.
- [ ] **P0 [HIS] Add hostile onboarding tests.** Cover guessed facility slug/name, forged `ADMIN`, forged `DOCTOR`, replayed setup token, duplicate requests, concurrent setup, and branchless access.
- [ ] **P0 [HIS] Make all tenant uploads private.** Stop writing protected files below the public static tree. Store private objects outside the web root and serve them only through an authenticated, tenant/branch/record-authorized download endpoint or short-lived signed grant.
- [ ] **P0 [HIS] Quarantine existing public tenant files.** Inventory existing paths, migrate metadata safely, block unauthenticated direct access, and verify old URLs no longer expose content. Do not delete evidence or hospital data during migration.
- [ ] **P0 [HIS] Replace the thread-local request session model.** Use one database session per request/task. Choose either regular `def` handlers with synchronous SQLAlchemy in FastAPI's thread pool, or a full `AsyncSession`/async-driver migration. Do not combine async endpoints with blocking shared sessions.
- [ ] **P0 [HIS] Create a minimal public facility DTO.** Public workspace/profile endpoints may return only explicitly public fields and public branches. Never return internal settings, usernames, IDs, module configuration, private contact data, or branch settings.
- [ ] **P0 [HIS] Centralize tenant and branch scope.** Introduce an immutable request `TenantContext` and repository/policy layer used by every tenant table. Missing branch assignment must fail closed for non-facility admins.
- [ ] **P0 [HIS] Add database tenant defense in depth.** Add composite tenant foreign keys/constraints and PostgreSQL row-level security where practical. Test direct-ID access across tenants and branches for every resource family.
- [ ] **P0 [HIS] Bind migration jobs to their owner.** Persist `facility_id`, requester, branch scope, status, and safe error code. A facility path parameter alone must never authorize a job lookup.
- [ ] **P0 [OS] Enforce authenticated app isolation in OhmattOS.** Every service route must derive `app_id` from the validated service credential, ignore/reject caller-selected ownership, and filter reads/writes by that app. Add cross-app attack tests before HIS Pro enables any OhmattOS feature flag.
- [ ] **P0 [SHARED] Keep all OhmattOS production flags disabled until the OhmattOS readiness gate passes.** Local clinical workflows remain authoritative during this period.

## Phase 1: Security And Authorization Foundation

### Authentication And Sessions

- [ ] **P1 [HIS] Redesign the identity schema before adding SSO.** Recommended model: global `Account`, tenant-scoped `FacilityMembership`, `BranchMembership`, and `ExternalIdentity`, with every session bound to one active facility membership. Record the final choice in an ADR.
- [ ] **P1 [HIS] Migrate current `User` data without losing staff ownership or audit attribution.** Replace global username/email assumptions with explicit normalized identity and membership uniqueness rules.
- [ ] **P1 [HIS] Move password reset challenges to durable storage.** Store only a hash, purpose, account, expiry, attempts, used/revoked time, and request metadata. Responses must not reveal whether an account exists.
- [ ] **P1 [HIS] Revoke active sessions after password reset, password change, account disable, role removal, and SSO deprovisioning.** Allow an explicitly re-authenticated current session only where policy permits.
- [ ] **P1 [HIS] Upgrade password hashing policy.** Use a memory-hard password hash such as Argon2id with parameter versioning and rehash-on-login. Retain safe migration support for existing hashes.
- [ ] **P1 [HIS] Enforce password, lockout, and credential-stuffing controls.** Rate-limit by account and trusted client identity, use generic errors, progressive delay, security alerts, and safe account recovery.
- [ ] **P1 [HIS] Implement idle, absolute, and risk-based session expiry.** Make facility policy configurable within secure limits and expose active sessions with device/time metadata.
- [ ] **P1 [HIS] Stop per-request activity writes.** Cache the authenticated context per request and throttle `last_seen`/`last_active` persistence to avoid a write on every API call.
- [ ] **P1 [HIS] Fix CSRF coverage.** Verify unsafe cookie-authenticated requests even when `Origin` and `Referer` are missing, rotate CSRF tokens appropriately, and include the CSRF header on the post-refresh retry path.
- [ ] **P1 [HIS] Use exact production origins only.** Remove broad credentialed origin regexes such as wildcard Vercel subdomains.
- [ ] **P1 [HIS] Sanitize validation and error responses.** Never echo password/input values, SQL details, stack traces, file paths, provider bodies, or raw migration errors.

### Roles, Permissions, And Tenant Policy

- [ ] **P1 [HIS] Create one declarative authorization policy source.** Generate or validate backend module middleware, route dependencies, frontend guards, navigation, staff-role options, and tests from the same role/permission catalog.
- [ ] **P1 [HIS] Reconcile all current role drift.** Include intentional support for `RADIOLOGIST`, `STORE_KEEPER`, and any other real role; unknown roles must fail closed instead of becoming receptionist.
- [ ] **P1 [HIS] Replace broad role checks with named permissions.** Examples: `patient.read`, `prescription.write`, `lab.result.release`, `billing.refund`, `staff.manage`, `audit.export`.
- [ ] **P1 [HIS] Add facility and branch membership lifecycle.** Invite, accept, suspend, reactivate, transfer branch, remove, expire temporary access, and preserve audit attribution.
- [ ] **P1 [HIS] Enforce multi-branch feature rules server-side and in the UI.** `BRANCH_ADMIN`, Administration department, and branch controls remain unavailable until multi-branch is enabled and a valid branch exists.
- [ ] **P1 [HIS] Add privileged step-up authorization.** Require recent MFA for staff administration, SSO configuration, bulk exports, destructive actions, refunds, security settings, and break-glass access.
- [ ] **P1 [HIS] Implement emergency break-glass access.** Require a reason, short duration, elevated audit/alerting, post-event review, and no silent privilege persistence.
- [ ] **P1 [HIS] Add permission and isolation matrix tests.** Test every role x module x facility x branch x action combination, including disabled modules and users with no branch.

### API And Platform Security

- [ ] **P1 [HIS] Rebuild rate limiting around a shared async Redis pool.** Trust proxy headers only from configured proxies, key by normalized route template plus account/tenant, bound in-memory fallback, and fail safely on authentication routes.
- [ ] **P1 [HIS] Add request size, decompression, and timeout limits.** Protect JSON, multipart, WebSocket, report, and migration endpoints from memory and slow-client exhaustion.
- [ ] **P1 [HIS] Add a strict Content Security Policy and complete security headers.** Validate against the deployed frontend, API proxy, object storage, and SSO redirects.
- [ ] **P1 [HIS] Centralize secrets in a production secret manager.** Rotate JWT, CSRF, database, Redis, provider, SSO, and service credentials without source changes.
- [ ] **P1 [HIS] Encrypt sensitive fields and backups.** Document key hierarchy, envelope encryption, rotation, revocation, recovery, and separation by environment.
- [ ] **P1 [HIS] Add dependency, secret, SAST, DAST, and container scanning to CI.** Block release on unresolved critical findings.
- [ ] **P1 [HIS] Complete an external penetration test and remediate all P0/P1 findings.** Include tenant escape, IDOR, auth, SSO, file upload, WebSocket, migration, and business-logic testing.

## Phase 2: Verified Identity, Recovery, And MFA

### Email Verification

- [ ] **P1 [HIS] Add normalized email identity fields.** Include `email_verified_at`, verification state, pending-email change, and audit metadata.
- [ ] **P1 [HIS] Create durable email-verification challenges.** Store only a token hash with account, purpose, audience, expiry, attempt count, consumed time, and revocation time.
- [ ] **P1 [HIS] Build request, verify, resend, and email-change endpoints.** Use generic responses, single-use tokens, resend cooldowns, per-account/IP limits, and transactional state changes.
- [ ] **P1 [HIS] Gate onboarding and sensitive actions on verified email.** A pending account must not create or join an existing facility outside its signed invitation/bootstrap transaction.
- [ ] **P1 [OS] Deliver verification email.** OhmattOS queues a template request, retries providers, records delivery status, and returns no verification secret in logs or analytics.
- [ ] **P1 [SHARED] Add signed delivery receipts and idempotency.** HIS Pro owns the challenge; OhmattOS owns delivery. Provider delivery is not treated as proof that the user clicked the link.
- [ ] **P1 [HIS] Add verification tests.** Cover expiry, replay, token theft between purposes, changed email, concurrent verification, enumeration, rate limits, and OhmattOS outage.

### SMS And Phone Verification

- [ ] **P1 [HIS] Normalize phone numbers to a canonical international form.** Preserve display formatting separately and make uniqueness rules explicit.
- [ ] **P1 [HIS] Create hashed OTP challenges.** Enforce short expiry, limited attempts, resend cooldown, one active challenge per purpose, and single-use consumption.
- [ ] **P1 [HIS] Add recipient/IP/account/tenant abuse controls and budget caps.** Prevent SMS pumping and expose security/finance alerts.
- [ ] **P1 [OS] Add production SMS providers and failover.** Support the selected regional provider plus a secondary provider, delivery callbacks, sender registration, cost records, and per-destination limits.
- [ ] **P1 [HIS] Treat SMS as verification/fallback, not the strongest privileged factor.** Privileged staff should use TOTP or passkeys where available.
- [ ] **P1 [HIS] Test invalid, expired, replayed, brute-forced, rate-limited, delayed, and duplicate provider delivery cases.**

### MFA And Account Recovery

- [ ] **P1 [HIS] Implement TOTP enrollment and verification.** Encrypt seeds, require password/SSO re-authentication, show a confirmation challenge, and never log the secret.
- [ ] **P1 [HIS] Add one-time recovery codes.** Store only hashes, show once, rotate as a set, and audit use.
- [ ] **P1 [HIS] Add passkey/WebAuthn support for phishing-resistant MFA.** Support multiple named authenticators, revocation, and tenant policy.
- [ ] **P1 [HIS] Add tenant MFA policy.** Allow required MFA for all staff, privileged roles, or sensitive actions, with a secure enrollment grace period.
- [ ] **P1 [HIS] Build recovery workflows that cannot bypass tenant policy.** Require strong verification and send security notifications on factor changes.
- [ ] **P1 [HIS] Test factor theft, replay, clock skew, recovery-code reuse, device removal, admin reset, and session revocation.**

## Phase 3: Tenant-Specific Enterprise SSO

### Architecture And Handoff

- [ ] **P1 [OS] Build an enterprise identity federation service.** OhmattOS becomes the protocol broker for tenant-specific OIDC and SAML connections; it is not the HIS Pro authorization authority.
- [ ] **P1 [OS] Add a tenant/app-scoped SSO connection registry.** Store connection ID, app ID, external tenant reference, protocol, issuer/entity ID, domains, endpoints, certificate/JWKS metadata, policy, status, and rotation dates.
- [ ] **P1 [OS] Encrypt SSO client secrets, private keys, and sensitive metadata at rest.** Restrict decryption to the identity service and audit every access/change.
- [ ] **P1 [HIS] Add a tenant SSO configuration screen and policy model.** Configure discovery domains, connection reference, enabled state, JIT policy, allowed membership types, claim mapping, local-login policy, and break-glass admins.
- [ ] **P1 [SHARED] Define a one-time authorization-code handoff.** OhmattOS returns only a short-lived, audience-bound, single-use code through the browser; HIS Pro exchanges it server-to-server for verified identity claims.
- [ ] **P1 [HIS] Map external identity by immutable keys.** Use connection + issuer + subject/NameID, never email alone. HIS Pro maps the identity to an approved facility membership and issues its own tenant-bound session.
- [ ] **P1 [SHARED] Sign, encrypt, and replay-protect the handoff.** Validate audience, app, tenant, nonce, state, timestamps, code use, redirect URI, and key ID.

### OIDC

- [ ] **P1 [OS] Implement OIDC authorization code flow with PKCE.** Validate state, nonce, issuer, audience, authorized party, signature, expiry, and redirect URI.
- [ ] **P1 [OS] Support discovery and safe JWKS rotation/cache.** Reject issuer changes, unsupported algorithms, missing signatures, and stale keys according to policy.
- [ ] **P1 [OS] Support tenant-specific client credentials and provider metadata.** Never share one tenant's secret or issuer configuration with another tenant.
- [ ] **P1 [HIS] Implement safe account linking and JIT provisioning.** JIT is off by default; domain or email match alone must not silently link an existing privileged account.
- [ ] **P2 [SHARED] Add front-channel/back-channel logout only after local session revocation semantics are correct.**

### SAML

- [ ] **P1 [OS] Implement SAML service-provider metadata, login initiation, and assertion consumer service.** Support per-connection entity IDs and certificates.
- [ ] **P1 [OS] Validate signatures and protocol constraints.** Validate response/assertion signature policy, `InResponseTo`, destination, recipient, audience, issuer, conditions, time bounds, and replay ID.
- [ ] **P1 [OS] Defend against signature wrapping, XML entity attacks, algorithm downgrade, unsigned responses, and replay.** Use a proven SAML library and hardened XML parser.
- [ ] **P1 [OS] Support encrypted assertions where required and certificate rollover with expiry alerts.**
- [ ] **P1 [HIS] Add explicit claim/group-to-membership mapping with least-privilege defaults.** Unknown groups receive no clinical permission.
- [ ] **P2 [SHARED] Decide whether IdP-initiated login is needed.** If enabled, require tenant-bound connection selection and strong replay/recipient controls.

### SCIM And Lifecycle

- [ ] **P2 [OS] Implement a tenant-scoped SCIM service with rotating bearer credentials or stronger client auth.**
- [ ] **P2 [HIS] Map SCIM users/groups to invitations and facility memberships.** Provisioning does not grant a clinical role unless an approved mapping exists.
- [ ] **P2 [HIS] Deprovision immediately.** Disable memberships, revoke sessions/tokens, preserve audit attribution, and notify security operators.
- [ ] **P2 [HIS] Support reconciliation, soft delete, reactivation, and conflict reporting.**
- [ ] **P1 [SHARED] Add interoperability tests against representative enterprise IdPs.** Cover OIDC, SAML, certificate/key rotation, clock skew, JIT disabled, wrong tenant, wrong audience, replay, deprovision, and OhmattOS outage.

## Phase 4: Clinical And Operational Completeness

Each workflow is complete only when it has tenant/branch policy, pagination/search, immutable audit, valid state transitions, concurrency handling, notifications, realtime/cache behavior, and role-specific end-to-end tests.

### Patient Administration

- [ ] **P1 [HIS] Complete patient registration and search.** Add server-side search/cursor pagination, duplicate detection, configurable identifiers, emergency/unknown patient flow, and safe merge/unmerge.
- [ ] **P1 [HIS] Add patient demographics, contacts, next-of-kin, consent, privacy preferences, identifiers, allergies, problem list, and document ownership rules.**
- [ ] **P1 [HIS] Add record correction/version history.** Signed clinical content must use amendments/addenda instead of silent overwrite.
- [ ] **P1 [HIS] Complete the longitudinal timeline with source links, access policy, pagination, and export controls.**

### Reception, Appointments, And Queue

- [ ] **P1 [HIS] Complete appointment lifecycle.** Create, reschedule, cancel, no-show, check-in, recurrence where needed, collision rules, reminders, and timezone handling.
- [ ] **P1 [HIS] Complete queue state transitions and concurrency.** Prevent duplicate check-in/start/complete operations and make ownership visible.
- [ ] **P1 [HIS] Add tenant-configurable scheduling, service duration, clinic hours, holidays, and clinician availability.**

### Consultations And Medical Records

- [ ] **P1 [HIS] Complete encounter lifecycle.** Draft, signed, amended, completed, reopened-with-reason, and locked states.
- [ ] **P1 [HIS] Add structured vitals, allergies, diagnoses, procedures, history, examination, care plan, follow-up, and discharge/referral summary.**
- [ ] **P1 [HIS] Add optimistic locking/version checks so concurrent edits cannot silently overwrite clinical data.**
- [ ] **P1 [HIS] Add clinical signature attribution and timestamp integrity.**

### Laboratory And Radiology

- [ ] **P1 [HIS] Complete lab ordering, specimen collection, accessioning, processing, result entry, verification, release, correction, and cancellation.**
- [ ] **P1 [HIS] Add units, reference ranges, abnormal/critical flags, result acknowledgment, and critical-result escalation.**
- [ ] **P1 [HIS] Complete radiology ordering, scheduling, performed state, report draft/sign/amend, result acknowledgment, and image/PACS reference handling.**
- [ ] **P2 [HIS] Add external lab and imaging integration adapters with tenant-specific credentials and reconciliation.**

### Pharmacy And Medication Safety

- [ ] **P1 [HIS] Complete prescription draft/sign/cancel/dispense/partial-dispense/substitute/return workflows.**
- [ ] **P1 [HIS] Make dispensing and stock movement atomic and idempotent.** Prevent negative stock and duplicate dispense under concurrency.
- [ ] **P1 [HIS] Add allergy, duplicate therapy, interaction, contraindication, dose, and formulary warnings with auditable override reasons.**
- [ ] **P2 [HIS] Add medication administration records for inpatient workflows where in scope.**

### Wards And Nursing

- [ ] **P1 [HIS] Complete bed status, admission, transfer, observation, task, medication administration where applicable, and discharge workflows.**
- [ ] **P1 [HIS] Prevent two active patients in one bed and preserve transfer history transactionally.**
- [ ] **P1 [HIS] Add nursing observations, escalation thresholds, handover, care plan, and overdue-task visibility.**

### Patient Billing, Claims, And Cash Operations

- [ ] **P1 [HIS] Complete patient invoice lifecycle.** Draft, issue, adjust, void-with-reason, partial payment, overpayment, refund, write-off, receipt, and daily reconciliation.
- [ ] **P1 [HIS] Make payment and receipt operations idempotent and auditable.** Never confuse patient billing with OhmattOS subscription billing.
- [ ] **P1 [HIS] Complete insurance eligibility, preauthorization, claim submission, denial, resubmission, remittance, and patient-balance workflows where in scope.**
- [ ] **P2 [HIS] Add tenant-specific payment provider integration and signed webhook reconciliation.**

### Inventory, Suppliers, Referrals, And Communication

- [ ] **P1 [HIS] Complete stock ledger, adjustment reason, batch/lot, expiry, transfer, reorder, receipt, supplier, and low-stock workflows.**
- [ ] **P1 [HIS] Complete referral create/accept/reject/transfer/complete states with responsibility and clinical handoff.**
- [ ] **P1 [HIS] Restrict chat attachments to conversation participants and apply the same private-file security pipeline.**
- [ ] **P1 [HIS] Complete alerts, read state, escalation, deduplication, and action links without duplicate realtime refreshes.**

### Reports And Exports

- [ ] **P1 [HIS] Validate every report against tenant/branch scope and source totals.** Add date/timezone semantics and reconciliation tests.
- [ ] **P1 [HIS] Move large reports/exports to durable background jobs with progress, cancellation, expiry, and access-controlled downloads.**
- [ ] **P1 [HIS] Add export approval/step-up for sensitive bulk data and watermark/audit metadata where appropriate.**
- [ ] **P1 [HIS] Prevent spreadsheet formula injection and unsafe file names/content in CSV/XLSX exports.**

## Phase 5: Patient Portal And External Access

- [ ] **P2 [HIS] Define patient identity proofing and account-linking policy.** A patient portal account must not attach to a chart by name, email, or phone alone.
- [ ] **P2 [HIS] Implement patient registration/invitation, verified contact methods, MFA/recovery, and tenant-specific branding.**
- [ ] **P2 [HIS] Add appointment, result, prescription, invoice/payment, document, consent, and secure-message views with release rules.**
- [ ] **P2 [HIS] Add proxy/caregiver/dependent access with scope, expiry, revocation, and audit.**
- [ ] **P2 [HIS] Add sensitive-result delay/release and clinician acknowledgment policies where required by the facility.**
- [ ] **P2 [HIS] Add patient data-access/correction request workflows without allowing direct clinical-history mutation.**

## Phase 6: Notifications And OhmattOS Delivery

- [ ] **P1 [HIS] Introduce a transactional outbox.** Patient/staff notification intent, audit mirror, analytics, and OhmattOS jobs are inserted in the same database transaction as the triggering HIS Pro change.
- [ ] **P1 [HIS] Add an outbox dispatcher with lease, retry, idempotency, backoff, dead-letter, redrive, and metrics.**
- [ ] **P1 [OS] Make notification submission tenant/app-derived and idempotent.** Store provider reference, attempts, status history, final disposition, and safe error categories.
- [ ] **P1 [OS] Complete production email delivery.** Add verified sender/domain, HTML and text templates, bounce/complaint handling, suppression, unsubscribe policy for non-transactional messages, and provider failover.
- [ ] **P1 [OS] Complete production SMS delivery.** Add selected regional providers, delivery callbacks, sender IDs, cost/usage records, quiet-hour rules where applicable, and failover.
- [ ] **P2 [OS] Add push and in-app delivery contracts where needed.**
- [ ] **P1 [HIS] Store notification preferences and lawful/clinical overrides per tenant and recipient.** Critical care messages cannot be silently disabled where policy requires them.
- [ ] **P1 [SHARED] Add signed callbacks and reconciliation.** HIS Pro maps delivery status to the original outbox/message without trusting arbitrary IDs.
- [ ] **P1 [SHARED] Test duplicate submission, delayed callback, callback replay, provider outage, OhmattOS outage, and recovery.**

## Phase 7: Private Files And Data Migration

### File Platform

- [ ] **P1 [HIS/OS] Select the protected-file architecture.** Either HIS Pro uses private object storage directly, or OhmattOS passes the full storage readiness gate before receiving clinical files.
- [ ] **P1 [OS] Implement real private object storage.** Add app/tenant-derived keys, streaming multipart upload, encryption, checksums, versioning, lifecycle, quota, and region policy.
- [ ] **P1 [OS] Add MIME sniffing, extension/content consistency, malware quarantine, scan status, and safe image/document processing.**
- [ ] **P1 [HIS] Store file ownership and ACL in the clinical database.** Include facility, branch, patient/record/conversation, uploader, classification, retention, scan status, and deletion state.
- [ ] **P1 [SHARED] Use short-lived, purpose-bound download grants.** Re-check HIS authorization before grant creation and log every protected-file access.
- [ ] **P1 [SHARED] Test cross-tenant paths, guessed IDs, stale grants, range requests, malicious files, oversized streams, duplicate upload, and scanner outage.**

### Existing-System Data Migration

- [ ] **P1 [HIS] Replace in-memory migration jobs with durable tenant-owned jobs.** Jobs survive restart, support cancellation/resume, and cannot be read across facilities.
- [ ] **P1 [HIS] Add a quarantined staging area.** Imported source files are private, encrypted, scanned, checksummed, retained by policy, and deleted safely after completion.
- [ ] **P1 [HIS] Support schema detection and explicit mapping.** Start with CSV/XLSX and add approved vendor/standard adapters; never map columns by unsafe string replacement.
- [ ] **P1 [HIS] Build dry-run validation.** Report row-level errors, required fields, invalid dates/codes, duplicate patients, foreign-key gaps, and estimated impact before commit.
- [ ] **P1 [HIS] Add deterministic deduplication and identity reconciliation.** Require human review for ambiguous patient or staff matches.
- [ ] **P1 [HIS] Import in bounded, idempotent batches.** Track checkpoints, source row IDs, created/updated/skipped/error counts, and retry only failed work.
- [ ] **P1 [HIS] Add migration-batch rollback/compensation.** Never delete pre-existing records and preserve a complete source-to-target manifest.
- [ ] **P1 [HIS] Require admin step-up, approval, and immutable audit for validation, import, rollback, and source-file deletion.**
- [ ] **P1 [HIS] Add post-import reconciliation.** Compare counts and financial/clinical totals and require signed acceptance before closing the migration.
- [ ] **P1 [HIS] Add migration load, malformed-file, restart, rollback, and cross-tenant tests.**

## Phase 8: Performance, Scalability, And Realtime

- [ ] **P1 [HIS] Make managed PostgreSQL the only production database.** Remove SQLite production examples/defaults and require TLS, backups, point-in-time recovery, and separate staging/production instances.
- [ ] **P1 [HIS] Add all declared indexes through Alembic migrations.** Verify query plans on tenant, branch, status, date, patient, and cursor filters with production-like volume.
- [ ] **P1 [HIS] Standardize cursor pagination and server-side search.** No unbounded `.all()` or fixed first-100/200/300 data loss. Use one response contract across modules.
- [ ] **P1 [HIS] Migrate frontend server state to React Query.** Use stable keys by tenant/branch/filter, useful stale times, cancellation, optimistic updates where safe, and precise invalidation.
- [ ] **P1 [HIS] Eliminate mutation plus WebSocket duplicate reloads.** Correlate event IDs/origin and update or invalidate each query once.
- [ ] **P1 [HIS] Fix WebSocket authorization and lifecycle.** Enforce module policy, distributed per-user/tenant limits, heartbeat/timeout, bounded queues, backpressure, cleanup, and graceful deploy behavior.
- [ ] **P1 [HIS] Use shared Redis with TLS/auth and pooled async clients.** Cover cache, rate limit, realtime fanout, session heartbeat, and distributed coordination without making clinical writes dependent on Redis.
- [ ] **P1 [HIS] Add transactional work queues for slow operations.** Reports, migration, reminders, scans, imports, exports, and provider calls leave the request path.
- [ ] **P1 [HIS] Configure PostgreSQL connection pooling and capacity budgets.** Include PgBouncer or equivalent, worker count, pool math, timeouts, statement timeout, and overload behavior.
- [ ] **P1 [HIS] Define and test load targets.** Record expected concurrent staff, requests/second, WebSockets, largest tenant, import size, and latency/error SLOs before load testing.
- [ ] **P1 [HIS] Run load, soak, spike, and failure tests.** Include database/Redis/OhmattOS degradation and verify no cross-tenant cache or session leakage.

## Phase 9: Audit, Observability, Reliability, And Operations

### Audit And Security Events

- [ ] **P1 [HIS] Redesign audit writes as append-only durable events.** Audit code must not commit or roll back the business transaction independently.
- [ ] **P1 [HIS] Use a semantic action taxonomy.** Avoid duplicate generic middleware entries when a specific clinical/security action exists.
- [ ] **P1 [HIS] Record successful and denied sensitive actions.** Include login, recovery, MFA, SSO, exports, permission changes, break-glass, migration, file access, and cross-tenant attempts.
- [ ] **P1 [HIS] Protect audit integrity and retention.** Restrict access, support tenant/branch views, export safely, and detect tampering/deletion.
- [ ] **P1 [HIS] Fix the current audit test failure and add volume/ordering tests.**

### Metrics, Tracing, And Alerts

- [ ] **P1 [HIS/OS] Add OpenTelemetry-compatible traces, metrics, and structured logs.** Propagate correlation IDs across browser, HIS Pro, worker, OhmattOS, and providers.
- [ ] **P1 [HIS] Add request, query, cache, job, WebSocket, auth, tenant-denial, migration, and clinical-workflow metrics without PHI labels.**
- [ ] **P1 [OS] Add per-app provider latency/error/cost, queue depth/age, retry, dead-letter, worker lease, and callback metrics.**
- [ ] **P1 [HIS/OS] Define SLOs and alerts.** Include availability, latency, error rate, queue age, failed notifications, database saturation, backup age, certificate expiry, and suspicious access.
- [ ] **P1 [HIS/OS] Build operator dashboards and runbooks tied to each actionable alert.**

### Backup, Recovery, And Continuity

- [ ] **P1 [HIS] Automate encrypted database and object backups with retention and access controls.**
- [ ] **P1 [HIS] Define RPO/RTO per service and clinical workflow.** Document Redis/OhmattOS degradation versus PostgreSQL/object-store disaster recovery.
- [ ] **P1 [HIS] Perform and record restore drills.** Verify relational data, object references, audit history, migration jobs, and tenant isolation after restore.
- [ ] **P1 [HIS] Add graceful shutdown and zero/low-downtime migration/deploy procedures.**
- [ ] **P1 [HIS] Create incident response, breach response, key compromise, provider outage, and tenant data-export/deletion runbooks.**

## Phase 10: Interoperability And Tenant Integrations

- [ ] **P2 [HIS] Define a versioned integration architecture and terminology strategy.** Select standards/profiles and code systems appropriate to each target market with clinical/legal review.
- [ ] **P2 [HIS] Add tenant-specific integration credentials and configuration.** Encrypt secrets, scope them to facility/branch, rotate them, and test connectivity without exposing values.
- [ ] **P2 [HIS] Add healthcare API/event adapters required by customers.** Candidate families include FHIR, HL7 messages, DICOM/DICOMweb, lab devices, pharmacy, insurance, and public-health reporting.
- [ ] **P2 [HIS] Add idempotent inbound processing and durable outbound delivery.** Validate schema/signature, quarantine invalid messages, reconcile acknowledgments, and provide replay tools.
- [ ] **P2 [HIS] Add terminology/version mapping, provenance, and source-system identifiers to imported clinical data.**
- [ ] **P2 [SHARED] Use OhmattOS for generic webhook delivery/monitoring only after app isolation and signed-delivery gates pass.**

## Phase 11: Frontend, Accessibility, And Button Coverage

- [ ] **P1 [HIS] Inventory every interactive control and expected outcome.** Cover dashboard quick actions, every module page, settings, modals, tables, menus, staff portal, patient portal, and mobile navigation.
- [ ] **P1 [HIS] Replace accidental navigation/page refresh behavior.** Buttons must use explicit `type`, commands must call the intended action, and links must lead to a valid route.
- [ ] **P1 [HIS] Add Playwright end-to-end tests for every role and module.** Verify button outcome, API mutation, loading, success, failure, empty state, permission denial, and browser refresh/deep link.
- [ ] **P1 [HIS] Add branch and disabled-module UI matrices.** Hidden controls are also rejected by the backend when called directly.
- [ ] **P1 [HIS] Make selects, menus, dialogs, and command lists viewport-safe.** Add max height, scrolling, keyboard navigation, focus management, and mobile checks.
- [ ] **P1 [HIS] Meet the selected accessibility conformance target.** Complete keyboard, screen reader, focus, contrast, label, error, reduced-motion, and zoom testing.
- [ ] **P1 [HIS] Remove placeholder/static operational data and nonfunctional settings toggles.** Every visible switch must persist and enforce a real policy or be removed until implemented.
- [ ] **P1 [HIS] Clear TypeScript, ESLint, React hook, console, and network errors.** Maintain zero build/type errors and an agreed warning budget.

## Phase 12: Compliance, Privacy, And Governance

- [ ] **P1 [HIS] Complete a jurisdiction-by-jurisdiction legal and clinical compliance review with qualified counsel.** Do not treat the current Privacy Policy, Terms, or DPA as final legal approval.
- [ ] **P1 [HIS] Maintain a data inventory and classification.** Map every table, file, log, metric, backup, provider, purpose, owner, location, and retention period.
- [ ] **P1 [HIS] Complete threat models and privacy impact assessments.** Cover multi-tenancy, SSO, patient portal, migration, files, analytics, OhmattOS, and subprocessors.
- [ ] **P1 [HIS] Add consent, lawful-purpose, retention, legal-hold, correction, export, and deletion workflows appropriate to the data type and jurisdiction.** Clinical record retention must not be confused with ordinary account deletion.
- [ ] **P1 [HIS] Publish and maintain subprocessor, data-location, security, incident-notification, and business-continuity documentation.**
- [ ] **P1 [HIS] Add privileged-access review and periodic tenant access certification.**
- [ ] **P1 [HIS] Define secure support access.** No hidden impersonation; require tenant approval or break-glass, limited duration, visible indicator, and immutable audit.
- [ ] **P1 [HIS] Establish vulnerability disclosure, patch SLAs, change management, and annual security review.**

## Phase 13: Deployment, CI/CD, And Commercial Operations

- [ ] **P1 [HIS] Build reproducible production images and dependency locks.** Run as non-root, use a minimal image, include a working healthcheck, and scan/sign artifacts.
- [ ] **P1 [HIS] Fix production deployment assets.** Remove references to missing Compose files, do not expose PostgreSQL/Redis publicly, and use multiple stateless API workers.
- [ ] **P1 [HIS] Create isolated development, test, staging, and production environments.** Never share databases, storage buckets, Redis, keys, SSO apps, or provider credentials.
- [ ] **P1 [HIS] Add CI gates.** Run formatting, lint, typecheck, unit, integration, migrations, isolation, E2E, security, and image scans before merge/release.
- [ ] **P1 [HIS] Add controlled CD with migration checks, canary/rolling deploy, smoke tests, rollback, and release audit.**
- [ ] **P1 [HIS] Add tenant provisioning, suspension, data export, offboarding, and deletion workflows.**
- [ ] **P1 [OS] Keep HIS Pro SaaS subscription plans, usage, invoices, and entitlement events separate from patient invoices.**
- [ ] **P2 [SHARED] Integrate app subscription billing and feature entitlements only after signed webhooks, reconciliation, grace periods, and fail-safe behavior are complete.** A billing outage must not corrupt clinical data.
- [ ] **P1 [HIS] Build support/admin tooling with least privilege and full audit.** Include tenant health, job redrive, notification status, migration status, and safe diagnostics without raw PHI in logs.

## OhmattOS Readiness Checklist

The current OhmattOS code has useful scaffolding, a Rust worker, Twilio/SendGrid adapters, API keys, jobs, notifications, analytics, flags, storage metadata, and logs. It is not yet safe to act as a production dependency for HIS Pro because service handlers commonly accept arbitrary `app_id` values and return unscoped data, identity federation is absent, and several worker/storage controls are incomplete.

### Platform Isolation And Credentials

- [ ] **P0 [OS] Use `AuthenticatedApp.app_id` in every service handler and query.** Remove arbitrary ownership from request bodies and filter all list/detail/update/delete operations.
- [ ] **P0 [OS] Add automated cross-app isolation tests for every route family.**
- [ ] **P1 [OS] Add service-key scopes, expiry, rotation, revocation, last-used throttling, and audit.**
- [ ] **P1 [OS] Add role-based OhmattOS admin permissions and MFA.** Separate platform super-admin, support, security, billing, and read-only operations.
- [ ] **P1 [OS] Enforce per-app CORS where browser access is intentionally supported.** Service APIs should normally be server-to-server.
- [ ] **P1 [OS] Encrypt provider credentials and secrets at rest using a managed key system.**

### Worker And Delivery Safety

- [ ] **P1 [OS] Make job claiming atomic across workers.** Use database locking/leases, heartbeat, lease expiry, and ownership so two workers cannot deliver the same item concurrently.
- [ ] **P1 [OS] Add idempotency keys and unique constraints to notifications, SMS, jobs, exports, and outbound webhooks.**
- [ ] **P1 [OS] Add bounded retries, exponential backoff with jitter, dead-letter queues, redrive, cancellation, and poison-message handling.**
- [ ] **P1 [OS] Sign outbound webhooks and callbacks.** Include event ID, timestamp, key ID, replay window, and documented verification.
- [ ] **P1 [OS] Restrict generic HTTP jobs.** Prevent SSRF to private/link-local/metadata addresses, enforce allow-lists, limit methods/body/redirects, and never accept arbitrary URLs from untrusted HIS users.
- [ ] **P1 [OS] Add provider status callbacks, reconciliation, suppression, quotas, cost controls, and per-app metrics.**

### Identity Broker

- [ ] **P1 [OS] Implement the OIDC, SAML, and one-time app handoff requirements from Phase 3.**
- [ ] **P1 [OS] Add connection ownership, secret encryption, certificate/key rotation, expiry alerts, and audit.**
- [ ] **P1 [OS] Add SCIM only after app/tenant isolation and admin RBAC are complete.**
- [ ] **P1 [OS] Complete an independent identity security review before onboarding a hospital IdP.**

### Storage, Telemetry, And Production

- [ ] **P1 [OS] Replace storage metadata-only routes with private object storage and the Phase 7 controls.**
- [ ] **P1 [OS] Add Prometheus/OpenTelemetry-compatible telemetry and durable, privacy-filtered audit logs.**
- [ ] **P1 [OS] Run production PostgreSQL and Redis securely with backups, restore drills, pool limits, TLS, and no public database/cache ports.**
- [ ] **P1 [OS] Add API/worker horizontal-scaling tests, graceful shutdown, queue-age SLOs, and provider outage drills.**
- [ ] **P1 [OS] Version and publish an OpenAPI/event-schema contract plus a compatibility policy for client apps.**

## HIS Pro <-> OhmattOS Integration Contract

- [ ] **P1 [SHARED] Create a versioned contract repository or schema directory.** Include request/response JSON schemas, event types, error codes, idempotency behavior, signature format, and compatibility rules.
- [ ] **P1 [SHARED] Replace synchronous `urllib` calls in HIS Pro with a pooled async client used only by an outbox worker.**
- [ ] **P1 [SHARED] Use TLS plus rotating app credentials; prefer asymmetric request signing or a standard client-credential flow.**
- [ ] **P1 [SHARED] Derive app identity from credentials and bind facility reference through an approved app-owned mapping.** Never trust an arbitrary facility/app ID in a payload.
- [ ] **P1 [SHARED] Define a data-minimization allow-list per integration.** Explicitly list which identity/contact fields may be sent for email/SMS and which clinical fields are forbidden.
- [ ] **P1 [SHARED] Add correlation, causation, event, and idempotency IDs end to end.**
- [ ] **P1 [SHARED] Add signed callbacks, replay storage, ordering rules, and reconciliation jobs.**
- [ ] **P1 [SHARED] Add circuit breakers, timeouts, bounded concurrency, backpressure, and safe local degradation.**
- [ ] **P1 [SHARED] Run contract, isolation, replay, duplicate, outage, recovery, and load tests in CI.**

## Release Gates

### Gate A: Safe Development With Representative Data

- [ ] All Phase 0 P0 containment items are complete.
- [ ] Seed/test data contains no real patient information.
- [ ] Cross-tenant and cross-branch test suites pass for all current modules.
- [ ] Secrets and production credentials are absent from source and development fixtures.

### Gate B: Controlled Hospital Pilot

- [ ] All P1 security, identity, authorization, file, audit, backup, and deployment items required by pilot scope are complete.
- [ ] Email verification, password recovery, MFA for privileged users, and notification delivery are production-tested.
- [ ] Restore drill, incident drill, and pilot data migration rehearsal pass.
- [ ] Every pilot role and button passes browser E2E tests on desktop and mobile.
- [ ] Legal, privacy, clinical safety, and hospital acceptance sign-offs are recorded.
- [ ] External penetration-test P0/P1 findings are closed.

### Gate C: Enterprise SSO Customer

- [ ] OhmattOS app-isolation and identity-broker readiness items are complete.
- [ ] OIDC or SAML connection passes wrong-tenant, replay, signature, audience, key/certificate rotation, JIT, deprovision, and outage tests.
- [ ] HIS Pro maps external identity to an existing/invited tenant membership and issues a tenant-bound local session.
- [ ] Break-glass local admin access and SSO outage runbooks are tested.
- [ ] SCIM is enabled only if its provisioning/deprovisioning reconciliation tests pass.

### Gate D: General Production

- [ ] All launch-scope P1 items are complete; deferred P2 items are documented and not represented as available.
- [ ] Performance targets and SLOs pass load/soak/failure testing with production-like data volume.
- [ ] Production monitoring, on-call, support, backup, restore, incident, and change-management operations are active.
- [ ] No unresolved critical/high security issue or unexplained tenant-isolation test failure remains.
- [ ] Final release checklist is signed by product, engineering, security/privacy, clinical safety, and operations owners.

## Recommended Execution Order

1. **Now: Phase 0 containment.** Close onboarding takeover, public uploads, database-session isolation, public DTO leakage, tenant context, migration-job ownership, and OhmattOS app isolation.
2. **Identity foundation.** Approve the account/membership ADR, migrate the identity model, fix reset/session security, centralize permissions, and add email verification.
3. **Delivery foundation.** Add the HIS Pro outbox, harden OhmattOS workers/app isolation, then enable email/SMS providers and phone verification.
4. **Strong authentication.** Add TOTP, recovery codes, passkeys, step-up, and tenant MFA policy.
5. **Enterprise federation.** Build the OhmattOS identity broker, HIS Pro membership mapping, OIDC, SAML, and then SCIM.
6. **Clinical completion.** Close each workflow against the common isolation, audit, state-transition, pagination, realtime, and E2E definition of done.
7. **Scale and operations.** Complete PostgreSQL, Redis, jobs, private storage, observability, backups, load tests, deployment, and incident readiness.
8. **Pilot then general release.** Pass Gate B before a controlled hospital pilot, Gate C before enterprise SSO, and Gate D before general production.

## Progress Log

Add one line for each completed item or important decision. Link the pull request, migration, tests, runbook, and evidence used to tick the item.

| Date | Item | Evidence | Owner |
| --- | --- | --- | --- |
| 2026-07-13 | Roadmap created from HIS Pro and OhmattOS code/document audit | `docs/HIS_PRO_COMPLETE_APP_ROADMAP.md` | Engineering |
| 2026-07-14 | HIS Pro email/SMS payloads aligned with the OhmattOS worker contract; idempotency and channel contract tests added. Production activation remains blocked by the outbox and signed status callback items. | `app/services/ohmattos_client.py`, `tests/test_ohmattos_integration.py` | HIS/Shared |
