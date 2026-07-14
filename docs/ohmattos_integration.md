# HIS Pro + OhmattOS Integration

HIS Pro treats OhmattOS as an optional platform dependency. Clinical workflows
must continue locally when OhmattOS is disabled or unavailable.

## Environment Flags

- `OHMATTOS_ENABLED`
- `OHMATTOS_URL`
- `OHMATTOS_API_KEY`
- `OHMATTOS_APP_ID`
- `OHMATTOS_TIMEOUT_SECONDS`
- `OHMATTOS_JOBS_ENABLED`
- `OHMATTOS_NOTIFICATIONS_ENABLED`
- `OHMATTOS_ANALYTICS_ENABLED`
- `OHMATTOS_LOGS_ENABLED`
- `OHMATTOS_STORAGE_ENABLED`

All feature flags default to off.

## Current Integration

- Background jobs are executed locally and mirrored to OhmattOS as sanitized job
  metadata when `OHMATTOS_JOBS_ENABLED=true`.
- Patient SMS/email notification requests are queued locally and optionally sent
  to OhmattOS when `OHMATTOS_NOTIFICATIONS_ENABLED=true`.
- Sensitive API actions can be mirrored as sanitized analytics events when
  `OHMATTOS_ANALYTICS_ENABLED=true`.
- Unhandled request exceptions can be reported to OhmattOS logs when
  `OHMATTOS_LOGS_ENABLED=true`.

## Clinical Boundary

HIS Pro keeps patient records, clinical orders, branch isolation, hospital RBAC,
clinical audit, patient invoices, and patient data migration rules.

OhmattOS should own platform primitives: durable workers, provider integrations,
notifications, object storage, app analytics, error aggregation, app billing,
feature flags, rate-limit rules, and platform observability.

## Safety Rules

- Do not send raw patient records to OhmattOS analytics/logs.
- Do not rely on OhmattOS for clinical authorization decisions.
- Do not let OhmattOS execute arbitrary HIS Pro Python jobs until a signed
  callback/worker contract exists.
- Keep local fallback behavior for critical hospital operations.
