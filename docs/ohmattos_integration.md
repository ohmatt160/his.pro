# HIS Pro + OhmattOS Integration

HIS Pro treats OhmattOS as an optional platform dependency. Clinical writes
remain local and authoritative when OhmattOS is disabled or unavailable.

## Trust Model

Ordinary HIS Pro calls use OAuth 2.0 client credentials with
`private_key_jwt` client authentication.

1. HIS Pro resolves and authorizes the user, hospital, and branch locally.
2. The hospital's immutable `Facility.id` becomes the requested `tenant_id`.
3. HIS Pro signs a 60-second client assertion with its private key.
4. OhmattOS authenticates the client and checks that the requested tenant and
   scopes exist in its application-tenant allow-list.
5. OhmattOS issues a tenant-scoped access token for no more than five minutes.
6. OhmattOS derives application and tenant ownership from that verified token.

HIS Pro never sends `app_id` or `tenant_id` inside a service payload. OAuth
Token Exchange is reserved for a future delegation flow carrying an existing
user or service identity; it is not used for this machine-to-machine flow.

## Client Assertion

The assertion uses `RS256` and contains:

```json
{
  "iss": "hispro-production",
  "sub": "hispro-production",
  "aud": "https://ohmattos.fly.dev/api/v1/auth/token",
  "iat": 0,
  "nbf": 0,
  "exp": 0,
  "jti": "<unique-assertion-id>"
}
```

OhmattOS must validate the exact token-endpoint audience, `iss == sub ==
client_id`, registered `kid`, algorithm allow-list, maximum assertion age, and
single use of `jti`.

Each service client also has an explicit tenant grant. A valid HIS Pro signing
key cannot mint a token for a hospital until OhmattOS has an active
`service_client_tenants` row for that client and hospital.

## Token Request

```text
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
client_id=hispro-production
client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer
client_assertion=<signed-jwt>
tenant_id=<immutable-hospital-uuid>
scope=notifications:send
audience=ohmattos-api
```

The token response must echo the external hospital UUID as `tenant_id` (or
`external_tenant_id`) and return `expires_in <= 300`. HIS Pro rejects a tenant
mismatch, a longer lifetime, a non-Bearer token, redirects, and an off-origin
token endpoint.

OhmattOS signs the access JWT with `typ=at+jwt`, publishes its public key at
`/api/v1/.well-known/jwks.json`, and includes `application_id`, the external
hospital `tenant_id`, the internal `tenant_ref`, exact scope, audience, and a
unique token `jti`.

## Runtime Configuration

Required when `OHMATTOS_ENABLED=true`:

- `OHMATTOS_URL`
- `OHMATTOS_TOKEN_URL`
- `OHMATTOS_CLIENT_ID`
- `OHMATTOS_CLIENT_PRIVATE_KEY_FILE`
- `OHMATTOS_CLIENT_KEY_ID`
- `OHMATTOS_CLIENT_SIGNING_ALG`
- `OHMATTOS_TOKEN_AUDIENCE`
- `OHMATTOS_API_AUDIENCE`

The private key must be mounted from a secret manager or backed by a KMS/HSM.
The current client supports a mounted PEM. Moving signing behind a KMS adapter
is required where non-exportable keys are available. `OHMATTOS_API_KEY` is
rejected in production.

Optional mTLS settings:

- `OHMATTOS_MTLS_CERT_FILE`
- `OHMATTOS_MTLS_KEY_FILE`
- `OHMATTOS_CA_BUNDLE`

Both mTLS identity files must be configured together. mTLS constrains access
token use, but it does not make a stolen client-signing key harmless.

## Transactional Outbox

External work is written to `integration_outbox` in the same database
transaction as the hospital action. FastAPI request workers never wait for
OhmattOS.

Run one or more independent dispatchers:

```bash
python scripts/process_integration_outbox.py
```

PostgreSQL dispatchers claim rows with `FOR UPDATE SKIP LOCKED`, a bounded
lease, exponential retry with jitter, and dead-letter state. A crash after
remote acceptance may replay a row, so OhmattOS idempotency remains mandatory.

The unique local boundary is:

```text
(destination, facility_id, idempotency_key)
```

Thus two hospitals may use the same business key without sharing a record.
The same key is forwarded to OhmattOS for notifications, jobs, analytics, and
logs.

## Notification Payload

```json
{
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

The access token supplies ownership. The payload contains no application ID,
tenant ID, facility slug, branch ID, source record metadata, IP address, or
user agent.

## OhmattOS Enforcement Gate

Do not enable production flags until OhmattOS:

- Authenticates `private_key_jwt` and prevents assertion `jti` replay.
- Checks `(application_id, external_tenant_id, scope, active)` before issuance.
- Signs five-minute, audience-restricted access tokens.
- Derives application and tenant context exclusively from verified tokens.
- Constrains notifications, jobs, analytics, logs, storage, exports, delivery
  status, and idempotency by `(application_id, tenant_id)`.
- Applies equivalent isolation inside workers and object-storage keys.
- Supports key rotation, emergency revocation, issuance auditing, anomaly
  detection, and per-client/per-tenant limits.
- Passes cross-application, cross-tenant, replay, duplicate, outage, and
  concurrent-worker tests.

Register or revoke the HIS Pro client grant for a hospital with:

```text
POST   /api/v1/apps/{app_id}/service-clients/hispro-production/tenants/{facility_uuid}
DELETE /api/v1/apps/{app_id}/service-clients/hispro-production/tenants/{facility_uuid}
```

Keep `OHMATTOS_JOBS_ENABLED=false` until HIS Pro submits a job type the
OhmattOS worker actually supports. A local Python task name is not a remotely
executable job.

## Clinical Boundary

HIS Pro retains patient records, clinical authorization, hospital and branch
RBAC, audit authority, patient billing, and migration rules. OhmattOS may
provide delivery and platform primitives, but it never decides whether a user
may access a clinical record.
