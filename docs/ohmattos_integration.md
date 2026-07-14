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

## Notification Contract

HIS Pro submits both email and SMS through:

```text
POST /api/v1/notifications/send
```

Email content uses the exact shape consumed by the OhmattOS worker:

```json
{
  "app_id": "<his-pro-app-id>",
  "user_id": "patient:<opaque-patient-id>",
  "channel_type": "email",
  "template_id": null,
  "idempotency_key": "hispro:patient-notification:<notification-id>",
  "content": {
    "to": "patient@example.com",
    "subject": "Appointment reminder",
    "body": "Your appointment is tomorrow."
  }
}
```

SMS content uses:

```json
{
  "app_id": "<his-pro-app-id>",
  "user_id": "patient:<opaque-patient-id>",
  "channel_type": "sms",
  "template_id": null,
  "idempotency_key": "hispro:patient-notification:<notification-id>",
  "content": {
    "to_number": "+2348012345678",
    "body": "Your prescription is ready."
  }
}
```

HIS Pro does not send `facility_slug`, source record IDs, invoice metadata, or
other clinical context in the provider content. The app service key and
OhmattOS app scope provide the application boundary.

To create portal, SMS, and email notifications for supported patient events:

```text
HISPRO_PATIENT_NOTIFICATION_CHANNELS=PORTAL,SMS,EMAIL
```

Before setting `OHMATTOS_NOTIFICATIONS_ENABLED=true`:

1. Rotate any OhmattOS key that has appeared in source or chat history.
2. Configure the rotated key and matching HIS Pro app ID only in backend secrets.
3. Configure SendGrid and Twilio credentials in the OhmattOS worker environment.
4. Run both the OhmattOS API and worker processes.
5. Verify one synthetic email and SMS reaches `queued`, then `sent`, before using patient data.
6. Keep production delivery disabled until the HIS Pro transactional outbox and signed delivery-status callback are complete.

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
