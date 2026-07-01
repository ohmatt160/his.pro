# HIS.Pro System Overview

This document describes the HIS.Pro application as it currently exists in the codebase. It is meant to be the working system map for engineering, production readiness, onboarding, audits, and future feature work.

## 1. Product Summary

HIS.Pro is a multi-tenant health information system for hospitals, clinics, medical campuses, branches, and growing healthcare groups. The product lets a facility create a workspace, select the modules it needs, onboard staff, register patients, run daily operations, and expand into branch-level workspaces as the organization grows.

The core product promise is:

- one secure workspace per healthcare tenant;
- branch-level isolation where a facility has multiple branches;
- configurable modules so a hospital can start small and add more features later;
- role-based access so staff see only the work they are allowed to perform;
- clinical, operational, billing, notification, and reporting workflows in one system.

## 2. Repository Layout

Active backend:

```text
C:\Users\mattw\Downloads\new-his
```

Active frontend:

```text
C:\Users\mattw\Downloads\new-his\app\templates\initial frontend
```

Old frontend copy:

```text
C:\Users\mattw\Downloads\new-his\app\templates\healthsuite-pro copy
```

The old `healthsuite-pro copy` directory is not the active frontend and should not be used for new work.

Important backend directories:

```text
app/main.py                 FastAPI application factory and middleware/router registration
app/extensions.py           SQLAlchemy engine, sessions, pooling, slow query logging
app/models/                 SQLAlchemy models
app/routes/                 FastAPI routers
app/schemas/                Pydantic request/response schemas
app/services/               Business logic and workflow services
app/middleware/             JWT, module access, security, CORS, rate limiting
app/utils/                  Dependencies, validation, branch scope, schema helpers
migrations/                 Alembic migration files
tests/                      Backend tests
scripts/                    Migration and performance scripts
```

Important frontend directories:

```text
src/App.tsx                 Application routing
src/components/AppShell.tsx Main authenticated workspace layout/sidebar
src/context/AuthContext.tsx Frontend auth state
src/api/client.ts           API client, token refresh, error sanitization
src/lib/modules.ts          Module catalog and module access helpers
src/lib/role-access.ts      Frontend role access mapping
src/lib/facility-workspace.ts Workspace route helpers
src/pages/                  Workspace pages and landing/legal pages
src/test/                   Frontend tests
api/                        Vercel proxy/serverless API helpers
```

## 3. High-Level Architecture

HIS.Pro uses a split deployment:

- Frontend: React + Vite on Vercel.
- Backend: FastAPI on Hugging Face Spaces or another container platform.
- Database: SQLite for local development; PostgreSQL recommended for staging and production.
- Optional Redis: available for supporting infrastructure such as rate limiting/session/cache patterns.

Runtime request flow:

```text
Browser
  -> Vercel React app
  -> /api/v1 relative frontend request
  -> Vercel proxy or direct configured backend URL
  -> FastAPI /api/v1 route
  -> Middleware stack
  -> Route dependency auth and role checks
  -> Service layer
  -> SQLAlchemy ORM
  -> Database
```

The frontend defaults to `/api/v1` through `src/api/client.ts`. In production this can be routed by Vercel to the backend, keeping browser requests same-origin where configured.

## 4. Backend Runtime

Backend entry point:

```text
app/main.py
```

The application is created by `create_app()`. It:

- initializes tenant hooks;
- creates the FastAPI app;
- configures exact-origin CORS;
- configures database session middleware;
- adds request timing headers;
- registers security, module, JWT, CORS, and rate limit middleware;
- registers global error handlers;
- registers all `/api/v1` routers;
- serves static assets and SPA fallback when static frontend assets are present.

Application lifespan:

- creates development tables when not production/staging;
- runs schema compatibility helpers in development;
- backfills `facility_id` values from `facility_slug`;
- initializes Redis if `REDIS_URL` is configured;
- initializes email service.

## 5. Middleware Stack

The backend middleware stack includes:

- `ForceCORSHeadersMiddleware`: ensures credentialed CORS headers are present on middleware-generated responses.
- `CORSMiddleware`: allows exact configured origins with credentials.
- `RateLimitMiddleware`: limits sensitive or high-volume routes.
- `InputValidationMiddleware`: rejects suspicious input patterns.
- `SecurityHeadersMiddleware`: adds browser security headers.
- `ModuleAccessMiddleware`: blocks access to disabled modules or modules the user role cannot use.
- `JWTMiddleware`: verifies access tokens from cookies or authorization headers and attaches token payload to request state.
- database session middleware: commits on success, rolls back on failure, removes scoped session after request.
- request timing middleware: adds `Server-Timing` and logs slow requests.

## 6. Authentication and Session Model

Primary auth routes:

```text
POST /api/v1/auth/register
POST /api/v1/auth/ensure
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
POST /api/v1/auth/logout-everywhere
GET  /api/v1/auth/sessions
POST /api/v1/auth/verify
```

Auth behavior:

- Passwords are hashed using Werkzeug PBKDF2-SHA256 with salt.
- Login returns access and refresh JWTs.
- Auth cookies are HttpOnly.
- Access token cookie name: `hispro_access_token`.
- Refresh token cookie name: `hispro_refresh_token`.
- JWTs include subject (`sub`), JWT ID (`jti`), token type, optional session ID (`sid`), and optional tenant ID (`tid`).
- Refresh token rotation is handled through `SessionService.rotate_refresh_token`.
- Logout revokes the current JWT ID and current session.
- Logout everywhere revokes all active sessions for the user.
- Active sessions track user agent, IP address, last seen time, expiry, and revocation state.

Frontend auth behavior:

- `AuthContext` manages current auth state.
- `src/api/client.ts` sends credentials with requests.
- 401 responses on refreshable routes trigger `/auth/refresh`.
- Failed refresh clears client state and dispatches `hispro:auth-expired`.
- Error messages shown to users are sanitized into natural language.

## 7. Multi-Tenant Architecture

The tenant root is `Facility`.

Model:

```text
app/models/facility.py
```

Important facility fields:

- `id`
- `name`
- `type`
- `slug`
- `hospital_type`
- `departments`
- `modules`
- `settings`
- `is_active`

Tenant-scoped models use `facility_slug`, and many also use `facility_id`.

Tenant helper service:

```text
app/services/tenant_service.py
```

Responsibilities:

- defines tenant-scoped model list;
- resolves facility ID by slug;
- populates `facility_id` before flush when only `facility_slug` is set;
- backfills existing tenant-scoped rows with `facility_id`.

Branch scope helper:

```text
app/utils/branch_scope.py
```

Responsibilities:

- requires a user to have a facility slug;
- determines effective branch for non-main-admin users;
- applies facility and branch filters to queries;
- verifies a row belongs to the current facility and branch;
- returns 404 for cross-tenant and cross-branch resources rather than leaking existence.

## 8. Branch / Multi-Clinic Architecture

Branches are separate operational workspaces under one facility tenant.

Model:

```text
app/models/branch.py
```

Important branch fields:

- `facility_id`
- `facility_slug`
- `name`
- `slug`
- `location`
- `address`
- `phone`
- `email`
- `modules`
- `settings`
- `is_public`
- `is_active`

Branch uniqueness:

```text
facility_slug + slug
```

Branch URL pattern:

```text
/:facilitySlug/branches/:branchSlug/login
/:facilitySlug/branches/:branchSlug/dashboard
/:facilitySlug/branches/:branchSlug/dashboard/:module
```

Main facility URL pattern:

```text
/:facilitySlug/login
/dashboard/:facilitySlug
/dashboard/:facilitySlug/:module
```

Branch admin rules:

- Branch admins authenticate only against their assigned branch portal.
- Branch admins should see branch-scoped workspace data.
- Branch admins use the branch module list, not the main facility module list.
- Branch admins should not manage main facility details or hospital type.
- Main facility admin manages facility-level configuration and branch creation.

## 9. Department vs Branch

The system currently contains both:

- Branches: physical or operational sub-workspaces under a facility, such as campus, clinic, building, or hospital branch.
- Departments: legacy/public-profile/service grouping data stored on the facility JSON field.

The current branch model is the stronger isolation boundary. Departments are useful as public-facing clinic/service labels and referral destinations, but branch is the operational tenant scope.

## 10. Roles and Access Control

Backend roles are uppercase:

```text
ADMIN
BRANCH_ADMIN
DOCTOR
NURSE
LAB_TECH
PHARMACIST
RECEPTIONIST
```

Frontend roles are normalized in places to lowercase:

```text
admin
branch_admin
doctor
nurse
reception
pharmacist
lab
```

Core access layers:

- Frontend route guards: `ProtectedRoute`.
- Frontend module guards: `ModuleRoute`.
- Frontend role mapping: `src/lib/role-access.ts`.
- Backend module middleware: `ModuleAccessMiddleware`.
- Backend route dependencies: `get_current_user`, role helpers, and route-specific checks.
- Tenant query helpers: `tenant_query`, `require_tenant_row`, `ensure_patient_branch_access`.

Module access is enforced both client-side for UX and backend-side for security.

## 11. Module System

Module catalog:

```text
src/lib/modules.ts
app/models/facility.py
app/middleware/module_access.py
```

Available modules:

1. Reception & Registration (`reception`)
2. Shared Patient Record (`records`)
3. Doctors & Consultations (`consultations`)
4. Nursing & Wards (`nursing`)
5. Laboratory (`lab`)
6. Pharmacy (`pharmacy`)
7. Billing & Claims (`billing`)
8. Radiology (`radiology`)
9. Inventory & Stores (`inventory`)
10. Reports (`reports`)

Facility-level modules live on:

```text
Facility.modules
```

Branch-level modules live on:

```text
Branch.modules
```

Module behavior:

- A single hospital can use the facility-level selected modules.
- A multi-branch facility can let each branch use its own module set.
- Disabled modules are hidden from navigation.
- Disabled modules are blocked by backend middleware even if a user manually enters a route.
- Module aliases map older route labels such as `appointments`, `patients`, and `medical_records` to canonical modules.

## 12. Signup and Workspace Creation Flow

Frontend pages:

```text
/get-started
/setting-up
/workspace-ready/:facilitySlug
```

Expected flow:

```text
Hospital admin fills setup form
  -> frontend authenticates/ensures setup user
  -> frontend creates or ensures facility
  -> backend creates facility and admin user link
  -> workspace URL is shown
  -> admin visits login URL
  -> admin logs in
  -> dashboard loads after authentication
```

Facility login URL:

```text
/:facilitySlug/login
```

Branch login URL:

```text
/:facilitySlug/branches/:branchSlug/login
```

The workspace should not skip login when a user is unauthenticated.

## 13. Frontend Routing

Main routing file:

```text
src/App.tsx
```

Public routes:

```text
/
/get-started
/privacy
/terms
/dpa
/login
/login/:facilitySlug
/:facilitySlug/login
/:facilitySlug/branches/:branchSlug/login
/:facilitySlug
/setting-up
/workspace-ready/:facilitySlug
/hospital/:facilitySlug
```

Main dashboard routes:

```text
/dashboard/:facilitySlug
/dashboard/:facilitySlug/staff
/dashboard/:facilitySlug/patients
/dashboard/:facilitySlug/patients/:patientId/timeline
/dashboard/:facilitySlug/appointments
/dashboard/:facilitySlug/billing
/dashboard/:facilitySlug/laboratory
/dashboard/:facilitySlug/pharmacy
/dashboard/:facilitySlug/radiology
/dashboard/:facilitySlug/inventory
/dashboard/:facilitySlug/records
/dashboard/:facilitySlug/alerts
/dashboard/:facilitySlug/chat
/dashboard/:facilitySlug/audit-logs
/dashboard/:facilitySlug/settings
/dashboard/:facilitySlug/suppliers
/dashboard/:facilitySlug/queue
/dashboard/:facilitySlug/consultations
/dashboard/:facilitySlug/wards
/dashboard/:facilitySlug/reports
/dashboard/:facilitySlug/public-profile
```

Branch dashboard routes:

```text
/:facilitySlug/branches/:branchSlug/dashboard
/:facilitySlug/branches/:branchSlug/dashboard/staff
/:facilitySlug/branches/:branchSlug/dashboard/patients
/:facilitySlug/branches/:branchSlug/dashboard/patients/:patientId/timeline
/:facilitySlug/branches/:branchSlug/dashboard/appointments
/:facilitySlug/branches/:branchSlug/dashboard/billing
/:facilitySlug/branches/:branchSlug/dashboard/laboratory
/:facilitySlug/branches/:branchSlug/dashboard/pharmacy
/:facilitySlug/branches/:branchSlug/dashboard/radiology
/:facilitySlug/branches/:branchSlug/dashboard/inventory
/:facilitySlug/branches/:branchSlug/dashboard/records
/:facilitySlug/branches/:branchSlug/dashboard/alerts
/:facilitySlug/branches/:branchSlug/dashboard/chat
/:facilitySlug/branches/:branchSlug/dashboard/audit-logs
/:facilitySlug/branches/:branchSlug/dashboard/settings
/:facilitySlug/branches/:branchSlug/dashboard/suppliers
/:facilitySlug/branches/:branchSlug/dashboard/queue
/:facilitySlug/branches/:branchSlug/dashboard/consultations
/:facilitySlug/branches/:branchSlug/dashboard/wards
/:facilitySlug/branches/:branchSlug/dashboard/reports
/:facilitySlug/branches/:branchSlug/dashboard/public-profile
```

Staff portal routes:

```text
/portal/:facilitySlug
/:facilitySlug/branches/:branchSlug/portal
```

## 14. Navigation and App Shell

Main authenticated layout:

```text
src/components/AppShell.tsx
```

The sidebar is generated from `navItems`. It uses:

- authenticated user role;
- selected facility or branch modules;
- current facility slug;
- current branch slug;
- active alert count;
- unread chat count;
- current workspace metadata.

Navigation items include:

- Dashboard
- My Portal
- Staff & Access
- Messages
- Alerts
- Audit Logs
- Reports
- Public Profile
- Patients
- Reception Queue
- Appointments
- Consultations
- Wards
- Medical Records
- Billing
- Laboratory
- Pharmacy
- Radiology
- Inventory
- Suppliers
- Settings

## 15. Backend API Surface

All APIs are under:

```text
/api/v1
```

Routers currently registered:

- Auth
- Patients
- Appointments
- Laboratory
- Pharmacy
- Billing
- Consultations
- Wards
- EMR
- Users
- Password Reset
- Patient Notifications
- Facilities
- Radiology
- Inventory
- Suppliers
- Reports
- Order Workflow
- Queue
- Alerts
- Dashboard
- Audit Logs
- Files
- Tasks
- Staff Chat
- Referrals
- Public Profile

## 16. Facility, Staff, Branch, and Department APIs

Facilities:

```text
GET    /api/v1/facilities
POST   /api/v1/facilities
POST   /api/v1/facilities/ensure
GET    /api/v1/facilities/workspace/{facility_slug}
GET    /api/v1/facilities/{facility_id}
PUT    /api/v1/facilities/{facility_id}
DELETE /api/v1/facilities/{facility_id}
PUT    /api/v1/facilities/{facility_id}/modules
PUT    /api/v1/facilities/{facility_slug}/settings
```

Branches:

```text
GET    /api/v1/facilities/{facility_slug}/branches
POST   /api/v1/facilities/{facility_slug}/branches
PUT    /api/v1/facilities/{facility_slug}/branches/{branch_id_or_slug}
PUT    /api/v1/facilities/{facility_slug}/branches/{branch_id_or_slug}/modules
DELETE /api/v1/facilities/{facility_slug}/branches/{branch_id_or_slug}
```

Departments:

```text
GET    /api/v1/facilities/{facility_slug}/departments
POST   /api/v1/facilities/{facility_slug}/departments
PUT    /api/v1/facilities/{facility_slug}/departments/{dept_id}
DELETE /api/v1/facilities/{facility_slug}/departments/{dept_id}
```

Staff:

```text
GET  /api/v1/facilities/{facility_slug}/staff
GET  /api/v1/facilities/{facility_slug}/clinicians
POST /api/v1/facilities/{facility_slug}/staff
GET  /api/v1/facilities/{facility_slug}/staff/{login_id}
PUT  /api/v1/facilities/{facility_slug}/staff/{login_id}
```

## 17. Patient and Reception Workflows

Patient APIs:

```text
GET    /api/v1/patients/options
GET    /api/v1/patients
POST   /api/v1/patients
GET    /api/v1/patients/{patient_id}
GET    /api/v1/patients/{patient_id}/timeline
PUT    /api/v1/patients/{patient_id}
DELETE /api/v1/patients/{patient_id}
```

Queue APIs:

```text
GET    /api/v1/queue
POST   /api/v1/queue
GET    /api/v1/queue/{queue_id}
PUT    /api/v1/queue/{queue_id}
DELETE /api/v1/queue/{queue_id}
PUT    /api/v1/queue/{queue_id}/checkin
PUT    /api/v1/queue/{queue_id}/start
PUT    /api/v1/queue/{queue_id}/complete
```

Reception workflow:

```text
Register patient
  -> add to queue or schedule appointment
  -> check in patient
  -> start encounter/visit
  -> complete or clear patient from queue
```

The patient timeline aggregates events such as registration, appointments, consultations, lab/radiology orders, prescriptions, billing, and queue activity.

## 18. Appointment Workflow

Appointment APIs:

```text
GET    /api/v1/appointments
POST   /api/v1/appointments
GET    /api/v1/appointments/{appointment_id}
PUT    /api/v1/appointments/{appointment_id}
DELETE /api/v1/appointments/{appointment_id}
```

Appointment features:

- patient selection;
- clinician selection;
- scheduling by date/time;
- status updates;
- tenant and branch filtering;
- optional notification hooks through patient notification workflows.

## 19. Consultations and Clinical Orders

Consultation APIs:

```text
GET  /api/v1/consultations
POST /api/v1/consultations/start
GET  /api/v1/consultations/{consultation_id}
PUT  /api/v1/consultations/{consultation_id}
POST /api/v1/consultations/{consultation_id}/complete
```

Consultation flow:

```text
Doctor starts consultation
  -> records symptoms, diagnosis, notes, plan
  -> can create lab orders
  -> can create radiology orders
  -> can create prescriptions
  -> completes consultation
```

Order workflow events are tracked separately so downstream modules can show status changes.

## 20. Laboratory Workflow

Laboratory APIs:

```text
GET  /api/v1/laboratory/tests
POST /api/v1/laboratory/tests
GET  /api/v1/laboratory/tests/{test_id}
PUT  /api/v1/laboratory/tests/{test_id}
GET  /api/v1/laboratory/orders
POST /api/v1/laboratory/orders
GET  /api/v1/laboratory/orders/{order_id}
PUT  /api/v1/laboratory/orders/{order_id}
GET  /api/v1/laboratory/results/{order_id}
POST /api/v1/laboratory/results/{order_id}
```

Lab workflow:

```text
Consultation or lab staff creates order
  -> sample is collected
  -> result is recorded
  -> result is released
  -> doctor is notified
```

## 21. Radiology Workflow

Radiology APIs:

```text
GET  /api/v1/radiology
POST /api/v1/radiology
GET  /api/v1/radiology/{order_id}
PUT  /api/v1/radiology/{order_id}
PUT  /api/v1/radiology/{order_id}/report
```

Radiology workflow:

```text
Order created
  -> imaging performed
  -> report completed
  -> doctor notified through alert/order workflow
```

## 22. Pharmacy Workflow

Pharmacy APIs:

```text
GET    /api/v1/pharmacy/medications
POST   /api/v1/pharmacy/medications
GET    /api/v1/pharmacy/medications/{medication_id}
PUT    /api/v1/pharmacy/medications/{medication_id}
GET    /api/v1/pharmacy/inventory/{medication_id}
POST   /api/v1/pharmacy/inventory/{medication_id}
GET    /api/v1/pharmacy/prescriptions
POST   /api/v1/pharmacy/prescriptions
GET    /api/v1/pharmacy/prescriptions/{prescription_id}
POST   /api/v1/pharmacy/prescriptions/{prescription_id}/dispense
DELETE /api/v1/pharmacy/prescriptions/{prescription_id}
```

Pharmacy workflow:

```text
Doctor creates prescription
  -> prescription appears for pharmacy
  -> pharmacist dispenses
  -> stock can be updated
  -> prescription status changes to dispensed
```

## 23. Wards and Nursing

Ward APIs:

```text
GET  /api/v1/wards/beds
POST /api/v1/wards/beds
PUT  /api/v1/wards/beds/{bed_id}
GET  /api/v1/wards/admissions
POST /api/v1/wards/admissions
PUT  /api/v1/wards/admissions/{admission_id}
POST /api/v1/wards/admissions/{admission_id}/observations
POST /api/v1/wards/admissions/{admission_id}/discharge
```

Nursing and ward features:

- bed board;
- admissions;
- active inpatient tracking;
- observations/vitals;
- discharge;
- ward task visibility in staff portal.

## 24. Billing, Payments, and Receipts

Billing APIs:

```text
GET  /api/v1/invoices
POST /api/v1/invoices
GET  /api/v1/invoices/{invoice_id}
PUT  /api/v1/invoices/{invoice_id}
POST /api/v1/invoices/{invoice_id}/payments
GET  /api/v1/invoices/{invoice_id}/payments
POST /api/v1/payments/{payment_id}/receipt
GET  /api/v1/payments/{payment_id}/receipt
```

Billing features:

- invoice creation;
- invoice itemization;
- payment recording;
- receipt generation/download;
- insurance provider and claim models;
- tenant and branch isolation.

Currency should be Nigerian naira in the UI.

## 25. Inventory and Suppliers

Inventory APIs:

```text
GET    /api/v1/inventory
POST   /api/v1/inventory
GET    /api/v1/inventory/low-stock
POST   /api/v1/inventory/reorder
GET    /api/v1/inventory/{item_id}
PUT    /api/v1/inventory/{item_id}
DELETE /api/v1/inventory/{item_id}
PUT    /api/v1/inventory/{item_id}/stock
```

Supplier APIs:

```text
GET    /api/v1/suppliers
POST   /api/v1/suppliers
GET    /api/v1/suppliers/{supplier_id}
PUT    /api/v1/suppliers/{supplier_id}
DELETE /api/v1/suppliers/{supplier_id}
```

Inventory features:

- stock records;
- low stock reporting;
- stock adjustment;
- reorder request workflow;
- supplier records.

## 26. Medical Records and EMR

EMR APIs:

```text
GET    /api/v1/emr
POST   /api/v1/emr
GET    /api/v1/emr/{record_id}
PUT    /api/v1/emr/{record_id}
DELETE /api/v1/emr/{record_id}
```

Medical record features:

- shared patient records;
- clinical notes;
- patient timeline;
- facility and branch scoping;
- role restrictions for clinical staff.

## 27. Reports and Analytics

Report APIs:

```text
GET /api/v1/reports/summary
GET /api/v1/reports/revenue
GET /api/v1/reports/departments
GET /api/v1/reports/operations
GET /api/v1/reports/inventory
```

Dashboard API:

```text
GET /api/v1/dashboard/stats
```

Report categories:

- overview;
- revenue;
- departments;
- operations;
- inventory.

Reports are intended to be tenant-scoped and branch-aware where applicable.

## 28. Alerts and Notifications

Alert APIs:

```text
GET    /api/v1/alerts
POST   /api/v1/alerts
POST   /api/v1/alerts/role
GET    /api/v1/alerts/{alert_id}
PUT    /api/v1/alerts/{alert_id}
DELETE /api/v1/alerts/{alert_id}
PUT    /api/v1/alerts/{alert_id}/read
PUT    /api/v1/alerts/{alert_id}/unread
PUT    /api/v1/alerts/actions/mark-all-read
```

Notification UX features:

- unread badges;
- mark one read;
- mark all read;
- role-targeted alerts;
- clinical/order notifications.

Patient notification APIs:

```text
GET /api/v1/patient-notifications
PUT /api/v1/patient-notifications/{notification_id}/sent
PUT /api/v1/patient-notifications/{notification_id}/read
```

Patient notification types:

- appointment reminders;
- lab result ready notices;
- bill/payment notices;
- discharge follow-ups.

## 29. Staff Messaging

Staff chat APIs:

```text
GET  /api/v1/chat/staff
GET  /api/v1/chat/health
POST /api/v1/chat/conversations
GET  /api/v1/chat/conversations
GET  /api/v1/chat/conversations/{conversation_id}/messages
POST /api/v1/chat/conversations/{conversation_id}/messages
POST /api/v1/chat/upload
GET  /api/v1/chat/files/{filename}
PUT  /api/v1/chat/conversations/{conversation_id}/read
GET  /api/v1/chat/unread-count
```

Chat features:

- staff list;
- tenant-isolated conversations;
- messages;
- unread count;
- file upload/download;
- read tracking.

## 30. Referrals

Referral APIs:

```text
POST /api/v1/referrals
GET  /api/v1/referrals
PUT  /api/v1/referrals/{referral_id}/accept
PUT  /api/v1/referrals/{referral_id}/complete
```

Referral workflow:

```text
Referring staff selects target department/branch context
  -> creates referral with reason, priority, notes
  -> receiving area sees referral
  -> referral is accepted
  -> referral is completed
```

## 31. Public Profile

Public profile APIs:

```text
GET /api/v1/facilities/{slug}/public-profile
PUT /api/v1/facilities/{slug}/public-profile
PUT /api/v1/facilities/{slug}/public-profile/departments/{dept_id}/services
PUT /api/v1/facilities/{slug}/public-profile/departments/{dept_id}/staff
```

Public frontend route:

```text
/hospital/:facilitySlug
```

Public profile features:

- public/private toggle;
- display name;
- description;
- phone/email;
- photos;
- department visibility;
- service/pricing configuration;
- public doctors/staff visibility;
- public hospital listing via `HospitalListing`.

## 32. Legal Pages

Frontend legal routes:

```text
/privacy
/terms
/dpa
```

Pages:

- Privacy Policy
- Terms of Service
- Data Processing Agreement

These documents should be reviewed by qualified legal counsel before signing enterprise agreements or entering a new jurisdiction.

## 33. File Uploads

File APIs:

```text
POST   /api/v1/files/upload
GET    /api/v1/files
GET    /api/v1/files/{filename}
DELETE /api/v1/files/{filename}
```

There is also a `files_new.py` route file in the codebase, but the currently registered router in `app/main.py` is `app.routes.files`.

File upload security expectations:

- validate file type;
- limit file size;
- randomize stored filenames;
- isolate tenant file paths;
- avoid serving untrusted executable content;
- optionally integrate malware scanning later.

## 34. Audit Logs

Audit log APIs:

```text
GET /api/v1/audit-logs
GET /api/v1/audit-logs/{log_id}
```

Audit logs are intended to capture:

- action;
- user;
- facility;
- branch where applicable;
- IP address;
- client/user agent;
- timestamp;
- target resource metadata.

Admin activity logs should be visible only to facility-level admins unless branch-specific audit views are intentionally added.

## 35. Tasks and Staff Portal

Task API:

```text
GET /api/v1/tasks
```

Staff portal routes:

```text
/portal/:facilitySlug
/:facilitySlug/branches/:branchSlug/portal
```

Staff portal features:

- role-tailored dashboard;
- quick actions;
- ward board access;
- tasks;
- recent activity;
- access scope display;
- staff profile summary.

## 36. Database Model Map

Core tenant and identity:

- Facility
- Branch
- User
- UserSession

Clinical:

- Patient
- Appointment
- MedicalRecord
- ClinicalNote
- LabTest
- LabOrder
- LabResult
- Radiology
- Referral
- WardBed
- WardAdmission
- PatientQueue

Medication and pharmacy:

- Medication
- PharmacyInventory
- Prescription
- PrescriptionItem

Finance:

- Invoice
- InvoiceItem
- Payment
- InsuranceProvider
- InsuranceClaim

Operations:

- Inventory
- Supplier
- Alert
- AuditLog
- PatientNotification
- OrderWorkflowEvent
- HospitalListing
- ChatConversation
- ChatMessage

Most operational tables are tenant-scoped with `facility_slug` and increasingly `facility_id`. Branch-aware tables use `branch_id` or legacy `department_id` where applicable.

## 37. Database and Performance

Database engine:

```text
app/extensions.py
```

Local development:

- SQLite is supported.
- SQLite uses WAL mode, normal sync, and configurable busy timeout.

Production/staging:

- PostgreSQL is recommended.
- SQLAlchemy connection pooling is configured for non-SQLite databases.
- Pool settings are controlled by env vars:
  - `DB_POOL_SIZE`
  - `DB_MAX_OVERFLOW`
  - `DB_POOL_TIMEOUT`
  - `DB_POOL_RECYCLE`
  - `DB_CONNECT_TIMEOUT`
  - `DB_APPLICATION_NAME`

Performance instrumentation:

- `Server-Timing` header on responses.
- slow request logging via `SLOW_REQUEST_MS`.
- slow query logging via `SLOW_QUERY_SECONDS`.

Migration files include production performance index work under:

```text
migrations/versions/
```

## 38. Security Posture

Security controls currently present:

- exact-origin CORS in production;
- production wildcard CORS rejection;
- HttpOnly auth cookies;
- secure cookies in production;
- JWT access and refresh token split;
- refresh token rotation;
- session tracking and revocation;
- logout everywhere;
- password hashing;
- input validation middleware;
- security headers middleware;
- rate limit middleware;
- module access middleware;
- route-level auth dependencies;
- generic auth errors for invalid credentials;
- docs disabled in production;
- tenant and branch query helpers;
- Vercel proxy support for same-origin browser requests.

Important security principles for future work:

- do not store JWTs in localStorage for browser auth;
- do not expose backend secrets or Hugging Face tokens to the browser;
- never use `ALLOWED_ORIGINS=*` in production;
- always filter tenant data by current user facility and branch;
- always return 404/403 for cross-tenant access without leaking records;
- validate file uploads before storage;
- keep production and staging databases separate;
- keep `.env` out of git.

## 39. Deployment

Backend deployment:

- Docker container from root `Dockerfile`.
- Hugging Face Spaces can host the backend.
- Production should use managed PostgreSQL.
- If SQLite is used on Hugging Face, persistent storage must be enabled or data can reset on rebuild.

Frontend deployment:

- Vercel project root:

```text
app/templates/initial frontend
```

Current documented frontend env:

```text
VITE_API_BASE_URL=https://your-backend/api/v1
```

If using same-origin Vercel proxy, frontend can use relative `/api/v1`.

Production backend env examples:

```text
APP_ENV=production
PORT=7860
JWT_SECRET_KEY=<long-random-secret>
SECRET_KEY=<long-random-secret>
FRONTEND_URL=https://your-vercel-project.vercel.app
ALLOWED_ORIGINS=https://your-vercel-project.vercel.app
COOKIE_SECURE=true
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
```

## 40. Staging Strategy

Recommended staging setup:

- staging Git branch;
- staging Vercel project or preview deployment;
- staging Hugging Face Space;
- staging PostgreSQL database separate from production;
- staging secrets separate from production;
- staging `ALLOWED_ORIGINS` matching staging frontend URL;
- staging smoke tests before merging to main.

Minimum smoke test before production:

1. Create facility.
2. Login as main admin.
3. Create branch.
4. Create branch admin.
5. Login to branch portal.
6. Confirm branch admin cannot login to wrong branch.
7. Confirm branch admin sees branch data only.
8. Create staff.
9. Register patient.
10. Schedule appointment.
11. Use queue check-in/start/complete.
12. Create consultation.
13. Create lab/radiology/pharmacy order.
14. Create invoice and payment.
15. Verify notifications, alerts, chat, and reports.
16. Refresh browser on deep routes.
17. Logout and login again.

## 41. Testing

Backend tests exist under:

```text
tests/
```

Important test files:

- `test_tenant_isolation.py`
- `test_branch_isolation.py`
- `test_staff_chat.py`
- `test_security_hardening.py`
- `test_schema_sync.py`
- `test_departments_public_profile.py`
- `test_setup_endpoints.py`
- `test_app_factory.py`

Frontend tests exist under:

```text
app/templates/initial frontend/src/test/
```

Important test areas:

- API client;
- auth/session;
- facility workspace;
- facility staff;
- modules;
- navigation;
- appointments;
- consultations;
- reports;
- tasks;
- wards;
- patient timeline.

Typical commands:

```powershell
Set-Location "app/templates/initial frontend"
npm test -- --run
npm run build

Set-Location "C:\Users\mattw\Downloads\new-his"
.\.venv\Scripts\python.exe -m pytest
```

## 42. Current Strengths

The system already has several strong production-oriented foundations:

- clear FastAPI router separation;
- SQLAlchemy ORM models;
- service layer for major workflows;
- facility and branch isolation helpers;
- role and module access control;
- staging/production split awareness;
- lazy-loaded frontend pages;
- centralized frontend API client;
- session refresh and logout everywhere;
- audit log model;
- public profile/legal page foundation;
- branch-aware route scheme;
- tests for branch isolation and tenant isolation.

## 43. Known Caution Areas

These areas should be handled carefully during future changes:

- Branch and department naming should stay distinct. Branch is the isolation boundary; department is not a full tenant.
- Browser auth should rely on HttpOnly cookies and safe same-origin proxy behavior where possible.
- Any new route must filter by `current_user.facility_slug` and branch scope where applicable.
- Any new module must be added consistently in frontend module catalog, backend module middleware, facility available modules, route guards, and navigation.
- Any new list endpoint should support pagination and avoid loading all tenant rows.
- Any new public endpoint must be intentionally unauthenticated and must not leak private data.
- Production and staging must never share the same database unless intentionally planned.
- Hugging Face Spaces using SQLite need persistent storage; otherwise rebuilds can reset data.

## 44. Future Feature Direction

Natural next improvements:

- stronger branch-level audit log views;
- branch-scoped public profile pages;
- patient portal login;
- SMS provider integration;
- email/SMS notification templates;
- background job queue for reminders and reports;
- richer role builder/custom permissions;
- managed object storage for uploads;
- malware scanning for uploads;
- Redis-backed rate limiting and caching when budget allows;
- deeper dashboard aggregation endpoints to reduce request count;
- admin observability dashboard for slow requests and errors.

## 45. Engineering Rule for New Work

Every new backend feature should answer these questions before merge:

1. Which facility owns this data?
2. Which branch owns this data?
3. Which roles can see it?
4. Which modules must be enabled?
5. What happens when the list is empty?
6. What happens when the user has no permission?
7. Does the route leak whether another tenant's record exists?
8. Does the query use indexes and pagination?
9. Does the frontend show a natural user-facing error?
10. Is there a test for tenant or branch isolation?

That is the standard that keeps HIS.Pro safe as it grows.
