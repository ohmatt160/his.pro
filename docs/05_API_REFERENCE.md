# API Reference

> Generated from the registered FastAPI routes and OpenAPI schemas by
> `scripts/generate_code_reference_docs.py`. Example values are illustrative;
> schemas and access requirements come from the running application.

## Protocol Conventions

- Base path: `/api/v1` except `/health`.
- Authentication: bearer access token or the secure access-token cookie.
- Browser cookie mutations also require the double-submit CSRF header.
- Mutation clients should send one stable `Idempotency-Key` per user action.
- Validation errors use HTTP `422`; business validation generally uses `400`.
- Tenant or branch mismatches generally return `404` to avoid record disclosure.
- Rate limiting may return `429`; unexpected failures use the normalized error envelope.

## Error Envelope

```json
{"error":{"message":"Request could not be completed","code":400,"status":400}}
```

## Endpoints

## Alerts

### `GET /api/v1/alerts`

**Purpose:** Get Alerts. Paginated list of alerts for user's facility

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `is_read` | query | no | `boolean` or `null` |
| `alert_type` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `AlertResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/alerts" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "alert_type": "<alert_type>",
    "title": "<title>",
    "message": "<message>",
    "recipient_id": "00000000-0000-0000-0000-000000000000",
    "recipient_name": "<recipient_name>",
    "is_read": true,
    "read_at": "<read_at>",
    "expires_at": "<expires_at>",
    "created_at": "<created_at>"
  }
]
```

### `POST /api/v1/alerts`

**Purpose:** Create Alert. Create a new alert

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `AlertCreate`.

**Success:** HTTP `201`; response schema `AlertResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/alerts" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"facility_slug":"example-hospital","alert_type":"<alert_type>","title":"<title>","message":"<message>","recipient_id":"00000000-0000-0000-0000-000000000000","expires_at":"<expires_at>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "alert_type": "<alert_type>",
  "title": "<title>",
  "message": "<message>",
  "recipient_id": "00000000-0000-0000-0000-000000000000",
  "recipient_name": "<recipient_name>",
  "is_read": true,
  "read_at": "<read_at>",
  "expires_at": "<expires_at>",
  "created_at": "<created_at>"
}
```

### `PUT /api/v1/alerts/actions/mark-all-read`

**Purpose:** Mark All As Read. Mark all visible unread alerts as read.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/alerts/actions/mark-all-read" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `POST /api/v1/alerts/role`

**Purpose:** Create Role Alert. Create the same alert for every active staff member with a role.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `RoleAlertCreate`.

**Success:** HTTP `201`; response schema Array of `AlertResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/alerts/role" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"alert_type":"<alert_type>","title":"<title>","message":"<message>","recipient_role":"<recipient_role>","expires_at":"<expires_at>"}'
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "alert_type": "<alert_type>",
    "title": "<title>",
    "message": "<message>",
    "recipient_id": "00000000-0000-0000-0000-000000000000",
    "recipient_name": "<recipient_name>",
    "is_read": true,
    "read_at": "<read_at>",
    "expires_at": "<expires_at>",
    "created_at": "<created_at>"
  }
]
```

### `DELETE /api/v1/alerts/{alert_id}`

**Purpose:** Delete Alert. Delete alert

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `alert_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/alerts/{alert_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/alerts/{alert_id}`

**Purpose:** Get Alert. Get alert by ID

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `alert_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `AlertResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/alerts/{alert_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "alert_type": "<alert_type>",
  "title": "<title>",
  "message": "<message>",
  "recipient_id": "00000000-0000-0000-0000-000000000000",
  "recipient_name": "<recipient_name>",
  "is_read": true,
  "read_at": "<read_at>",
  "expires_at": "<expires_at>",
  "created_at": "<created_at>"
}
```

### `PUT /api/v1/alerts/{alert_id}`

**Purpose:** Update Alert. Update alert

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `alert_id` | path | yes | `string` |

**Request body:** `application/json` using `AlertUpdate`.

**Success:** HTTP `200`; response schema `AlertResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/alerts/{alert_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"title":"<title>","message":"<message>","alert_type":"<alert_type>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "alert_type": "<alert_type>",
  "title": "<title>",
  "message": "<message>",
  "recipient_id": "00000000-0000-0000-0000-000000000000",
  "recipient_name": "<recipient_name>",
  "is_read": true,
  "read_at": "<read_at>",
  "expires_at": "<expires_at>",
  "created_at": "<created_at>"
}
```

### `PUT /api/v1/alerts/{alert_id}/read`

**Purpose:** Mark As Read. Mark alert as read

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `alert_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `AlertResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/alerts/{alert_id}/read" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "alert_type": "<alert_type>",
  "title": "<title>",
  "message": "<message>",
  "recipient_id": "00000000-0000-0000-0000-000000000000",
  "recipient_name": "<recipient_name>",
  "is_read": true,
  "read_at": "<read_at>",
  "expires_at": "<expires_at>",
  "created_at": "<created_at>"
}
```

### `PUT /api/v1/alerts/{alert_id}/unread`

**Purpose:** Mark As Unread. Mark alert as unread

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `alert_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `AlertResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/alerts/{alert_id}/unread" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "alert_type": "<alert_type>",
  "title": "<title>",
  "message": "<message>",
  "recipient_id": "00000000-0000-0000-0000-000000000000",
  "recipient_name": "<recipient_name>",
  "is_read": true,
  "read_at": "<read_at>",
  "expires_at": "<expires_at>",
  "created_at": "<created_at>"
}
```

## Appointments

### `GET /api/v1/appointments`

**Purpose:** Get Appointments. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |
| `patient_id` | query | no | `string` or `null` |
| `doctor_id` | query | no | `string` or `null` |
| `department_id` | query | no | `string` or `null` |
| `branch_id` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `AppointmentResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/appointments" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "patient_id": "00000000-0000-0000-0000-000000000000",
    "doctor_id": "00000000-0000-0000-0000-000000000000",
    "appointment_date": "2026-07-31",
    "scheduled_time": "<scheduled_time>",
    "duration_minutes": 1,
    "status": "<status>",
    "reason": "<reason>",
    "notes": "<notes>",
    "facility_slug": "example-hospital",
    "created_at": "<created_at>",
    "updated_at": "2026-07-31"
  }
]
```

### `POST /api/v1/appointments`

**Purpose:** Create Appointment. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `AppointmentCreate`.

**Success:** HTTP `201`; response schema `AppointmentResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/appointments" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"patient_id":"00000000-0000-0000-0000-000000000000","doctor_id":"00000000-0000-0000-0000-000000000000","appointment_date":"2026-07-31","duration_minutes":30,"reason":"<reason>","notes":"<notes>","department_id":"00000000-0000-0000-0000-000000000000","branch_id":"00000000-0000-0000-0000-000000000000"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "doctor_id": "00000000-0000-0000-0000-000000000000",
  "appointment_date": "2026-07-31",
  "scheduled_time": "<scheduled_time>",
  "duration_minutes": 1,
  "status": "<status>",
  "reason": "<reason>",
  "notes": "<notes>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `DELETE /api/v1/appointments/{appointment_id}`

**Purpose:** Cancel Appointment. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `appointment_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/appointments/{appointment_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/appointments/{appointment_id}`

**Purpose:** Get Appointment. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `appointment_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `AppointmentResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/appointments/{appointment_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "doctor_id": "00000000-0000-0000-0000-000000000000",
  "appointment_date": "2026-07-31",
  "scheduled_time": "<scheduled_time>",
  "duration_minutes": 1,
  "status": "<status>",
  "reason": "<reason>",
  "notes": "<notes>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `PUT /api/v1/appointments/{appointment_id}`

**Purpose:** Update Appointment. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `appointment_id` | path | yes | `string` |

**Request body:** `application/json` using `AppointmentUpdate`.

**Success:** HTTP `200`; response schema `AppointmentResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/appointments/{appointment_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"status":"<status>","appointment_date":"2026-07-31","duration_minutes":5,"reason":"<reason>","notes":"<notes>","department_id":"00000000-0000-0000-0000-000000000000","branch_id":"00000000-0000-0000-0000-000000000000"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "doctor_id": "00000000-0000-0000-0000-000000000000",
  "appointment_date": "2026-07-31",
  "scheduled_time": "<scheduled_time>",
  "duration_minutes": 1,
  "status": "<status>",
  "reason": "<reason>",
  "notes": "<notes>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

## Audit Logs

### `GET /api/v1/audit-logs`

**Purpose:** Get Audit Logs. Get audit logs (admin only)

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `action` | query | no | `string` or `null` |
| `resource_type` | query | no | `string` or `null` |
| `user_id` | query | no | `string` or `null` |
| `start_date` | query | no | `string` or `null` |
| `end_date` | query | no | `string` or `null` |
| `limit` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `AuditLogResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/audit-logs" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "user_id": "00000000-0000-0000-0000-000000000000",
    "action": "<action>",
    "resource_type": "<resource_type>",
    "resource_id": "00000000-0000-0000-0000-000000000000",
    "details": {},
    "ip_address": "<ip_address>",
    "user_agent": "<user_agent>",
    "facility_slug": "example-hospital",
    "created_at": "<created_at>"
  }
]
```

### `GET /api/v1/audit-logs/{log_id}`

**Purpose:** Get Audit Log. Get single audit log entry (admin only)

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `log_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `AuditLogResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/audit-logs/{log_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "user_id": "00000000-0000-0000-0000-000000000000",
  "action": "<action>",
  "resource_type": "<resource_type>",
  "resource_id": "00000000-0000-0000-0000-000000000000",
  "details": {},
  "ip_address": "<ip_address>",
  "user_agent": "<user_agent>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>"
}
```

## Authentication

### `POST /api/v1/auth/ensure`

**Purpose:** Ensure User. Create a setup user if it does not exist, or authenticate the existing user.

**Access:** Public.

**Request body:** `application/json` using `UserRegister`.

**Success:** HTTP `200`; response schema `TokenResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/auth/ensure" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"username":"<username>","email":"staff@example.invalid","password":"<strong-password>","role":"<role>","first_name":"<first_name>","last_name":"<last_name>","facility_slug":"example-hospital"}'
```

**Example response shape**

```json
{
  "access_token": "<access_token>",
  "refresh_token": "<refresh_token>",
  "token_type": "bearer"
}
```

### `POST /api/v1/auth/login`

**Purpose:** Login User. Login and get access token

**Access:** Public.

**Request body:** `application/json` using `UserLogin`.

**Success:** HTTP `200`; response schema `TokenResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/auth/login" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"username":"<username>","password":"<strong-password>"}'
```

**Example response shape**

```json
{
  "access_token": "<access_token>",
  "refresh_token": "<refresh_token>",
  "token_type": "bearer"
}
```

### `POST /api/v1/auth/logout`

**Purpose:** Logout User. Logout user by adding token to blocklist

**Access:** Public.

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/auth/logout" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `POST /api/v1/auth/logout-everywhere`

**Purpose:** Logout Everywhere. No additional route description is declared.

**Access:** Public.

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/auth/logout-everywhere" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `POST /api/v1/auth/onboard`

**Purpose:** Onboard Facility. Atomically create a facility and its first administrator.

**Access:** Public.

**Request body:** `application/json` using `FacilityOnboardingCreate`.

**Success:** HTTP `200`; response schema `FacilityOnboardingResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/auth/onboard" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"owner":{"username":"<username>","email":"staff@example.invalid","password":"<strong-password>","first_name":"<first_name>","last_name":"<last_name>"},"facility":{"name":"<name>","type":"<type>","country":"<country>","address":"<address>","phone":"+2348000000000","email":"<email>","modules":["<modules>"],"settings":{}}}'
```

**Example response shape**

```json
{
  "access_token": "<access_token>",
  "refresh_token": "<refresh_token>",
  "token_type": "bearer",
  "facility": {
    "id": "00000000-0000-0000-0000-000000000000",
    "tenant_id": "00000000-0000-0000-0000-000000000000",
    "canonical_subdomain": "<canonical_subdomain>",
    "name": "<name>",
    "slug": "example-hospital",
    "type": "<type>",
    "country": "<country>",
    "address": "<address>",
    "phone": "+2348000000000",
    "email": "<email>",
    "modules": [
      "<modules>"
    ],
    "settings": {}
  }
}
```

### `POST /api/v1/auth/refresh`

**Purpose:** Refresh Token. Refresh access token using refresh token

**Access:** Public.

**Request body:** none.

**Success:** HTTP `200`; response schema `TokenResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/auth/refresh" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "access_token": "<access_token>",
  "refresh_token": "<refresh_token>",
  "token_type": "bearer"
}
```

### `POST /api/v1/auth/register`

**Purpose:** Register User. Register a new user

**Access:** Public.

**Request body:** `application/json` using `UserRegister`.

**Success:** HTTP `201`; response schema `UserResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/auth/register" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"username":"<username>","email":"staff@example.invalid","password":"<strong-password>","role":"<role>","first_name":"<first_name>","last_name":"<last_name>","facility_slug":"example-hospital"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "username": "<username>",
  "email": "<email>",
  "role": "<role>",
  "first_name": "<first_name>",
  "last_name": "<last_name>",
  "facility_slug": "example-hospital",
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `GET /api/v1/auth/sessions`

**Purpose:** List Sessions. No additional route description is declared.

**Access:** Public.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `UserSessionResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/auth/sessions"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "user_agent": "<user_agent>",
    "ip_address": "<ip_address>",
    "last_seen_at": "<last_seen_at>",
    "expires_at": "<expires_at>",
    "is_current": true
  }
]
```

### `POST /api/v1/auth/verify`

**Purpose:** Verify Current Session. No additional route description is declared.

**Access:** Public.

**Request body:** none.

**Success:** HTTP `200`; response schema `UserResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/auth/verify" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "username": "<username>",
  "email": "<email>",
  "role": "<role>",
  "first_name": "<first_name>",
  "last_name": "<last_name>",
  "facility_slug": "example-hospital",
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

## Billing

### `GET /api/v1/billing/invoices`

**Purpose:** Get Invoices. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |
| `patient_id` | query | no | `string` or `null` |
| `status` | query | no | `string` or `null` |
| `branch_id` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `InvoiceResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/billing/invoices" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "patient_id": "00000000-0000-0000-0000-000000000000",
    "invoice_number": "<invoice_number>",
    "amount": 1.0,
    "paid_amount": 1.0,
    "balance": 1.0,
    "status": "<status>",
    "due_date": "2026-07-31",
    "paid_date": "2026-07-31",
    "notes": "<notes>",
    "facility_slug": "example-hospital",
    "created_at": "<created_at>"
  }
]
```

### `POST /api/v1/billing/invoices`

**Purpose:** Create Invoice. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `InvoiceCreate`.

**Success:** HTTP `201`; response schema `InvoiceResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/billing/invoices" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"patient_id":"00000000-0000-0000-0000-000000000000","amount":1.0,"due_date":"2026-07-31","notes":"<notes>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "invoice_number": "<invoice_number>",
  "amount": 1.0,
  "paid_amount": 1.0,
  "balance": 1.0,
  "status": "<status>",
  "due_date": "2026-07-31",
  "paid_date": "2026-07-31",
  "notes": "<notes>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>"
}
```

### `GET /api/v1/billing/invoices/{invoice_id}`

**Purpose:** Get Invoice. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `invoice_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `InvoiceResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/billing/invoices/{invoice_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "invoice_number": "<invoice_number>",
  "amount": 1.0,
  "paid_amount": 1.0,
  "balance": 1.0,
  "status": "<status>",
  "due_date": "2026-07-31",
  "paid_date": "2026-07-31",
  "notes": "<notes>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>"
}
```

### `PUT /api/v1/billing/invoices/{invoice_id}`

**Purpose:** Update Invoice. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `invoice_id` | path | yes | `string` |

**Request body:** `application/json` using `InvoiceUpdate`.

**Success:** HTTP `200`; response schema `InvoiceResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/billing/invoices/{invoice_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"status":"<status>","due_date":"2026-07-31","notes":"<notes>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "invoice_number": "<invoice_number>",
  "amount": 1.0,
  "paid_amount": 1.0,
  "balance": 1.0,
  "status": "<status>",
  "due_date": "2026-07-31",
  "paid_date": "2026-07-31",
  "notes": "<notes>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>"
}
```

### `GET /api/v1/billing/invoices/{invoice_id}/payments`

**Purpose:** Get Invoice Payments. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `invoice_id` | path | yes | `string` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `PaymentResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/billing/invoices/{invoice_id}/payments" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "invoice_id": "00000000-0000-0000-0000-000000000000",
    "amount": 1.0,
    "payment_method": "<payment_method>",
    "reference": "<reference>",
    "notes": "<notes>",
    "processed_by": "<processed_by>",
    "created_at": "<created_at>"
  }
]
```

### `POST /api/v1/billing/invoices/{invoice_id}/payments`

**Purpose:** Add Payment. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `invoice_id` | path | yes | `string` |
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `PaymentCreate`.

**Success:** HTTP `201`; response schema `PaymentResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/billing/invoices/{invoice_id}/payments" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"amount":1.0,"payment_method":"<payment_method>","reference":"<reference>","notes":"<notes>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "invoice_id": "00000000-0000-0000-0000-000000000000",
  "amount": 1.0,
  "payment_method": "<payment_method>",
  "reference": "<reference>",
  "notes": "<notes>",
  "processed_by": "<processed_by>",
  "created_at": "<created_at>"
}
```

### `GET /api/v1/billing/payments/{payment_id}/receipt`

**Purpose:** Download Payment Receipt. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `payment_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/billing/payments/{payment_id}/receipt" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `POST /api/v1/billing/payments/{payment_id}/receipt`

**Purpose:** Upload Payment Receipt. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `payment_id` | path | yes | `string` |

**Request body:** `multipart/form-data` using `Body_upload_payment_receipt_api_v1_billing_payments__payment_id__receipt_post`.

**Success:** HTTP `200`; response schema `PaymentResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/billing/payments/{payment_id}/receipt" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "invoice_id": "00000000-0000-0000-0000-000000000000",
  "amount": 1.0,
  "payment_method": "<payment_method>",
  "reference": "<reference>",
  "notes": "<notes>",
  "processed_by": "<processed_by>",
  "created_at": "<created_at>"
}
```

## Consultations

### `GET /api/v1/consultations`

**Purpose:** List Consultations. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `patient_id` | query | no | `string` or `null` |
| `appointment_id` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `ConsultationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/consultations" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "patient_id": "00000000-0000-0000-0000-000000000000",
    "patient_name": "<patient_name>",
    "appointment_id": "00000000-0000-0000-0000-000000000000",
    "appointment_status": "<appointment_status>",
    "chief_complaint": "<chief_complaint>",
    "vital_signs": {},
    "symptoms": [
      "<symptoms>"
    ],
    "diagnosis": [
      "<diagnosis>"
    ],
    "treatment_plan": "<treatment_plan>",
    "prescriptions": [
      {}
    ],
    "lab_orders": [
      {}
    ]
  }
]
```

### `POST /api/v1/consultations/start`

**Purpose:** Start Consultation. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `ConsultationStart`.

**Success:** HTTP `201`; response schema `ConsultationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/consultations/start" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"patient_id":"00000000-0000-0000-0000-000000000000","appointment_id":"00000000-0000-0000-0000-000000000000","chief_complaint":"<chief_complaint>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "appointment_status": "<appointment_status>",
  "chief_complaint": "<chief_complaint>",
  "vital_signs": {},
  "symptoms": [
    "<symptoms>"
  ],
  "diagnosis": [
    "<diagnosis>"
  ],
  "treatment_plan": "<treatment_plan>",
  "prescriptions": [
    {}
  ],
  "lab_orders": [
    {}
  ]
}
```

### `GET /api/v1/consultations/{consultation_id}`

**Purpose:** Get Consultation. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `consultation_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `ConsultationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/consultations/{consultation_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "appointment_status": "<appointment_status>",
  "chief_complaint": "<chief_complaint>",
  "vital_signs": {},
  "symptoms": [
    "<symptoms>"
  ],
  "diagnosis": [
    "<diagnosis>"
  ],
  "treatment_plan": "<treatment_plan>",
  "prescriptions": [
    {}
  ],
  "lab_orders": [
    {}
  ]
}
```

### `PUT /api/v1/consultations/{consultation_id}`

**Purpose:** Update Consultation. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `consultation_id` | path | yes | `string` |

**Request body:** `application/json` using `ConsultationUpdate`.

**Success:** HTTP `200`; response schema `ConsultationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/consultations/{consultation_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "appointment_status": "<appointment_status>",
  "chief_complaint": "<chief_complaint>",
  "vital_signs": {},
  "symptoms": [
    "<symptoms>"
  ],
  "diagnosis": [
    "<diagnosis>"
  ],
  "treatment_plan": "<treatment_plan>",
  "prescriptions": [
    {}
  ],
  "lab_orders": [
    {}
  ]
}
```

### `POST /api/v1/consultations/{consultation_id}/complete`

**Purpose:** Complete Consultation. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `consultation_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `ConsultationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/consultations/{consultation_id}/complete" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "appointment_status": "<appointment_status>",
  "chief_complaint": "<chief_complaint>",
  "vital_signs": {},
  "symptoms": [
    "<symptoms>"
  ],
  "diagnosis": [
    "<diagnosis>"
  ],
  "treatment_plan": "<treatment_plan>",
  "prescriptions": [
    {}
  ],
  "lab_orders": [
    {}
  ]
}
```

## Dashboard

### `GET /api/v1/dashboard/stats`

**Purpose:** Get Dashboard Stats. Get dashboard statistics for a facility

**Access:** Authenticated user.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | query | yes | `string` |
| `department_id` | query | no | `string` or `null` |
| `branch_id` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/dashboard/stats" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape:** not constrained by a declared JSON response model.

## Emr

### `GET /api/v1/emr`

**Purpose:** Get Records. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `patient_id` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `MedicalRecordResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/emr" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "patient_id": "00000000-0000-0000-0000-000000000000",
    "appointment_id": "00000000-0000-0000-0000-000000000000",
    "chief_complaint": "<chief_complaint>",
    "vital_signs": {},
    "symptoms": [
      "<symptoms>"
    ],
    "diagnosis": [
      "<diagnosis>"
    ],
    "treatment_plan": "<treatment_plan>",
    "prescriptions": [
      {}
    ],
    "lab_orders": [
      {}
    ],
    "follow_up_date": "2026-07-31",
    "notes": "<notes>"
  }
]
```

### `POST /api/v1/emr`

**Purpose:** Create Record. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `MedicalRecordCreate`.

**Success:** HTTP `201`; response schema `MedicalRecordResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/emr" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"patient_id":"00000000-0000-0000-0000-000000000000"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "chief_complaint": "<chief_complaint>",
  "vital_signs": {},
  "symptoms": [
    "<symptoms>"
  ],
  "diagnosis": [
    "<diagnosis>"
  ],
  "treatment_plan": "<treatment_plan>",
  "prescriptions": [
    {}
  ],
  "lab_orders": [
    {}
  ],
  "follow_up_date": "2026-07-31",
  "notes": "<notes>"
}
```

### `DELETE /api/v1/emr/{record_id}`

**Purpose:** Delete Record. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `record_id` | path | yes | `string` |
| `reason` | query | no | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/emr/{record_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/emr/{record_id}`

**Purpose:** Get Record. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `record_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MedicalRecordResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/emr/{record_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "chief_complaint": "<chief_complaint>",
  "vital_signs": {},
  "symptoms": [
    "<symptoms>"
  ],
  "diagnosis": [
    "<diagnosis>"
  ],
  "treatment_plan": "<treatment_plan>",
  "prescriptions": [
    {}
  ],
  "lab_orders": [
    {}
  ],
  "follow_up_date": "2026-07-31",
  "notes": "<notes>"
}
```

### `PUT /api/v1/emr/{record_id}`

**Purpose:** Update Record. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `record_id` | path | yes | `string` |

**Request body:** `application/json` using `MedicalRecordUpdate`.

**Success:** HTTP `200`; response schema `MedicalRecordResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/emr/{record_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "chief_complaint": "<chief_complaint>",
  "vital_signs": {},
  "symptoms": [
    "<symptoms>"
  ],
  "diagnosis": [
    "<diagnosis>"
  ],
  "treatment_plan": "<treatment_plan>",
  "prescriptions": [
    {}
  ],
  "lab_orders": [
    {}
  ],
  "follow_up_date": "2026-07-31",
  "notes": "<notes>"
}
```

## Facilities

### `GET /api/v1/facilities`

**Purpose:** Get Facilities. Get all facilities (admin only)

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `search` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `FacilityResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "tenant_id": "00000000-0000-0000-0000-000000000000",
    "canonical_subdomain": "<canonical_subdomain>",
    "name": "<name>",
    "slug": "example-hospital",
    "type": "<type>",
    "country": "<country>",
    "address": "<address>",
    "phone": "+2348000000000",
    "email": "<email>",
    "modules": [
      "<modules>"
    ],
    "settings": {}
  }
]
```

### `POST /api/v1/facilities`

**Purpose:** Create Facility. Create a new facility (admin only)

**Access:** Authenticated; roles: `ADMIN`.

**Request body:** `application/json` using `FacilityCreate`.

**Success:** HTTP `201`; response schema `FacilityResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/facilities" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","type":"<type>","country":"<country>","address":"<address>","phone":"+2348000000000","email":"<email>","modules":["<modules>"],"settings":{}}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "tenant_id": "00000000-0000-0000-0000-000000000000",
  "canonical_subdomain": "<canonical_subdomain>",
  "name": "<name>",
  "slug": "example-hospital",
  "type": "<type>",
  "country": "<country>",
  "address": "<address>",
  "phone": "+2348000000000",
  "email": "<email>",
  "modules": [
    "<modules>"
  ],
  "settings": {}
}
```

### `POST /api/v1/facilities/ensure`

**Purpose:** Ensure Facility. Create a facility once, or return the existing facility for setup retries.

**Access:** Authenticated; roles: `ADMIN`.

**Request body:** `application/json` using `FacilityCreate`.

**Success:** HTTP `200`; response schema `FacilityResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/facilities/ensure" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","type":"<type>","country":"<country>","address":"<address>","phone":"+2348000000000","email":"<email>","modules":["<modules>"],"settings":{}}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "tenant_id": "00000000-0000-0000-0000-000000000000",
  "canonical_subdomain": "<canonical_subdomain>",
  "name": "<name>",
  "slug": "example-hospital",
  "type": "<type>",
  "country": "<country>",
  "address": "<address>",
  "phone": "+2348000000000",
  "email": "<email>",
  "modules": [
    "<modules>"
  ],
  "settings": {}
}
```

### `GET /api/v1/facilities/resolve-host/{canonical_subdomain}`

**Purpose:** Resolve Public Facility Host. Resolve a registered tenant hostname to its immutable facility identity.

**Access:** Public.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `canonical_subdomain` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `FacilityRoutingResponse`.

**Possible errors:** `400` business validation, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/resolve-host/{canonical_subdomain}"
```

**Example response shape**

```json
{
  "slug": "example-hospital",
  "canonical_subdomain": "<canonical_subdomain>"
}
```

### `GET /api/v1/facilities/resolve-workspace/{facility_slug}`

**Purpose:** Resolve Public Facility Workspace. Resolve a legacy slug without exposing facility configuration.

**Access:** Public.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `FacilityRoutingResponse`.

**Possible errors:** `400` business validation, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/resolve-workspace/{facility_slug}"
```

**Example response shape**

```json
{
  "slug": "example-hospital",
  "canonical_subdomain": "<canonical_subdomain>"
}
```

### `GET /api/v1/facilities/workspace/{facility_slug}`

**Purpose:** Get Public Facility Workspace. Return non-sensitive workspace metadata needed before login.

**Access:** Public.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `PublicFacilityWorkspaceResponse`.

**Possible errors:** `400` business validation, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/workspace/{facility_slug}"
```

**Example response shape**

```json
{
  "canonical_subdomain": "<canonical_subdomain>",
  "name": "<name>",
  "slug": "example-hospital",
  "type": "<type>",
  "country": "<country>",
  "modules": [
    "<modules>"
  ]
}
```

### `DELETE /api/v1/facilities/{facility_id}`

**Purpose:** Deactivate Facility. Deactivate facility (soft delete)

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/facilities/{facility_id}`

**Purpose:** Get Facility. Get facility by ID or slug for the current facility context.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `FacilityResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "tenant_id": "00000000-0000-0000-0000-000000000000",
  "canonical_subdomain": "<canonical_subdomain>",
  "name": "<name>",
  "slug": "example-hospital",
  "type": "<type>",
  "country": "<country>",
  "address": "<address>",
  "phone": "+2348000000000",
  "email": "<email>",
  "modules": [
    "<modules>"
  ],
  "settings": {}
}
```

### `PUT /api/v1/facilities/{facility_id}`

**Purpose:** Update Facility. Update facility (admin only)

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_id` | path | yes | `string` |

**Request body:** `application/json` using `FacilityUpdate`.

**Success:** HTTP `200`; response schema `FacilityResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","type":"<type>","country":"<country>","address":"<address>","phone":"+2348000000000","email":"<email>","settings":{}}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "tenant_id": "00000000-0000-0000-0000-000000000000",
  "canonical_subdomain": "<canonical_subdomain>",
  "name": "<name>",
  "slug": "example-hospital",
  "type": "<type>",
  "country": "<country>",
  "address": "<address>",
  "phone": "+2348000000000",
  "email": "<email>",
  "modules": [
    "<modules>"
  ],
  "settings": {}
}
```

### `PUT /api/v1/facilities/{facility_id}/modules`

**Purpose:** Update Facility Modules. Update enabled modules for a facility

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_id` | path | yes | `string` |

**Request body:** `application/json` using Array of `string` or `FacilityModulesUpdate`.

**Success:** HTTP `200`; response schema `FacilityResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_id}/modules" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '["<value>"]'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "tenant_id": "00000000-0000-0000-0000-000000000000",
  "canonical_subdomain": "<canonical_subdomain>",
  "name": "<name>",
  "slug": "example-hospital",
  "type": "<type>",
  "country": "<country>",
  "address": "<address>",
  "phone": "+2348000000000",
  "email": "<email>",
  "modules": [
    "<modules>"
  ],
  "settings": {}
}
```

### `GET /api/v1/facilities/{facility_slug}/branches`

**Purpose:** List Branches. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `BranchResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/branches" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "name": "<name>",
    "slug": "example-hospital",
    "login_url_path": "<login_url_path>",
    "dashboard_url_path": "<dashboard_url_path>",
    "created_at": "<created_at>"
  }
]
```

### `POST /api/v1/facilities/{facility_slug}/branches`

**Purpose:** Create Branch. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |

**Request body:** `application/json` using `BranchCreate`.

**Success:** HTTP `201`; response schema `BranchResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/branches" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","location":"<location>","address":"<address>","phone":"+2348000000000","email":"staff@example.invalid","modules":["<modules>"],"settings":{}}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "name": "<name>",
  "slug": "example-hospital",
  "login_url_path": "<login_url_path>",
  "dashboard_url_path": "<dashboard_url_path>",
  "created_at": "<created_at>"
}
```

### `DELETE /api/v1/facilities/{facility_slug}/branches/{branch_id_or_slug}`

**Purpose:** Deactivate Branch. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `branch_id_or_slug` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/branches/{branch_id_or_slug}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `PUT /api/v1/facilities/{facility_slug}/branches/{branch_id_or_slug}`

**Purpose:** Update Branch. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `branch_id_or_slug` | path | yes | `string` |

**Request body:** `application/json` using `BranchUpdate`.

**Success:** HTTP `200`; response schema `BranchResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/branches/{branch_id_or_slug}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "name": "<name>",
  "slug": "example-hospital",
  "login_url_path": "<login_url_path>",
  "dashboard_url_path": "<dashboard_url_path>",
  "created_at": "<created_at>"
}
```

### `PUT /api/v1/facilities/{facility_slug}/branches/{branch_id_or_slug}/modules`

**Purpose:** Update Branch Modules. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `branch_id_or_slug` | path | yes | `string` |

**Request body:** `application/json` using `BranchModulesUpdate`.

**Success:** HTTP `200`; response schema `BranchResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/branches/{branch_id_or_slug}/modules" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"modules":["<modules>"]}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "name": "<name>",
  "slug": "example-hospital",
  "login_url_path": "<login_url_path>",
  "dashboard_url_path": "<dashboard_url_path>",
  "created_at": "<created_at>"
}
```

### `GET /api/v1/facilities/{facility_slug}/clinicians`

**Purpose:** Get Facility Clinicians. List active clinicians that can be assigned to appointments.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `FacilityStaffResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/clinicians" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "staffRecordId": "<staffRecordId>",
    "facilitySlug": "example-hospital",
    "fullName": "<fullName>",
    "role": "<role>",
    "department": "<department>",
    "email": "<email>",
    "phone": "+2348000000000",
    "loginId": "<loginId>",
    "mustChangePassword": true,
    "status": "<status>",
    "createdAt": "<createdAt>"
  }
]
```

### `POST /api/v1/facilities/{facility_slug}/data-migrations/import`

**Purpose:** Queue Data Migration Import. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `multipart/form-data` using `Body_queue_data_migration_import_api_v1_facilities__facility_slug__data_migrations_import_post`.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/data-migrations/import" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `GET /api/v1/facilities/{facility_slug}/data-migrations/jobs/{job_id}`

**Purpose:** Get Data Migration Job. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `job_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/data-migrations/jobs/{job_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `POST /api/v1/facilities/{facility_slug}/data-migrations/validate`

**Purpose:** Validate Data Migration. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |

**Request body:** `multipart/form-data` using `Body_validate_data_migration_api_v1_facilities__facility_slug__data_migrations_validate_post`.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/data-migrations/validate" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `GET /api/v1/facilities/{facility_slug}/departments`

**Purpose:** List Departments. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/departments" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `POST /api/v1/facilities/{facility_slug}/departments`

**Purpose:** Add Department. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |

**Request body:** `application/json` using `DepartmentCreate`.

**Success:** HTTP `201`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/departments" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","location":"<location>","phone_extension":"+2348000000000","services":["<services>"],"is_visible":false}'
```

**Example response shape:** not constrained by a declared JSON response model.

### `DELETE /api/v1/facilities/{facility_slug}/departments/{dept_id}`

**Purpose:** Remove Department. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `dept_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/departments/{dept_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `PUT /api/v1/facilities/{facility_slug}/departments/{dept_id}`

**Purpose:** Update Department. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `dept_id` | path | yes | `string` |

**Request body:** `application/json` using `DepartmentUpdate`.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/departments/{dept_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","location":"<location>","phone_extension":"+2348000000000","services":["<services>"],"is_visible":true}'
```

**Example response shape:** not constrained by a declared JSON response model.

### `PUT /api/v1/facilities/{facility_slug}/settings`

**Purpose:** Update Facility Settings. Switch a facility between single-hospital and multi-clinic operation.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |

**Request body:** `application/json` using `FacilitySettingsUpdate`.

**Success:** HTTP `200`; response schema `FacilityResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/settings" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"hospital_type":"single"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "tenant_id": "00000000-0000-0000-0000-000000000000",
  "canonical_subdomain": "<canonical_subdomain>",
  "name": "<name>",
  "slug": "example-hospital",
  "type": "<type>",
  "country": "<country>",
  "address": "<address>",
  "phone": "+2348000000000",
  "email": "<email>",
  "modules": [
    "<modules>"
  ],
  "settings": {}
}
```

### `GET /api/v1/facilities/{facility_slug}/staff`

**Purpose:** Get Facility Staff. List active staff accounts for a facility.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `FacilityStaffResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/staff" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "staffRecordId": "<staffRecordId>",
    "facilitySlug": "example-hospital",
    "fullName": "<fullName>",
    "role": "<role>",
    "department": "<department>",
    "email": "<email>",
    "phone": "+2348000000000",
    "loginId": "<loginId>",
    "mustChangePassword": true,
    "status": "<status>",
    "createdAt": "<createdAt>"
  }
]
```

### `POST /api/v1/facilities/{facility_slug}/staff`

**Purpose:** Create Facility Staff. Create a staff user for a facility and return one-time credentials.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |

**Request body:** `application/json` using `FacilityStaffCreate`.

**Success:** HTTP `201`; response schema `FacilityStaffResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/staff" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"fullName":"<fullName>","role":"<role>","department":"<department>"}'
```

**Example response shape**

```json
{
  "staffRecordId": "<staffRecordId>",
  "facilitySlug": "example-hospital",
  "fullName": "<fullName>",
  "role": "<role>",
  "department": "<department>",
  "email": "<email>",
  "phone": "+2348000000000",
  "loginId": "<loginId>",
  "mustChangePassword": true,
  "status": "<status>",
  "createdAt": "<createdAt>"
}
```

### `GET /api/v1/facilities/{facility_slug}/staff/{login_id}`

**Purpose:** Get Facility Staff Member. Get one staff account by login ID.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `login_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `FacilityStaffResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/staff/{login_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "staffRecordId": "<staffRecordId>",
  "facilitySlug": "example-hospital",
  "fullName": "<fullName>",
  "role": "<role>",
  "department": "<department>",
  "email": "<email>",
  "phone": "+2348000000000",
  "loginId": "<loginId>",
  "mustChangePassword": true,
  "status": "<status>",
  "createdAt": "<createdAt>"
}
```

### `PUT /api/v1/facilities/{facility_slug}/staff/{login_id}`

**Purpose:** Update Facility Staff Member. Update a staff account's details, role, active state, or password.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | path | yes | `string` |
| `login_id` | path | yes | `string` |

**Request body:** `application/json` using `FacilityStaffUpdate`.

**Success:** HTTP `200`; response schema `FacilityStaffResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/facilities/{facility_slug}/staff/{login_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{}'
```

**Example response shape**

```json
{
  "staffRecordId": "<staffRecordId>",
  "facilitySlug": "example-hospital",
  "fullName": "<fullName>",
  "role": "<role>",
  "department": "<department>",
  "email": "<email>",
  "phone": "+2348000000000",
  "loginId": "<loginId>",
  "mustChangePassword": true,
  "status": "<status>",
  "createdAt": "<createdAt>"
}
```

## Files

### `GET /api/v1/files`

**Purpose:** List Files. List uploaded files

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `folder` | query | no | `string` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/files" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `GET /api/v1/files/content/{filename}`

**Purpose:** Download File. Download a private file after tenant and branch authorization.

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `filename` | path | yes | `string` |
| `folder` | query | no | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/files/content/{filename}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `POST /api/v1/files/upload`

**Purpose:** Upload File. Upload a file

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Request body:** `multipart/form-data` using `Body_upload_file_api_v1_files_upload_post`.

**Success:** HTTP `201`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/files/upload" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `DELETE /api/v1/files/{filename}`

**Purpose:** Delete File. Delete a file

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `filename` | path | yes | `string` |
| `folder` | query | no | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/files/{filename}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/files/{filename}`

**Purpose:** Get File Info. Get file information

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `filename` | path | yes | `string` |
| `folder` | query | no | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/files/{filename}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape:** not constrained by a declared JSON response model.

## Inventory

### `GET /api/v1/inventory`

**Purpose:** Get Inventory Items. Paginated list of inventory items

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `PHARMACIST`, `STORE_KEEPER`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |
| `facility_slug` | query | no | `string` or `null` |
| `category` | query | no | `string` or `null` |
| `search` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `app__schemas__inventory__InventoryResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/inventory" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "name": "<name>",
    "sku": "<sku>",
    "category": "<category>",
    "unit": "<unit>",
    "reorder_level": 1,
    "reorder_quantity": 1,
    "current_stock": 1,
    "expiry_date": "2026-07-31",
    "supplier_id": "00000000-0000-0000-0000-000000000000",
    "unit_cost": 1.0
  }
]
```

### `POST /api/v1/inventory`

**Purpose:** Create Inventory Item. Create a new inventory item

**Access:** Authenticated; roles: `ADMIN`, `PHARMACIST`, `STORE_KEEPER`.

**Request body:** `application/json` using `app__schemas__inventory__InventoryCreate`.

**Success:** HTTP `201`; response schema `app__schemas__inventory__InventoryResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/inventory" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","sku":"<sku>","category":"<category>","unit":"<unit>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "name": "<name>",
  "sku": "<sku>",
  "category": "<category>",
  "unit": "<unit>",
  "reorder_level": 1,
  "reorder_quantity": 1,
  "current_stock": 1,
  "expiry_date": "2026-07-31",
  "supplier_id": "00000000-0000-0000-0000-000000000000",
  "unit_cost": 1.0
}
```

### `GET /api/v1/inventory/low-stock`

**Purpose:** Get Low Stock. Get items that are below reorder level

**Access:** Authenticated; roles: `ADMIN`, `PHARMACIST`, `STORE_KEEPER`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `facility_slug` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `LowStockItemResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/inventory/low-stock" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "medication_id": "00000000-0000-0000-0000-000000000000",
    "medication_name": "<medication_name>",
    "quantity": 1,
    "reorder_level": 1,
    "facility_slug": "example-hospital"
  }
]
```

### `POST /api/v1/inventory/reorder`

**Purpose:** Create Reorder Requests. Create reorder requests for low stock items (placeholder)

**Access:** Authenticated; roles: `ADMIN`, `PHARMACIST`.

**Request body:** `application/json` using `ReorderRequest`.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/inventory/reorder" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"item_ids":["<item_ids>"],"supplier_id":"00000000-0000-0000-0000-000000000000","notes":"<notes>"}'
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `DELETE /api/v1/inventory/{item_id}`

**Purpose:** Deactivate Inventory Item. Deactivate inventory item (soft delete)

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `item_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/inventory/{item_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/inventory/{item_id}`

**Purpose:** Get Inventory Item. Get inventory item by ID

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `PHARMACIST`, `STORE_KEEPER`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `item_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `app__schemas__inventory__InventoryResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/inventory/{item_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "name": "<name>",
  "sku": "<sku>",
  "category": "<category>",
  "unit": "<unit>",
  "reorder_level": 1,
  "reorder_quantity": 1,
  "current_stock": 1,
  "expiry_date": "2026-07-31",
  "supplier_id": "00000000-0000-0000-0000-000000000000",
  "unit_cost": 1.0
}
```

### `PUT /api/v1/inventory/{item_id}`

**Purpose:** Update Inventory Item. Update inventory item

**Access:** Authenticated; roles: `ADMIN`, `PHARMACIST`, `STORE_KEEPER`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `item_id` | path | yes | `string` |

**Request body:** `application/json` using `InventoryUpdate`.

**Success:** HTTP `200`; response schema `app__schemas__inventory__InventoryResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/inventory/{item_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "name": "<name>",
  "sku": "<sku>",
  "category": "<category>",
  "unit": "<unit>",
  "reorder_level": 1,
  "reorder_quantity": 1,
  "current_stock": 1,
  "expiry_date": "2026-07-31",
  "supplier_id": "00000000-0000-0000-0000-000000000000",
  "unit_cost": 1.0
}
```

### `PUT /api/v1/inventory/{item_id}/stock`

**Purpose:** Update Stock. Update stock level

**Access:** Authenticated; roles: `ADMIN`, `PHARMACIST`, `STORE_KEEPER`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `item_id` | path | yes | `string` |
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `StockUpdate`.

**Success:** HTTP `200`; response schema `app__schemas__inventory__InventoryResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

- The mutation uses a database row lock on supported databases.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/inventory/{item_id}/stock" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"current_stock":1,"adjustment_type":"<adjustment_type>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "name": "<name>",
  "sku": "<sku>",
  "category": "<category>",
  "unit": "<unit>",
  "reorder_level": 1,
  "reorder_quantity": 1,
  "current_stock": 1,
  "expiry_date": "2026-07-31",
  "supplier_id": "00000000-0000-0000-0000-000000000000",
  "unit_cost": 1.0
}
```

## Laboratory

### `GET /api/v1/laboratory/orders`

**Purpose:** Get Lab Orders. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |
| `patient_id` | query | no | `string` or `null` |
| `status` | query | no | `string` or `null` |
| `branch_id` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `LabOrderResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/laboratory/orders" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "patient_id": "00000000-0000-0000-0000-000000000000",
    "test_id": "00000000-0000-0000-0000-000000000000",
    "ordered_by": "<ordered_by>",
    "status": "<status>",
    "priority": "<priority>",
    "notes": "<notes>",
    "completed_at": "<completed_at>",
    "facility_slug": "example-hospital",
    "created_at": "<created_at>",
    "updated_at": "2026-07-31"
  }
]
```

### `POST /api/v1/laboratory/orders`

**Purpose:** Create Lab Order. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `LabOrderCreate`.

**Success:** HTTP `201`; response schema `LabOrderResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/laboratory/orders" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"patient_id":"00000000-0000-0000-0000-000000000000","test_id":"00000000-0000-0000-0000-000000000000","priority":"<priority>","notes":"<notes>","order_date":"2026-07-31","department_id":"00000000-0000-0000-0000-000000000000","branch_id":"00000000-0000-0000-0000-000000000000"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "test_id": "00000000-0000-0000-0000-000000000000",
  "ordered_by": "<ordered_by>",
  "status": "<status>",
  "priority": "<priority>",
  "notes": "<notes>",
  "completed_at": "<completed_at>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `GET /api/v1/laboratory/orders/{order_id}`

**Purpose:** Get Lab Order. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `order_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `LabOrderResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/laboratory/orders/{order_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "test_id": "00000000-0000-0000-0000-000000000000",
  "ordered_by": "<ordered_by>",
  "status": "<status>",
  "priority": "<priority>",
  "notes": "<notes>",
  "completed_at": "<completed_at>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `PUT /api/v1/laboratory/orders/{order_id}`

**Purpose:** Update Lab Order Status. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `LAB_TECH`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `order_id` | path | yes | `string` |

**Request body:** `application/json` using `LabOrderUpdate`.

**Success:** HTTP `200`; response schema `LabOrderResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/laboratory/orders/{order_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"status":"<status>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "test_id": "00000000-0000-0000-0000-000000000000",
  "ordered_by": "<ordered_by>",
  "status": "<status>",
  "priority": "<priority>",
  "notes": "<notes>",
  "completed_at": "<completed_at>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `GET /api/v1/laboratory/results/{order_id}`

**Purpose:** Get Lab Result. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `order_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `LabResultResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/laboratory/results/{order_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "order_id": "00000000-0000-0000-0000-000000000000",
  "entered_by": "<entered_by>",
  "value": "<value>",
  "is_abnormal": true,
  "notes": "<notes>",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `POST /api/v1/laboratory/results/{order_id}`

**Purpose:** Create Lab Result. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `LAB_TECH`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `order_id` | path | yes | `string` |

**Request body:** `application/json` using `LabResultCreate`.

**Success:** HTTP `201`; response schema `LabResultResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/laboratory/results/{order_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"value":"<value>","is_abnormal":false,"notes":"<notes>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "order_id": "00000000-0000-0000-0000-000000000000",
  "entered_by": "<entered_by>",
  "value": "<value>",
  "is_abnormal": true,
  "notes": "<notes>",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `GET /api/v1/laboratory/tests`

**Purpose:** Get Lab Tests. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `active_only` | query | no | `boolean` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `LabTestResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/laboratory/tests" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "name": "<name>",
    "code": "<code>",
    "description": "<description>",
    "category": "<category>",
    "unit": "<unit>",
    "reference_range": "<reference_range>",
    "price": 1.0,
    "is_active": true,
    "created_at": "<created_at>",
    "updated_at": "2026-07-31"
  }
]
```

### `POST /api/v1/laboratory/tests`

**Purpose:** Create Lab Test. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Request body:** `application/json` using `LabTestCreate`.

**Success:** HTTP `201`; response schema `LabTestResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/laboratory/tests" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","code":"<code>","description":"<description>","category":"<category>","unit":"<unit>","reference_range":"<reference_range>","price":1.0}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "name": "<name>",
  "code": "<code>",
  "description": "<description>",
  "category": "<category>",
  "unit": "<unit>",
  "reference_range": "<reference_range>",
  "price": 1.0,
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `GET /api/v1/laboratory/tests/{test_id}`

**Purpose:** Get Lab Test. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `test_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `LabTestResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/laboratory/tests/{test_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "name": "<name>",
  "code": "<code>",
  "description": "<description>",
  "category": "<category>",
  "unit": "<unit>",
  "reference_range": "<reference_range>",
  "price": 1.0,
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `PUT /api/v1/laboratory/tests/{test_id}`

**Purpose:** Update Lab Test. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `test_id` | path | yes | `string` |

**Request body:** `application/json` using `LabTestCreate`.

**Success:** HTTP `200`; response schema `LabTestResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/laboratory/tests/{test_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","code":"<code>","description":"<description>","category":"<category>","unit":"<unit>","reference_range":"<reference_range>","price":1.0}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "name": "<name>",
  "code": "<code>",
  "description": "<description>",
  "category": "<category>",
  "unit": "<unit>",
  "reference_range": "<reference_range>",
  "price": 1.0,
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

## Operations

### `GET /health`

**Purpose:** Health Check. No additional route description is declared.

**Access:** Public.

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/health"
```

**Example response shape:** not constrained by a declared JSON response model.

## Order Workflow

### `GET /api/v1/order-workflow`

**Purpose:** List Order Workflow Events. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `patient_id` | query | no | `string` or `null` |
| `order_type` | query | no | `string` or `null` |
| `order_id` | query | no | `string` or `null` |
| `event_type` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `OrderWorkflowEventResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/order-workflow" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "order_type": "<order_type>",
    "order_id": "00000000-0000-0000-0000-000000000000",
    "event_type": "<event_type>",
    "status": "<status>",
    "title": "<title>",
    "occurred_at": "<occurred_at>",
    "created_at": "<created_at>"
  }
]
```

## Password Reset

### `POST /api/v1/password-reset/change`

**Purpose:** Change Password Authenticated. Change password for authenticated user

**Access:** Authenticated user.

**Request body:** `application/json` using `ChangePasswordRequest`.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/password-reset/change" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"current_password":"<strong-password>","new_password":"<strong-password>"}'
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `POST /api/v1/password-reset/confirm`

**Purpose:** Confirm Password Reset. Confirm password reset with token

**Access:** Public.

**Request body:** `application/json` using `ResetPasswordRequest`.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/password-reset/confirm" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"token":"<token>","new_password":"<strong-password>"}'
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `POST /api/v1/password-reset/forgot`

**Purpose:** Forgot Password. Request password reset - sends reset email

**Access:** Public.

**Request body:** `application/json` using `ForgotPasswordRequest`.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/password-reset/forgot" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"email":"staff@example.invalid"}'
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

## Patient Notifications

### `GET /api/v1/patient-notifications`

**Purpose:** List Patient Notifications. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `patient_id` | query | no | `string` or `null` |
| `status` | query | no | `string` or `null` |
| `channel` | query | no | `string` or `null` |
| `notification_type` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `PatientNotificationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/patient-notifications" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "patient_id": "00000000-0000-0000-0000-000000000000",
    "notification_type": "<notification_type>",
    "channel": "<channel>",
    "title": "<title>",
    "message": "<message>",
    "status": "<status>",
    "created_at": "<created_at>"
  }
]
```

### `PUT /api/v1/patient-notifications/{notification_id}/read`

**Purpose:** Mark Patient Notification Read. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `notification_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `PatientNotificationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/patient-notifications/{notification_id}/read" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "notification_type": "<notification_type>",
  "channel": "<channel>",
  "title": "<title>",
  "message": "<message>",
  "status": "<status>",
  "created_at": "<created_at>"
}
```

### `PUT /api/v1/patient-notifications/{notification_id}/sent`

**Purpose:** Mark Patient Notification Sent. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `notification_id` | path | yes | `string` |

**Request body:** `application/json` using `PatientNotificationMarkSent`.

**Success:** HTTP `200`; response schema `PatientNotificationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/patient-notifications/{notification_id}/sent" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"provider_message_id":"00000000-0000-0000-0000-000000000000"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "notification_type": "<notification_type>",
  "channel": "<channel>",
  "title": "<title>",
  "message": "<message>",
  "status": "<status>",
  "created_at": "<created_at>"
}
```

## Patients

### `GET /api/v1/patients`

**Purpose:** Get Patients. Get paginated list of patients

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |
| `search` | query | no | `string` or `null` |
| `department_id` | query | no | `string` or `null` |
| `branch_id` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema `PatientListResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/patients" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "patients": [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "first_name": "<first_name>",
      "last_name": "<last_name>",
      "date_of_birth": "2026-07-31",
      "gender": "<gender>",
      "phone": "+2348000000000",
      "email": "<email>",
      "address": "<address>",
      "blood_type": "<blood_type>",
      "medical_history": {},
      "emergency_contact_name": "<emergency_contact_name>",
      "emergency_contact_phone": "+2348000000000"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 1,
  "pages": 1
}
```

### `POST /api/v1/patients`

**Purpose:** Create Patient. Create a new patient

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `PatientCreate`.

**Success:** HTTP `201`; response schema `PatientResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/patients" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"first_name":"<first_name>","last_name":"<last_name>","date_of_birth":"2026-07-31"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "first_name": "<first_name>",
  "last_name": "<last_name>",
  "date_of_birth": "2026-07-31",
  "gender": "<gender>",
  "phone": "+2348000000000",
  "email": "<email>",
  "address": "<address>",
  "blood_type": "<blood_type>",
  "medical_history": {},
  "emergency_contact_name": "<emergency_contact_name>",
  "emergency_contact_phone": "+2348000000000"
}
```

### `GET /api/v1/patients/options`

**Purpose:** Get Patient Options. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `search` | query | no | `string` or `null` |
| `limit` | query | no | `integer` |
| `department_id` | query | no | `string` or `null` |
| `branch_id` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `PatientOptionResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/patients/options" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "first_name": "<first_name>",
    "last_name": "<last_name>",
    "full_name": "<full_name>",
    "phone": "+2348000000000"
  }
]
```

### `DELETE /api/v1/patients/{patient_id}`

**Purpose:** Delete Patient. Delete patient (soft delete)

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `patient_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/patients/{patient_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/patients/{patient_id}`

**Purpose:** Get Patient. Get patient by ID

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `patient_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `PatientResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/patients/{patient_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "first_name": "<first_name>",
  "last_name": "<last_name>",
  "date_of_birth": "2026-07-31",
  "gender": "<gender>",
  "phone": "+2348000000000",
  "email": "<email>",
  "address": "<address>",
  "blood_type": "<blood_type>",
  "medical_history": {},
  "emergency_contact_name": "<emergency_contact_name>",
  "emergency_contact_phone": "+2348000000000"
}
```

### `PUT /api/v1/patients/{patient_id}`

**Purpose:** Update Patient. Update patient information

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `patient_id` | path | yes | `string` |

**Request body:** `application/json` using `PatientUpdate`.

**Success:** HTTP `200`; response schema `PatientResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/patients/{patient_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "first_name": "<first_name>",
  "last_name": "<last_name>",
  "date_of_birth": "2026-07-31",
  "gender": "<gender>",
  "phone": "+2348000000000",
  "email": "<email>",
  "address": "<address>",
  "blood_type": "<blood_type>",
  "medical_history": {},
  "emergency_contact_name": "<emergency_contact_name>",
  "emergency_contact_phone": "+2348000000000"
}
```

### `GET /api/v1/patients/{patient_id}/timeline`

**Purpose:** Get Patient Timeline. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `patient_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `PatientTimelineResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/patients/{patient_id}/timeline" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "patient": {
    "id": "00000000-0000-0000-0000-000000000000",
    "first_name": "<first_name>",
    "last_name": "<last_name>",
    "date_of_birth": "2026-07-31",
    "gender": "<gender>",
    "phone": "+2348000000000",
    "email": "<email>",
    "address": "<address>",
    "blood_type": "<blood_type>",
    "medical_history": {},
    "emergency_contact_name": "<emergency_contact_name>",
    "emergency_contact_phone": "+2348000000000"
  },
  "events": [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "event_type": "<event_type>",
      "module": "<module>",
      "title": "<title>",
      "description": "<description>",
      "status": "<status>",
      "occurred_at": "<occurred_at>",
      "metadata": {}
    }
  ],
  "total": 1
}
```

## Pharmacy

### `GET /api/v1/pharmacy/inventory/{medication_id}`

**Purpose:** Get Inventory. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `PHARMACIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `medication_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `app__schemas__pharmacy__InventoryResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/inventory/{medication_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "medication_id": "00000000-0000-0000-0000-000000000000",
  "quantity": 1,
  "expiry_date": "2026-07-31",
  "batch_number": "<batch_number>",
  "location": "<location>",
  "last_updated": "2026-07-31"
}
```

### `POST /api/v1/pharmacy/inventory/{medication_id}`

**Purpose:** Add Inventory. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `PHARMACIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `medication_id` | path | yes | `string` |
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `app__schemas__pharmacy__InventoryCreate`.

**Success:** HTTP `201`; response schema `app__schemas__pharmacy__InventoryResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/inventory/{medication_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"quantity":1,"expiry_date":"2026-07-31","batch_number":"<batch_number>","location":"<location>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "medication_id": "00000000-0000-0000-0000-000000000000",
  "quantity": 1,
  "expiry_date": "2026-07-31",
  "batch_number": "<batch_number>",
  "location": "<location>",
  "last_updated": "2026-07-31"
}
```

### `GET /api/v1/pharmacy/medications`

**Purpose:** Get Medications. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `PHARMACIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `active_only` | query | no | `boolean` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `MedicationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/medications" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "name": "<name>",
    "code": "<code>",
    "generic_name": "<generic_name>",
    "description": "<description>",
    "category": "<category>",
    "unit": "<unit>",
    "strength": "<strength>",
    "price": 1.0,
    "reorder_level": 1,
    "is_active": true,
    "facility_slug": "example-hospital"
  }
]
```

### `POST /api/v1/pharmacy/medications`

**Purpose:** Create Medication. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Request body:** `application/json` using `MedicationCreate`.

**Success:** HTTP `201`; response schema `MedicationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/medications" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","code":"<code>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "name": "<name>",
  "code": "<code>",
  "generic_name": "<generic_name>",
  "description": "<description>",
  "category": "<category>",
  "unit": "<unit>",
  "strength": "<strength>",
  "price": 1.0,
  "reorder_level": 1,
  "is_active": true,
  "facility_slug": "example-hospital"
}
```

### `GET /api/v1/pharmacy/medications/{medication_id}`

**Purpose:** Get Medication. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `PHARMACIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `medication_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MedicationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/medications/{medication_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "name": "<name>",
  "code": "<code>",
  "generic_name": "<generic_name>",
  "description": "<description>",
  "category": "<category>",
  "unit": "<unit>",
  "strength": "<strength>",
  "price": 1.0,
  "reorder_level": 1,
  "is_active": true,
  "facility_slug": "example-hospital"
}
```

### `PUT /api/v1/pharmacy/medications/{medication_id}`

**Purpose:** Update Medication. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `medication_id` | path | yes | `string` |

**Request body:** `application/json` using `MedicationCreate`.

**Success:** HTTP `200`; response schema `MedicationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/medications/{medication_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","code":"<code>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "name": "<name>",
  "code": "<code>",
  "generic_name": "<generic_name>",
  "description": "<description>",
  "category": "<category>",
  "unit": "<unit>",
  "strength": "<strength>",
  "price": 1.0,
  "reorder_level": 1,
  "is_active": true,
  "facility_slug": "example-hospital"
}
```

### `GET /api/v1/pharmacy/prescriptions`

**Purpose:** Get Prescriptions. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `PHARMACIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |
| `patient_id` | query | no | `string` or `null` |
| `status` | query | no | `string` or `null` |
| `department_id` | query | no | `string` or `null` |
| `branch_id` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `PrescriptionResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/prescriptions" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "patient_id": "00000000-0000-0000-0000-000000000000",
    "prescribed_by": "<prescribed_by>",
    "status": "<status>",
    "notes": "<notes>",
    "filled_by": "<filled_by>",
    "filled_at": "<filled_at>",
    "facility_slug": "example-hospital",
    "created_at": "<created_at>",
    "updated_at": "2026-07-31"
  }
]
```

### `POST /api/v1/pharmacy/prescriptions`

**Purpose:** Create Prescription. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `PrescriptionCreate`.

**Success:** HTTP `201`; response schema `PrescriptionResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/prescriptions" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"patient_id":"00000000-0000-0000-0000-000000000000","items":[{"medication_id":"00000000-0000-0000-0000-000000000000","quantity":1,"dosage":"<dosage>","instructions":"<instructions>"}],"notes":"<notes>","department_id":"00000000-0000-0000-0000-000000000000","branch_id":"00000000-0000-0000-0000-000000000000"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "prescribed_by": "<prescribed_by>",
  "status": "<status>",
  "notes": "<notes>",
  "filled_by": "<filled_by>",
  "filled_at": "<filled_at>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `DELETE /api/v1/pharmacy/prescriptions/{prescription_id}`

**Purpose:** Cancel Prescription. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `prescription_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/prescriptions/{prescription_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/pharmacy/prescriptions/{prescription_id}`

**Purpose:** Get Prescription. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `PHARMACIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `prescription_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `PrescriptionResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/prescriptions/{prescription_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "prescribed_by": "<prescribed_by>",
  "status": "<status>",
  "notes": "<notes>",
  "filled_by": "<filled_by>",
  "filled_at": "<filled_at>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `POST /api/v1/pharmacy/prescriptions/{prescription_id}/dispense`

**Purpose:** Dispense Prescription. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `PHARMACIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `prescription_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `PrescriptionResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/pharmacy/prescriptions/{prescription_id}/dispense" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "prescribed_by": "<prescribed_by>",
  "status": "<status>",
  "notes": "<notes>",
  "filled_by": "<filled_by>",
  "filled_at": "<filled_at>",
  "facility_slug": "example-hospital",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

## Public Profile

### `GET /api/v1/facilities/{slug}/public-profile`

**Purpose:** Get Public Profile. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `slug` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/facilities/{slug}/public-profile" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `PUT /api/v1/facilities/{slug}/public-profile`

**Purpose:** Update Public Profile. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `slug` | path | yes | `string` |

**Request body:** `application/json` using `PublicProfileUpdate`.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/facilities/{slug}/public-profile" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"is_public":false,"display_name":"<display_name>","description":"<description>","phone":"+2348000000000","email":"<email>","photos":["<photos>"],"departments":[{"id":"00000000-0000-0000-0000-000000000000","is_visible":false,"services":[{"id":null,"name":null,"price":null,"duration":null,"description":null}],"staff_ids":["<staff_ids>"],"working_hours":{},"photos":["<photos>"]}]}'
```

**Example response shape:** not constrained by a declared JSON response model.

### `PUT /api/v1/facilities/{slug}/public-profile/departments/{dept_id}/services`

**Purpose:** Update Department Services. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `slug` | path | yes | `string` |
| `dept_id` | path | yes | `string` |

**Request body:** `application/json` using Array of `PublicService`.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/facilities/{slug}/public-profile/departments/{dept_id}/services" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '[{"id":"00000000-0000-0000-0000-000000000000","name":"<name>","price":1.0,"duration":"<duration>","description":"<description>"}]'
```

**Example response shape:** not constrained by a declared JSON response model.

### `PUT /api/v1/facilities/{slug}/public-profile/departments/{dept_id}/staff`

**Purpose:** Update Public Staff. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `slug` | path | yes | `string` |
| `dept_id` | path | yes | `string` |

**Request body:** `application/json` using Array of `string`.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/facilities/{slug}/public-profile/departments/{dept_id}/staff" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '["<value>"]'
```

**Example response shape:** not constrained by a declared JSON response model.

## Queue

### `GET /api/v1/queue`

**Purpose:** Get Queue. Get queue entries for user's facility

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `status` | query | no | `string` or `null` |
| `department` | query | no | `string` or `null` |
| `branch_id` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema `QueueListResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/queue" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "queue_entries": [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "patient_id": "00000000-0000-0000-0000-000000000000",
      "patient_name": "<patient_name>",
      "patient_phone": "+2348000000000",
      "patient_date_of_birth": "2026-07-31",
      "appointment_id": "00000000-0000-0000-0000-000000000000",
      "appointment_time": "<appointment_time>",
      "facility_slug": "example-hospital",
      "department": "<department>",
      "status": "<status>",
      "queue_number": 1,
      "priority": "<priority>"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 1,
  "pages": 1
}
```

### `POST /api/v1/queue`

**Purpose:** Add To Queue. Add patient to queue

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `QueueCreate`.

**Success:** HTTP `201`; response schema `QueueResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/queue" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"patient_id":"00000000-0000-0000-0000-000000000000","appointment_id":"00000000-0000-0000-0000-000000000000","department":"<department>","branch_id":"00000000-0000-0000-0000-000000000000","priority":"normal"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "patient_phone": "+2348000000000",
  "patient_date_of_birth": "2026-07-31",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "appointment_time": "<appointment_time>",
  "facility_slug": "example-hospital",
  "department": "<department>",
  "status": "<status>",
  "queue_number": 1,
  "priority": "<priority>"
}
```

### `DELETE /api/v1/queue/{queue_id}`

**Purpose:** Remove From Queue. Remove patient from queue

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `queue_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/queue/{queue_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/queue/{queue_id}`

**Purpose:** Get Queue Entry. Get queue entry by ID

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `queue_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `QueueResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/queue/{queue_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "patient_phone": "+2348000000000",
  "patient_date_of_birth": "2026-07-31",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "appointment_time": "<appointment_time>",
  "facility_slug": "example-hospital",
  "department": "<department>",
  "status": "<status>",
  "queue_number": 1,
  "priority": "<priority>"
}
```

### `PUT /api/v1/queue/{queue_id}`

**Purpose:** Update Queue Entry. Update queue entry

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `queue_id` | path | yes | `string` |

**Request body:** `application/json` using `QueueUpdate`.

**Success:** HTTP `200`; response schema `QueueResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/queue/{queue_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"status":"<status>","priority":"<priority>","department":"<department>","branch_id":"00000000-0000-0000-0000-000000000000"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "patient_phone": "+2348000000000",
  "patient_date_of_birth": "2026-07-31",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "appointment_time": "<appointment_time>",
  "facility_slug": "example-hospital",
  "department": "<department>",
  "status": "<status>",
  "queue_number": 1,
  "priority": "<priority>"
}
```

### `PUT /api/v1/queue/{queue_id}/checkin`

**Purpose:** Check In Patient. Check in patient

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `queue_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `QueueResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/queue/{queue_id}/checkin" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "patient_phone": "+2348000000000",
  "patient_date_of_birth": "2026-07-31",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "appointment_time": "<appointment_time>",
  "facility_slug": "example-hospital",
  "department": "<department>",
  "status": "<status>",
  "queue_number": 1,
  "priority": "<priority>"
}
```

### `PUT /api/v1/queue/{queue_id}/complete`

**Purpose:** Complete Visit. Complete patient visit

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `queue_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `QueueResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/queue/{queue_id}/complete" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "patient_phone": "+2348000000000",
  "patient_date_of_birth": "2026-07-31",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "appointment_time": "<appointment_time>",
  "facility_slug": "example-hospital",
  "department": "<department>",
  "status": "<status>",
  "queue_number": 1,
  "priority": "<priority>"
}
```

### `PUT /api/v1/queue/{queue_id}/start`

**Purpose:** Start Visit. Start patient visit

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `queue_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `QueueResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/queue/{queue_id}/start" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "patient_phone": "+2348000000000",
  "patient_date_of_birth": "2026-07-31",
  "appointment_id": "00000000-0000-0000-0000-000000000000",
  "appointment_time": "<appointment_time>",
  "facility_slug": "example-hospital",
  "department": "<department>",
  "status": "<status>",
  "queue_number": 1,
  "priority": "<priority>"
}
```

## Radiology

### `GET /api/v1/radiology`

**Purpose:** Get Radiology Orders. Paginated list of radiology orders

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RADIOLOGIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |
| `facility_slug` | query | no | `string` or `null` |
| `status` | query | no | `string` or `null` |
| `patient_id` | query | no | `string` or `null` |
| `branch_id` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `RadiologyResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/radiology" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "patient_id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "modality": "<modality>",
    "body_part": "<body_part>",
    "clinical_notes": "<clinical_notes>",
    "status": "<status>",
    "requested_by": "<requested_by>",
    "radiologist_id": "00000000-0000-0000-0000-000000000000",
    "report": "<report>",
    "report_date": "2026-07-31",
    "request_date": "2026-07-31"
  }
]
```

### `POST /api/v1/radiology`

**Purpose:** Create Radiology Order. Create a new radiology order

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `RadiologyCreate`.

**Success:** HTTP `201`; response schema `RadiologyResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

- Branch access is constrained by the authenticated user's scope.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/radiology" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"patient_id":"00000000-0000-0000-0000-000000000000","facility_slug":"example-hospital","modality":"<modality>","body_part":"<body_part>","clinical_notes":"<clinical_notes>","department_id":"00000000-0000-0000-0000-000000000000","branch_id":"00000000-0000-0000-0000-000000000000"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "modality": "<modality>",
  "body_part": "<body_part>",
  "clinical_notes": "<clinical_notes>",
  "status": "<status>",
  "requested_by": "<requested_by>",
  "radiologist_id": "00000000-0000-0000-0000-000000000000",
  "report": "<report>",
  "report_date": "2026-07-31",
  "request_date": "2026-07-31"
}
```

### `GET /api/v1/radiology/{order_id}`

**Purpose:** Get Radiology Order. Get radiology order by ID

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RADIOLOGIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `order_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `RadiologyResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/radiology/{order_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "modality": "<modality>",
  "body_part": "<body_part>",
  "clinical_notes": "<clinical_notes>",
  "status": "<status>",
  "requested_by": "<requested_by>",
  "radiologist_id": "00000000-0000-0000-0000-000000000000",
  "report": "<report>",
  "report_date": "2026-07-31",
  "request_date": "2026-07-31"
}
```

### `PUT /api/v1/radiology/{order_id}`

**Purpose:** Update Radiology Order. Update radiology order

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `RADIOLOGIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `order_id` | path | yes | `string` |

**Request body:** `application/json` using `RadiologyUpdate`.

**Success:** HTTP `200`; response schema `RadiologyResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/radiology/{order_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"status":"<status>","radiologist_id":"00000000-0000-0000-0000-000000000000","clinical_notes":"<clinical_notes>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "modality": "<modality>",
  "body_part": "<body_part>",
  "clinical_notes": "<clinical_notes>",
  "status": "<status>",
  "requested_by": "<requested_by>",
  "radiologist_id": "00000000-0000-0000-0000-000000000000",
  "report": "<report>",
  "report_date": "2026-07-31",
  "request_date": "2026-07-31"
}
```

### `PUT /api/v1/radiology/{order_id}/report`

**Purpose:** Add Radiology Report. Add or update radiology report

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `RADIOLOGIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `order_id` | path | yes | `string` |

**Request body:** `application/json` using `RadiologyReport`.

**Success:** HTTP `200`; response schema `RadiologyResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/radiology/{order_id}/report" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"report":"<report>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "modality": "<modality>",
  "body_part": "<body_part>",
  "clinical_notes": "<clinical_notes>",
  "status": "<status>",
  "requested_by": "<requested_by>",
  "radiologist_id": "00000000-0000-0000-0000-000000000000",
  "report": "<report>",
  "report_date": "2026-07-31",
  "request_date": "2026-07-31"
}
```

## Referrals

### `GET /api/v1/referrals`

**Purpose:** Get Referrals. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `department_id` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `ReferralResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/referrals" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "patient_id": "00000000-0000-0000-0000-000000000000",
    "from_department_id": "00000000-0000-0000-0000-000000000000",
    "to_department_id": "00000000-0000-0000-0000-000000000000",
    "reason": "<reason>",
    "priority": "<priority>",
    "notes": "<notes>",
    "status": "<status>",
    "created_by": "<created_by>",
    "accepted_by": "<accepted_by>",
    "completed_by": "<completed_by>"
  }
]
```

### `POST /api/v1/referrals`

**Purpose:** Create Referral. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `ReferralCreate`.

**Success:** HTTP `201`; response schema `ReferralResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/referrals" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"patient_id":"00000000-0000-0000-0000-000000000000","to_department_id":"00000000-0000-0000-0000-000000000000","reason":"<reason>","priority":"routine","notes":"<notes>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "from_department_id": "00000000-0000-0000-0000-000000000000",
  "to_department_id": "00000000-0000-0000-0000-000000000000",
  "reason": "<reason>",
  "priority": "<priority>",
  "notes": "<notes>",
  "status": "<status>",
  "created_by": "<created_by>",
  "accepted_by": "<accepted_by>",
  "completed_by": "<completed_by>"
}
```

### `PUT /api/v1/referrals/{referral_id}/accept`

**Purpose:** Accept Referral. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `referral_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `ReferralResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/referrals/{referral_id}/accept" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "from_department_id": "00000000-0000-0000-0000-000000000000",
  "to_department_id": "00000000-0000-0000-0000-000000000000",
  "reason": "<reason>",
  "priority": "<priority>",
  "notes": "<notes>",
  "status": "<status>",
  "created_by": "<created_by>",
  "accepted_by": "<accepted_by>",
  "completed_by": "<completed_by>"
}
```

### `PUT /api/v1/referrals/{referral_id}/complete`

**Purpose:** Complete Referral. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `referral_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `ReferralResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/referrals/{referral_id}/complete" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "from_department_id": "00000000-0000-0000-0000-000000000000",
  "to_department_id": "00000000-0000-0000-0000-000000000000",
  "reason": "<reason>",
  "priority": "<priority>",
  "notes": "<notes>",
  "status": "<status>",
  "created_by": "<created_by>",
  "accepted_by": "<accepted_by>",
  "completed_by": "<completed_by>"
}
```

## Reports

### `GET /api/v1/reports/departments`

**Purpose:** Get Department Activity Report. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `date_from` | query | no | `string` or `null` |
| `date_to` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema `DepartmentActivityReport`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/reports/departments" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "facility_slug": "example-hospital",
  "date_from": "2026-07-31",
  "date_to": "2026-07-31",
  "departments": [
    {
      "department": "<department>",
      "module": "<module>",
      "total": 1,
      "completed": 1,
      "pending": 1,
      "by_status": {}
    }
  ],
  "generated_at": "<generated_at>"
}
```

### `GET /api/v1/reports/inventory`

**Purpose:** Get Inventory Detail Report. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `PHARMACIST`.

**Request body:** none.

**Success:** HTTP `200`; response schema `InventoryDetailReport`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/reports/inventory" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "facility_slug": "example-hospital",
  "active_items": 1,
  "low_stock_items": 1,
  "stock_value": 1.0,
  "reorder_items": [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "name": "<name>",
      "sku": "<sku>",
      "category": "<category>",
      "current_stock": 1,
      "reorder_level": 1,
      "reorder_quantity": 1,
      "unit": "<unit>",
      "stock_value": 1.0
    }
  ],
  "by_category": [
    {
      "label": "<label>",
      "value": 1.0,
      "metadata": {}
    }
  ],
  "generated_at": "<generated_at>"
}
```

### `GET /api/v1/reports/operations`

**Purpose:** Get Operations Report. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `date_from` | query | no | `string` or `null` |
| `date_to` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema `OperationsReport`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/reports/operations" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "facility_slug": "example-hospital",
  "date_from": "2026-07-31",
  "date_to": "2026-07-31",
  "queue": {
    "total": 1,
    "by_status": {}
  },
  "appointments": {
    "total": 1,
    "by_status": {}
  },
  "active_tasks_by_role": [
    {
      "label": "<label>",
      "value": 1.0,
      "metadata": {}
    }
  ],
  "high_priority_tasks": [
    {
      "label": "<label>",
      "value": 1.0,
      "metadata": {}
    }
  ],
  "generated_at": "<generated_at>"
}
```

### `GET /api/v1/reports/revenue`

**Purpose:** Get Revenue Report. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `date_from` | query | no | `string` or `null` |
| `date_to` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema `RevenueDetailReport`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/reports/revenue" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "facility_slug": "example-hospital",
  "date_from": "2026-07-31",
  "date_to": "2026-07-31",
  "invoice_count": 1,
  "paid_invoice_count": 1,
  "outstanding_invoice_count": 1,
  "invoiced_total": 1.0,
  "collected_total": 1.0,
  "outstanding_total": 1.0,
  "receipt_count": 1,
  "payment_methods": [
    {
      "label": "<label>",
      "value": 1.0,
      "metadata": {}
    }
  ],
  "invoice_statuses": [
    {
      "label": "<label>",
      "value": 1.0,
      "metadata": {}
    }
  ]
}
```

### `GET /api/v1/reports/summary`

**Purpose:** Get Report Summary. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `date_from` | query | no | `string` or `null` |
| `date_to` | query | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema `FacilityReportSummary`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/reports/summary" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "facility_slug": "example-hospital",
  "date_from": "2026-07-31",
  "date_to": "2026-07-31",
  "patients": {
    "total": 1,
    "by_status": {}
  },
  "appointments": {
    "total": 1,
    "by_status": {}
  },
  "consultations": {
    "total": 1,
    "by_status": {}
  },
  "admissions": {
    "total": 1,
    "by_status": {}
  },
  "queue": {
    "total": 1,
    "by_status": {}
  },
  "laboratory": {
    "total": 1,
    "by_status": {}
  },
  "radiology": {
    "total": 1,
    "by_status": {}
  },
  "billing": {
    "invoice_count": 1,
    "outstanding_invoice_count": 1,
    "invoiced_total": 1.0,
    "payments_total": 1.0,
    "outstanding_total": 1.0
  },
  "inventory": {
    "active_items": 1,
    "low_stock_items": 1,
    "stock_value": 1.0
  }
}
```

## Staff Chat

### `GET /api/v1/chat/conversations`

**Purpose:** List Conversations. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `ChatConversationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/chat/conversations" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "participant_ids": [
      "<participant_ids>"
    ],
    "other_staff": {
      "id": "00000000-0000-0000-0000-000000000000",
      "username": "<username>",
      "full_name": "<full_name>",
      "role": "<role>",
      "department": "<department>",
      "is_online": true,
      "last_active": "<last_active>"
    },
    "last_message": {
      "id": "00000000-0000-0000-0000-000000000000",
      "conversation_id": "00000000-0000-0000-0000-000000000000",
      "facility_slug": "example-hospital",
      "sender_id": "00000000-0000-0000-0000-000000000000",
      "sender": {
        "id": null,
        "username": null,
        "full_name": null,
        "role": null
      },
      "content": null,
      "message_type": "<message_type>",
      "is_read": true,
      "created_at": "<created_at>"
    },
    "unread_count": 1,
    "last_message_at": "<last_message_at>",
    "created_at": "<created_at>"
  }
]
```

### `POST /api/v1/chat/conversations`

**Purpose:** Create Or Get Conversation. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Request body:** `application/json` using `ConversationCreate`.

**Success:** HTTP `201`; response schema `ChatConversationResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/chat/conversations" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"participant_id":"00000000-0000-0000-0000-000000000000"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "participant_ids": [
    "<participant_ids>"
  ],
  "other_staff": {
    "id": "00000000-0000-0000-0000-000000000000",
    "username": "<username>",
    "full_name": "<full_name>",
    "role": "<role>",
    "department": "<department>",
    "is_online": true,
    "last_active": "<last_active>"
  },
  "last_message": {
    "id": "00000000-0000-0000-0000-000000000000",
    "conversation_id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "sender_id": "00000000-0000-0000-0000-000000000000",
    "sender": {
      "id": "00000000-0000-0000-0000-000000000000",
      "username": "<username>",
      "full_name": "<full_name>",
      "role": "<role>"
    },
    "content": "<content>",
    "message_type": "<message_type>",
    "is_read": true,
    "created_at": "<created_at>"
  },
  "unread_count": 1,
  "last_message_at": "<last_message_at>",
  "created_at": "<created_at>"
}
```

### `GET /api/v1/chat/conversations/{conversation_id}/messages`

**Purpose:** List Messages. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `conversation_id` | path | yes | `string` |
| `limit` | query | no | `integer` |
| `offset` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `ChatMessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/chat/conversations/{conversation_id}/messages" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "conversation_id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "sender_id": "00000000-0000-0000-0000-000000000000",
    "sender": {
      "id": "00000000-0000-0000-0000-000000000000",
      "username": "<username>",
      "full_name": "<full_name>",
      "role": "<role>"
    },
    "content": "<content>",
    "message_type": "<message_type>",
    "is_read": true,
    "created_at": "<created_at>"
  }
]
```

### `POST /api/v1/chat/conversations/{conversation_id}/messages`

**Purpose:** Send Message. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `conversation_id` | path | yes | `string` |
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `ChatMessageCreate`.

**Success:** HTTP `201`; response schema `ChatMessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/chat/conversations/{conversation_id}/messages" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"content":"<content>","message_type":"text","file_name":"<file_name>","file_url":"<file_url>","file_size":1,"file_type":"<file_type>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "conversation_id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "sender_id": "00000000-0000-0000-0000-000000000000",
  "sender": {
    "id": "00000000-0000-0000-0000-000000000000",
    "username": "<username>",
    "full_name": "<full_name>",
    "role": "<role>"
  },
  "content": "<content>",
  "message_type": "<message_type>",
  "is_read": true,
  "created_at": "<created_at>"
}
```

### `PUT /api/v1/chat/conversations/{conversation_id}/read`

**Purpose:** Mark Conversation Read. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `conversation_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `ChatUnreadCountResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/chat/conversations/{conversation_id}/read" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "unread_count": 1
}
```

### `GET /api/v1/chat/files/{filename}`

**Purpose:** Download Chat File. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `filename` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/chat/files/{filename}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `GET /api/v1/chat/health`

**Purpose:** Chat Health. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`.

**Request body:** none.

**Success:** HTTP `200`; response schema Not declared.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/chat/health" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape:** not constrained by a declared JSON response model.

### `GET /api/v1/chat/staff`

**Purpose:** List Chat Staff. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `ChatStaffResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/chat/staff" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "username": "<username>",
    "full_name": "<full_name>",
    "role": "<role>",
    "department": "<department>",
    "is_online": true,
    "last_active": "<last_active>"
  }
]
```

### `GET /api/v1/chat/unread-count`

**Purpose:** Get Unread Count. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Request body:** none.

**Success:** HTTP `200`; response schema `ChatUnreadCountResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/chat/unread-count" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "unread_count": 1
}
```

### `POST /api/v1/chat/upload`

**Purpose:** Upload Chat File. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `BRANCH_ADMIN`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Request body:** `multipart/form-data` using `Body_upload_chat_file_api_v1_chat_upload_post`.

**Success:** HTTP `201`; response schema `ChatUploadResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/chat/upload" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "file_url": "<file_url>",
  "file_name": "<file_name>",
  "file_size": 1,
  "file_type": "<file_type>"
}
```

## Suppliers

### `GET /api/v1/suppliers`

**Purpose:** Get Suppliers. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `PHARMACIST`, `STORE_KEEPER`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `search` | query | no | `string` or `null` |
| `active_only` | query | no | `boolean` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `SupplierResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/suppliers" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "name": "<name>",
    "contact_person": "<contact_person>",
    "email": "<email>",
    "phone": "+2348000000000",
    "address": "<address>",
    "is_active": true,
    "created_at": "<created_at>",
    "updated_at": "2026-07-31"
  }
]
```

### `POST /api/v1/suppliers`

**Purpose:** Create Supplier. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `PHARMACIST`, `STORE_KEEPER`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `SupplierCreate`.

**Success:** HTTP `201`; response schema `SupplierResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/suppliers" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","contact_person":"<contact_person>","email":"staff@example.invalid","phone":"+2348000000000","address":"<address>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "name": "<name>",
  "contact_person": "<contact_person>",
  "email": "<email>",
  "phone": "+2348000000000",
  "address": "<address>",
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `DELETE /api/v1/suppliers/{supplier_id}`

**Purpose:** Deactivate Supplier. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `PHARMACIST`, `STORE_KEEPER`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `supplier_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X DELETE \
  "https://<tenant>.app.his.pro/api/v1/suppliers/{supplier_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/suppliers/{supplier_id}`

**Purpose:** Get Supplier. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `PHARMACIST`, `STORE_KEEPER`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `supplier_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `SupplierResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/suppliers/{supplier_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "name": "<name>",
  "contact_person": "<contact_person>",
  "email": "<email>",
  "phone": "+2348000000000",
  "address": "<address>",
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `PUT /api/v1/suppliers/{supplier_id}`

**Purpose:** Update Supplier. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `PHARMACIST`, `STORE_KEEPER`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `supplier_id` | path | yes | `string` |

**Request body:** `application/json` using `SupplierUpdate`.

**Success:** HTTP `200`; response schema `SupplierResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/suppliers/{supplier_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"name":"<name>","contact_person":"<contact_person>","email":"staff@example.invalid","phone":"+2348000000000","address":"<address>","is_active":true}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "name": "<name>",
  "contact_person": "<contact_person>",
  "email": "<email>",
  "phone": "+2348000000000",
  "address": "<address>",
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

## Tasks

### `GET /api/v1/tasks`

**Purpose:** Get Tasks. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BILLING`, `DOCTOR`, `LAB_TECH`, `NURSE`, `PHARMACIST`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `role` | query | no | `string` or `null` |
| `limit` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema `TaskListResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/tasks" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "tasks": [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "title": "<title>",
      "description": "<description>",
      "role": "<role>",
      "module": "<module>",
      "priority": "<priority>",
      "status": "<status>",
      "source_type": "<source_type>",
      "source_id": "00000000-0000-0000-0000-000000000000",
      "action_path": "<action_path>",
      "created_at": "<created_at>"
    }
  ],
  "total": 1,
  "role": "<role>",
  "generated_at": "<generated_at>"
}
```

## Users

### `GET /api/v1/users/me`

**Purpose:** Get Current User Profile. Get current user's profile

**Access:** Authenticated user.

**Request body:** none.

**Success:** HTTP `200`; response schema `UserResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/users/me" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "username": "<username>",
  "email": "<email>",
  "role": "<role>",
  "first_name": "<first_name>",
  "last_name": "<last_name>",
  "facility_slug": "example-hospital",
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `PUT /api/v1/users/me`

**Purpose:** Update Current User. Update current user's profile

**Access:** Authenticated user.

**Request body:** `application/json` using `UserUpdate`.

**Success:** HTTP `200`; response schema `UserResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/users/me" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"username":"<username>","email":"staff@example.invalid","first_name":"<first_name>","last_name":"<last_name>","phone":"+2348000000000"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "username": "<username>",
  "email": "<email>",
  "role": "<role>",
  "first_name": "<first_name>",
  "last_name": "<last_name>",
  "facility_slug": "example-hospital",
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `POST /api/v1/users/me/change-password`

**Purpose:** Change Password. Change current user's password

**Access:** Authenticated user.

**Request body:** `application/json` using `ChangePasswordRequest`.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/users/me/change-password" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"current_password":"<strong-password>","new_password":"<strong-password>"}'
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

### `GET /api/v1/users/{user_id}`

**Purpose:** Get User. Get user by ID (admin only)

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `user_id` | path | yes | `string` |

**Request body:** none.

**Success:** HTTP `200`; response schema `UserResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/users/{user_id}" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "username": "<username>",
  "email": "<email>",
  "role": "<role>",
  "first_name": "<first_name>",
  "last_name": "<last_name>",
  "facility_slug": "example-hospital",
  "is_active": true,
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `PUT /api/v1/users/{user_id}/activate`

**Purpose:** Toggle User Activation. Activate or deactivate a user (admin only)

**Access:** Authenticated; roles: `ADMIN`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `user_id` | path | yes | `string` |
| `activate` | query | no | `boolean` |

**Request body:** none.

**Success:** HTTP `200`; response schema `MessageResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/users/{user_id}/activate" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "message": "<message>"
}
```

## Wards

### `GET /api/v1/wards/admissions`

**Purpose:** List Admissions. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `status` | query | no | `string` or `null` |
| `patient_id` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `WardAdmissionResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/wards/admissions" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "patient_id": "00000000-0000-0000-0000-000000000000",
    "patient_name": "<patient_name>",
    "patient_phone": "+2348000000000",
    "bed_id": "00000000-0000-0000-0000-000000000000",
    "bed_number": "<bed_number>",
    "ward_name": "<ward_name>",
    "reason": "<reason>",
    "acuity": "<acuity>",
    "status": "<status>",
    "observations": [
      {}
    ]
  }
]
```

### `POST /api/v1/wards/admissions`

**Purpose:** Admit Patient. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `WardAdmissionCreate`.

**Success:** HTTP `201`; response schema `WardAdmissionResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/wards/admissions" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"patient_id":"00000000-0000-0000-0000-000000000000","bed_id":"00000000-0000-0000-0000-000000000000","ward_name":"<ward_name>","reason":"<reason>","acuity":"normal"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "patient_phone": "+2348000000000",
  "bed_id": "00000000-0000-0000-0000-000000000000",
  "bed_number": "<bed_number>",
  "ward_name": "<ward_name>",
  "reason": "<reason>",
  "acuity": "<acuity>",
  "status": "<status>",
  "observations": [
    {}
  ]
}
```

### `PUT /api/v1/wards/admissions/{admission_id}`

**Purpose:** Update Admission. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `admission_id` | path | yes | `string` |

**Request body:** `application/json` using `WardAdmissionUpdate`.

**Success:** HTTP `200`; response schema `WardAdmissionResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/wards/admissions/{admission_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"bed_id":"00000000-0000-0000-0000-000000000000","ward_name":"<ward_name>","reason":"<reason>","acuity":"<acuity>","status":"<status>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "patient_phone": "+2348000000000",
  "bed_id": "00000000-0000-0000-0000-000000000000",
  "bed_number": "<bed_number>",
  "ward_name": "<ward_name>",
  "reason": "<reason>",
  "acuity": "<acuity>",
  "status": "<status>",
  "observations": [
    {}
  ]
}
```

### `POST /api/v1/wards/admissions/{admission_id}/discharge`

**Purpose:** Discharge Patient. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `admission_id` | path | yes | `string` |
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** none.

**Success:** HTTP `200`; response schema `WardAdmissionResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/wards/admissions/{admission_id}/discharge" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>"
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "patient_phone": "+2348000000000",
  "bed_id": "00000000-0000-0000-0000-000000000000",
  "bed_number": "<bed_number>",
  "ward_name": "<ward_name>",
  "reason": "<reason>",
  "acuity": "<acuity>",
  "status": "<status>",
  "observations": [
    {}
  ]
}
```

### `POST /api/v1/wards/admissions/{admission_id}/observations`

**Purpose:** Add Observation. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `admission_id` | path | yes | `string` |
| `Idempotency-Key` | header | no | `string` or `null` |

**Request body:** `application/json` using `NursingObservationCreate`.

**Success:** HTTP `200`; response schema `WardAdmissionResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

- A valid `Idempotency-Key` is required and replays are tenant-scoped.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/wards/admissions/{admission_id}/observations" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"vital_signs":{},"note":"<note>","medication_round":"<medication_round>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "patient_id": "00000000-0000-0000-0000-000000000000",
  "patient_name": "<patient_name>",
  "patient_phone": "+2348000000000",
  "bed_id": "00000000-0000-0000-0000-000000000000",
  "bed_number": "<bed_number>",
  "ward_name": "<ward_name>",
  "reason": "<reason>",
  "acuity": "<acuity>",
  "status": "<status>",
  "observations": [
    {}
  ]
}
```

### `GET /api/v1/wards/beds`

**Purpose:** List Beds. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `BRANCH_ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `ward_name` | query | no | `string` or `null` |
| `status` | query | no | `string` or `null` |
| `page` | query | no | `integer` |
| `per_page` | query | no | `integer` |

**Request body:** none.

**Success:** HTTP `200`; response schema Array of `WardBedResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X GET \
  "https://<tenant>.app.his.pro/api/v1/wards/beds" \
  -H "Authorization: Bearer <access-token>"
```

**Example response shape**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "facility_slug": "example-hospital",
    "ward_name": "<ward_name>",
    "bed_number": "<bed_number>",
    "status": "<status>",
    "notes": "<notes>",
    "created_at": "<created_at>",
    "updated_at": "2026-07-31"
  }
]
```

### `POST /api/v1/wards/beds`

**Purpose:** Create Bed. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `NURSE`.

**Request body:** `application/json` using `WardBedCreate`.

**Success:** HTTP `201`; response schema `WardBedResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X POST \
  "https://<tenant>.app.his.pro/api/v1/wards/beds" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"ward_name":"<ward_name>","bed_number":"<bed_number>","status":"AVAILABLE","notes":"<notes>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "ward_name": "<ward_name>",
  "bed_number": "<bed_number>",
  "status": "<status>",
  "notes": "<notes>",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

### `PUT /api/v1/wards/beds/{bed_id}`

**Purpose:** Update Bed. No additional route description is declared.

**Access:** Authenticated; roles: `ADMIN`, `NURSE`.

**Parameters**

| Name | In | Required | Schema |
|---|---|---:|---|
| `bed_id` | path | yes | `string` |

**Request body:** `application/json` using `WardBedUpdate`.

**Success:** HTTP `200`; response schema `WardBedResponse`.

**Possible errors:** `400` business validation, `401` authentication, `403` authorization, `404` missing or inaccessible resource, `409` idempotency/state conflict where applicable, `422` schema validation, `429` rate limit.

**Example request**

```bash
curl -X PUT \
  "https://<tenant>.app.his.pro/api/v1/wards/beds/{bed_id}" \
  -H "Authorization: Bearer <access-token>" \
  -H "Idempotency-Key: <unique-operation-key>" \
  -H "Content-Type: application/json" \
  --data '{"ward_name":"<ward_name>","bed_number":"<bed_number>","status":"<status>","notes":"<notes>"}'
```

**Example response shape**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "facility_slug": "example-hospital",
  "ward_name": "<ward_name>",
  "bed_number": "<bed_number>",
  "status": "<status>",
  "notes": "<notes>",
  "created_at": "<created_at>",
  "updated_at": "2026-07-31"
}
```

## Implementation Notes

- FastAPI documentation routes are disabled in production, but the OpenAPI
  document remains registered at `/api/v1/openapi.json` in the current app.
  Restrict it at the edge if public schema discovery is not desired.
- Authentication is implemented through route dependencies plus JWT/session
  middleware, so OpenAPI does not currently expose a standard security scheme.
- Several endpoints return a bare array while accepting pagination inputs;
  callers do not receive total-count metadata.
