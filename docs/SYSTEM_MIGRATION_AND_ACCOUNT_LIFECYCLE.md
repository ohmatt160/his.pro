# HIS.Pro System Migration and Account Lifecycle Guide

This guide describes the current hospital-facing import/export workflow and the
reversible facility-account deletion process. It is an operational guide, not a
claim that every source system has a completed vendor-specific converter.

## Scope and safeguards

- Migration and export are restricted to a facility administrator and operate on
  the facility selected by the authenticated request. Backend ownership checks
  remain authoritative; hiding controls in the frontend is not authorization.
- Patient and clinical data are **Restricted**. Exports can contain PHI, staff
  data, appointments, billing, audit, pharmacy, laboratory, and operational
  records. Store transfers encrypted, limit access to named migration staff, and
  securely delete working copies after the hospital signs off.
- Import uploads are limited to 25 MiB and 50,000 rows. Supported upload formats
  are CSV and JSON. Source selections include generic CSV/JSON, OpenMRS,
  Bahmni, DHIS2, and other HIS; source selection enables field normalization,
  but does not mean every source schema or entity has a dedicated adapter.
- Current import modes are patients, staff, appointments, inventory, and full
  archive. Validate the actual export with HIS.Pro before committing to a
  production migration date. Unsupported or unrecognized fields may be ignored
  or reported as warnings.
- Imports are validated first, summarized by valid/duplicate/error rows, then
  queued as durable tenant-owned jobs. The validation ticket is short-lived and
  bound to the exact uploaded content digest, facility, source, and import mode.
  Any file or option change requires validation again.

## Hospital import runbook

1. Name a hospital migration lead and HIS.Pro administrator. Confirm the source
   system, modules, branch mapping, source timezone, patient identifiers, data
   ownership, retention obligations, and planned downtime or dual-entry period.
2. Take and verify a source-system backup. Export only data authorized for
   transfer. Preserve an encrypted, access-controlled original until the
   hospital signs off; do not send PHI through ordinary email or chat.
3. Normalize source data to CSV or JSON with stable headers and UTF-8 text.
   Remove credentials, passwords, API keys, and data not approved for transfer.
   Do not use real patient data in a test migration unless the hospital has
   approved the environment and safeguards.
4. In HIS.Pro Settings, select the closest source system and import type, upload
   the file, then choose **Validate**. Review record totals, accepted entities,
   duplicate counts, errors, and warnings with the hospital lead.
5. Correct the source file as needed and revalidate. Do not queue an import when
   there are unresolved identity conflicts, unacceptable errors, or unapproved
   mappings. Revalidation invalidates the old content-bound ticket.
6. Use a non-production tenant or agreed pilot dataset first. Queue the approved
   import once, monitor the durable migration job, and retain its job ID and
   validation summary in the change record.
7. Reconcile source and destination counts and samples for each entity; verify
   patient identity, branch ownership, appointments, stock quantities, and
   access roles. Have the hospital sign off before cutover. Keep a rollback plan
   and a clear source-of-truth decision for the dual-entry window.
8. After sign-off, securely dispose of temporary exports and migration working
   copies according to the hospital's retention policy. Record completion and
   exceptions in the migration change log.

### Current import limitations

Migration is not an unrestricted database restore. It does not promise to
preserve every source-system relationship, attachment, audit history, billing
state, clinical terminology, or vendor-specific extension. The Settings UI
currently accepts CSV/JSON uploads; it does not accept direct database
credentials or connect to a hospital's network. Staff records must never import
source passwords as usable HIS.Pro credentials. Confirm role mapping and require
users to establish credentials through the supported account process.

Large-scale imports above the stated limits, resumable partial checkpoints,
automated rollback/compensation, signed reconciliation reports, direct FHIR or
vendor APIs, attachment migration, and hospital-side acceptance automation are
not covered by this workflow. Plan these as separately tested capabilities.

## Export runbook

1. A facility administrator requests **Export facility data** in Settings.
2. HIS.Pro checks facility ownership and generates a tenant-scoped ZIP archive
   on demand. The archive contains JSON entities and a manifest with format
   version, facility identity, entity counts, and Restricted classification.
   The server does not retain a shared downloadable archive.
3. The export action is audit logged. The browser downloads the archive over the
   authenticated session; the hospital is responsible for encrypting it at
   rest, limiting recipients, recording transfer, and deleting copies when no
   longer required.
4. Verify the manifest and counts before importing to another system. An export
   is a portable data extract, not a point-in-time database backup or a promise
   of lossless round-trip restoration.

Keep archives off shared workstations and public links. Do not put export files
in tickets, email attachments, public object storage, or source control.

## Facility account deletion and recovery

### Before requesting deletion

Export any records the hospital is entitled and required to retain. Resolve
outstanding invoices, legal holds, data-processing obligations, and patient
record retention requirements. Deletion is facility-wide, not a staff-user
deactivation control.

### Request and retention period

Only a facility administrator may request deletion. The UI requires the current
password and exact facility name. On acceptance, the facility is disabled
immediately, active sessions are revoked, and a purge job is scheduled. The
default retention period is 30 days, configurable from 1 to 90 days with
`ACCOUNT_DELETION_RETENTION_DAYS`.

The administrator receives a private recovery link by email. The secret is
stored server-side only as a SHA-256 hash; it is placed in the URL fragment so
it is not sent in the initial HTTP request, and the recovery page removes it
from browser history before submitting it. The link is single-use and expires
when the retention period ends. Recovery reactivates the facility and cancels
the queued purge while requiring staff to sign in again.

If the recovery email is not delivered, a production deletion request fails
closed rather than silently scheduling an unrecoverable deletion. Administrators
should verify the configured public HTTPS origin and email delivery before
offering account deletion to hospitals.

### What happens at purge

After the retention deadline, a durable background job removes tenant-owned
application records and changes the facility to a minimal inactive tombstone so
the original tenant slug is not immediately reused. Private tenant upload files
are removed by a separate retryable job, created in the same database
transaction as the tombstone. A failed file cleanup is visible as a failed or
retrying background job and must be operationally monitored.

Deletion does not override statutory retention duties, legal holds, independent
backups, external notification providers, payment processors, or copies already
downloaded by the hospital. Backup expiry and third-party deletion require
separate documented retention controls. Do not describe the account as erased
from every backup or processor unless those systems have confirmed the purge.

### Recovery and support

During the retention window, use only the emailed recovery link. Never ask the
hospital to send its recovery token to support. Support should verify the
requester through the established identity-verification process and inspect
job/audit status without exposing tokens or patient data. After the deadline,
the recovery route rejects the expired token; restoration then requires an
authorized restore or re-onboarding process, not a claim that the old account
can still be recovered.

## Operator checklist

- Confirm `PUBLIC_APP_ORIGIN` is the correct public HTTPS frontend origin in
  staging/production and email delivery is healthy.
- Confirm background workers are running and monitor queued, retrying, and
  failed migration, facility purge, and storage purge jobs.
- Confirm database backups, object/file storage backups, and restore drills have
  their own retention and tenant-isolation controls.
- Run a synthetic migration and export in staging; verify tenant A cannot export
  or mutate tenant B's records and files.
- Rehearse deletion, link recovery, expiry, database purge, and failed/retried
  storage cleanup before enabling hospital self-service account deletion.
- Have the hospital approve the mapping, reconciliation report, cutover window,
  and retention/disposal plan in writing.
