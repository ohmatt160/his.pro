# HIS.Pro Hospital Operations Manual

**Deployment, Administration, Daily Use, Security, and Go-Live Guide**

| Document item | Value |
|---|---|
| Product | HIS.Pro Hospital Information System |
| Manual version | 1.0 release-candidate draft |
| Baseline date | 31 July 2026 |
| Intended readers | Hospital leadership, system administrators, department leads, trained staff, implementation team |
| Classification | Confidential - hospital operational documentation |
| Approval state | Draft for hospital review and user acceptance |

## Document Control

This manual explains the implemented HIS.Pro workflows and the responsibilities of
the hospital and HIS.Pro implementation team. It is not a medical protocol, legal
opinion, regulatory certification, or replacement for the hospital's clinical,
privacy, finance, records-retention, or emergency policies.

The hospital should nominate a document owner. Approved changes must record the
version, date, author, approver, and reason.

| Version | Date | Change | Author | Approver |
|---|---|---|---|---|
| 1.0 RC | 31 July 2026 | Initial implementation and operations manual | HIS.Pro team | Pending |

## 1. System Purpose

HIS.Pro provides one protected workspace for:

- facility and branch administration;
- staff accounts and role-based access;
- patient registration and demographic maintenance;
- appointments and outpatient queue;
- consultations and medical records;
- laboratory and radiology orders/results;
- prescriptions, pharmacy stock, and dispensing;
- ward admissions, nursing observations, and discharge;
- invoices, payments, and private receipts;
- general inventory and suppliers;
- alerts, referrals, staff chat, reports, and audit review;
- validation/import of approved legacy CSV or JSON data.

Each hospital is a separate tenant. Staff must sign in to the correct hospital and,
where applicable, branch. HIS.Pro checks tenant, branch, role, and enabled module
again on the server for every protected action.

## 2. Responsibilities

### HIS.Pro Implementation Team

- deploy and monitor approved infrastructure;
- protect platform secrets and apply security updates;
- configure tenant URLs, database, Redis, workers, scanning, and backups;
- investigate defects and security incidents;
- provide release notes, migration support, and technical evidence;
- avoid accessing hospital data except under approved support/incident procedure.

### Hospital Leadership And Data Controller

- approve who may use the system and for what purpose;
- approve role assignments, retention, consent, downtime, and incident policy;
- provide accurate migration source data and reconciliation owners;
- ensure staff training and confidentiality obligations;
- review access/audit reports and remove leavers promptly;
- approve go-live only after user acceptance, backup restore, security, and privacy gates.

### Department Leads

- confirm department workflows and authorized staff;
- review sampled patient, order, stock, and financial data;
- report incorrect access or data immediately;
- oversee downtime entry and post-restoration reconciliation.

### Every User

- use only their own account;
- keep passwords and verification methods private;
- check the hospital/branch name before accessing data;
- search for an existing patient before registration;
- verify patient identity before clinical or financial entry;
- report errors and suspected unauthorized access without delay;
- sign out on shared workstations and never export data without approval.

## 3. Supported Roles

| Display role | Main duties | Important limits |
|---|---|---|
| Main Facility Admin | Facility setup, staff, modules, branches, settings, migration, audit, reports | Use a separate non-admin account for routine work where possible |
| Branch Admin | Branch oversight in a multi-branch facility | Not available until multi-branch mode is enabled |
| Doctor | Consultation, records, prescriptions, lab/radiology orders | Access remains tenant/branch and module limited |
| Nurse | Patient support, queue, records, observations, wards | Clinical privileges follow hospital policy and endpoint permission |
| Receptionist | Registration, appointment, check-in, queue | No general administrative or unrestricted clinical access |
| Billing Officer | Invoice, payment, receipt, billing report workflow | Cannot administer the whole facility by default |
| Pharmacist | Medication catalogue/stock, prescription review, dispensing | Facility-level pharmacy stock in current version |
| Lab Staff | Test/order/result workflow | Limited to laboratory and explicitly shared records |

Do not create shared accounts such as `reception1` for a group. Every person needs
an attributable account. Backend references to Radiologist and Store Keeper are not
fully supported in staff creation/UI in this release candidate and must not be
promised until reconciled.

## 4. Facility And Branch Setup

### Initial Owner Setup

1. Open the approved HIS.Pro onboarding link.
2. Enter the owner's real name, work email, secure password, and facility details.
3. Enter the pilot invitation code when provided.
4. Submit once and wait for the real setup result.
5. Record the canonical hospital URL supplied by HIS.Pro.
6. Sign in and immediately review facility name, type, modules, contact, and address.

Public owner signup remains disabled until email verification is released. Do not
publish a general onboarding code or send it through an insecure group channel.

### Hospital URL

Before HIS.Pro has a custom domain, the approved format is:

```text
https://<vercel-project>.vercel.app/<hospital-slug>/login
```

After a wildcard domain is configured, the canonical format is:

```text
https://<hospital-subdomain>.<tenant-base-domain>
```

For example, a deployment configured with `TENANT_BASE_DOMAIN=example.com` issues
`https://sunrise-medical.example.com`. The suffix differs by deployment and must
never be guessed from a generated hosting URL.

Old supported path links remain valid. Users should update bookmarks after the
custom-domain migration is announced.
If a link shows another hospital subdomain, stop and contact the administrator.

### Modules

Enable only modules the hospital will use and support. A role such as Pharmacist,
Lab Staff, Nurse, or Billing Officer cannot be created when its required module is
disabled. Disable unused modules only after reviewing active work and data impact.

### Multi-Branch

Enable multi-branch only after branches, staff ownership, and operating policy are
approved. Branch Admin and the Administration department appear only in this mode.
Current ward beds are facility-level; branch staff cannot assign them. Multi-branch
inpatient use is therefore not approved in this release candidate.

## 5. Staff Account Administration

### Create Staff

1. Sign in as Main Facility Admin.
2. Open **Staff Access** and choose **Add Staff**.
3. Enter the person's legal/working name and approved work contact.
4. Select the least-privilege role required for their job.
5. Select the correct branch/department when available.
6. Confirm the required module is enabled.
7. Submit once; wait for confirmation.
8. Give temporary credentials directly to the named user through an approved channel.
9. Require password change at first sign-in where configured.
10. Record that access was approved by the department lead.

### Create A Billing Officer

1. Confirm the **Billing** module is enabled.
2. Add staff and choose **Billing Officer**.
3. Assign the correct branch if the facility is multi-branch.
4. Use **Revenue & Billing** as the normal department.
5. Test invoice lookup, payment entry, and receipt access with a non-production record.
6. Confirm the user cannot access settings, staff administration, or unrelated branches.

### Change Or Remove Access

- Update role/branch only after written approval.
- Deactivate leavers or suspended users immediately.
- Revoke active sessions after a suspected compromise.
- Review administrators, billing, pharmacy, laboratory, and migration access monthly.
- Never reuse a former employee's login for a replacement.

## 6. Patient Registration And Records

### Register A Patient

1. Open **Patients** and search by name, phone, date of birth, or known identifier.
2. If a matching patient exists, open and verify that record; do not create another.
3. Choose **Create Patient** only when no correct record exists.
4. Confirm identity with the hospital's approved identifiers.
5. Enter demographics, contact, emergency contact, and relevant history accurately.
6. Check the selected branch and submit once.
7. Wait for success before navigating away.

The interface prevents rapid repeat submission and the server uses an idempotency
key. If a network error occurs, retry through the same screen; do not open several
tabs and repeatedly press Create.

### View And Edit

Use the patient action menu to open details or the timeline. Verify the patient at
every encounter. Correct demographics through Edit and record the source of the
correction under hospital procedure. Do not overwrite clinical history to hide an
error.

### Archive

Archive only when authorized, for example a confirmed duplicate under an approved
merge/archive procedure. Archive hides the active patient from routine selection
but retains linked medical and financial history. Physical deletion is not offered.

## 7. Appointment, Queue, And Consultation

### Appointment

1. Open **Appointments**.
2. Select the verified patient, clinician, date/time, duration, and reason.
3. Confirm branch and submit once.
4. Update status/notes according to attendance and hospital policy.

### Queue And Check-In

1. Search and verify the patient.
2. Check in the appointment or create an approved walk-in queue entry.
3. Set priority only under clinical/triage policy.
4. Move the patient through waiting, active consultation, and completed states.
5. Do not create a second active queue entry to change priority; update the first.

### Consultation And Medical Record

1. Doctor opens the patient from the authorized queue/appointment context.
2. Confirm identity and encounter before entry.
3. Record complaint, observations/vitals, symptoms, diagnosis, plan, follow-up,
   and notes according to hospital documentation policy.
4. Create lab, radiology, or prescription orders when clinically required.
5. Review and submit once.

If a record is wrong, use the supported edit where appropriate or **Void** with a
clear reason. Voiding keeps the original, actor, reason, and time. Never request
database deletion to conceal a clinical correction.

## 8. Laboratory And Radiology

### Laboratory

1. Admin maintains the hospital's test catalogue and reference information.
2. Doctor/authorized staff orders a test for the verified patient.
3. Lab staff confirm patient and order before collection.
4. Move the order through the supported processing status.
5. Enter and review result, abnormal indicator, unit/reference context, and notes.
6. Complete only after the hospital's result verification procedure.
7. Notify the responsible clinician under critical-result policy.

### Radiology

1. Doctor creates an order with modality, body part, clinical notes, and branch.
2. Authorized imaging staff process the study and report.
3. Clinician reviews the result in the patient workflow.

The dedicated Radiologist staff role is not fully exposed in this release
candidate. The hospital and HIS.Pro team must agree the interim authorized role or
defer radiology go-live; do not grant Main Facility Admin simply to bypass this gap.

## 9. Prescription And Pharmacy

### Prescribe

1. Doctor opens the verified patient/consultation.
2. Select medications from the facility catalogue.
3. Enter quantity, dosage, and instructions.
4. Review interactions/allergies under clinical policy; HIS.Pro does not replace
   professional medication safety checks.
5. Submit once.

### Receive Pharmacy Stock

1. Verify medication, quantity, expiry, batch, and location against source documents.
2. Submit the stock receipt once and wait for confirmation.
3. If the connection fails, retry from the same action; the server prevents double addition.
4. Reconcile physical and system stock according to hospital policy.

### Dispense

1. Pharmacist opens a pending prescription and verifies patient and prescription.
2. Confirm every item and available stock.
3. Dispense once. The server locks and updates the prescription/stock together.
4. If any item has insufficient stock, no partial database dispense should occur.
5. Give counseling and documentation required by hospital policy.

Current pharmacy inventory is one facility-level quantity per medication. It does
not provide full branch, lot, or stock-movement accounting. Hospitals requiring
that control must defer or use an approved companion process until implemented.

## 10. Billing, Payment, And Receipt

### How Billing Works

An invoice is the patient's charge document. It contains one or more line items,
subtotal, tax, discount, total, status, and branch. A payment is a separate record
applied to the invoice. One invoice may have several partial payments. When paid
amount reaches total, the invoice becomes paid.

### Create Invoice

1. Verify patient and billable services/items.
2. Open **Billing** and choose **Create Invoice**.
3. Add each clear line description, quantity, and unit price.
4. Enter only approved tax/discount and an approved due date/notes.
5. Review total with source documents and submit once.

### Record Payment

1. Billing Officer opens the correct invoice.
2. Confirm patient, invoice number, total, paid amount, and remaining balance.
3. Enter a positive amount no greater than the balance.
4. Select payment method and enter the real reference where available.
5. Add a receipt image/PDF only through the private receipt control.
6. Submit once and wait for success.
7. Provide/download the receipt under hospital procedure.

The server locks the invoice, recalculates existing payments, rejects overpayment,
and prevents a network retry from recording the same payment twice.

### Corrections And Reconciliation

Do not edit or delete a historical payment to imitate a refund. Refunds/credit notes
are not implemented. Use the hospital's approved interim correction procedure,
retain evidence, and escalate to finance leadership/HIS.Pro support. Reconcile
daily totals by method, invoice status, cashier/Billing Officer, and bank/cash source.

## 11. Wards And Nursing

1. Verify patient and authorization for admission.
2. Create one active admission with ward, reason, acuity, and optional bed.
3. Enter observations and nursing notes against the active admission.
4. Confirm medications and vitals under hospital procedure.
5. Discharge once after authorization; the bed is released and follow-up record created.

Database controls prevent one patient having two active admissions and one bed
holding two active patients. Branch staff cannot assign current facility-level beds.
Do not launch multi-branch inpatient allocation until branch beds are implemented.

## 12. Inventory And Suppliers

### Inventory

- Create a unique SKU, category, unit, reorder threshold, supplier, and cost.
- Use Set only for an approved physical reconciliation.
- Use Addition for received stock and Reduction for issued/wasted stock.
- Enter a non-negative amount; the server prevents stock below zero.
- Do not deactivate an item while stock remains.

Every stock change should have matching source documentation. HIS.Pro currently
does not persist a complete purchase-order/goods-received workflow; the Reorder
command is not a purchase order.

### Suppliers

Create one active supplier record per facility/name, update approved contacts, and
deactivate rather than duplicate an obsolete supplier. Store no bank credentials or
unnecessary personal data in free-text supplier fields.

## 13. Alerts, Referrals, And Staff Chat

- Alerts may be personal, facility-wide, or role-targeted. Do not include excessive
  patient detail; use the patient record as the source of truth.
- Referrals send a patient to an approved receiving department. Receiving staff
  accept and complete under department policy.
- Staff chat is facility-only and supports private scanned attachments. Confirm
  recipient before sending. Do not use chat as the sole medical record or emergency
  channel.
- Marking an alert/message read is personal workflow state, not proof a clinical
  escalation was actioned.

## 14. Data Migration From An Existing System

### Supported Input

HIS.Pro validates CSV or JSON files up to 25 MB and 50,000 rows for patients,
staff, appointments, inventory, or an approved full archive. Field aliases exist
for generic exports and selected OpenMRS, Bahmni, and DHIS2 naming. Native `.xlsx`
files are not currently parsed; convert/validate through the approved process.

### Required Migration Procedure

1. Nominate hospital data owner, HIS.Pro migration lead, and independent reviewer.
2. Freeze or record the legacy-system cutoff period.
3. Export an encrypted immutable source copy and calculate a checksum.
4. Remove unsupported/unnecessary fields only under approved mapping.
5. Upload to **Settings > Data Migration > Validate**.
6. Review every error, warning, field mapping, duplicate, and row count.
7. Correct the source/mapping and validate again; never edit production rows manually.
8. Import to staging and reconcile totals plus sampled high-risk records.
9. Obtain hospital written approval and verify a production backup/restore point.
10. Queue the production import once and monitor the job ID.
11. Reconcile patient counts, sampled demographics, appointments, staff roles,
    stock totals, errors, rejects, and audit event.
12. Obtain data-owner sign-off before decommissioning the old system.

Migration files contain sensitive information. Store them encrypted, restrict
access, log handling, and destroy them when approved retention ends.

## 15. Security And Privacy Operations

### Daily User Security

- Check tenant/branch before viewing a patient.
- Lock the screen when leaving.
- Do not share passwords, tokens, screenshots, or exports.
- Do not store files in personal email/cloud/USB without written approval.
- Report unexpected records, permissions, pop-ups, redirects, or login prompts.

### Administrator Security

- Review inactive/leaver accounts daily during staffing changes.
- Review privileged accounts and active sessions monthly.
- Keep public signup and OhmattOS feature flags off unless formally approved.
- Review audit logs for staff changes, migrations, payments, clinical voids,
  repeated login failure, large access, and file activity.
- Use separate random production secrets in the secret manager and rotate under plan.

### Incident Reporting

Immediately report suspected wrong-patient entry, unauthorized access, lost device,
shared credential, malware, data export, payment discrepancy, or cross-hospital
record. Preserve evidence; do not delete logs or investigate through broad data
access. Follow the hospital's incident/breach escalation and legal notification plan.

HIS.Pro does not by itself establish compliance certification. The hospital and
processor must maintain appropriate legal basis, contracts, privacy notices,
retention, access review, training, infrastructure, and incident evidence.

## 16. Downtime And Recovery

### During Downtime

1. Incident lead declares downtime and records start time/scope.
2. Use approved numbered paper/offline forms for registration, medication, results,
   admissions, and payments.
3. Verify patient identity and prevent duplicate numbering.
4. Do not repeatedly retry payments or stock actions in many browser tabs.
5. Escalate urgent clinical communication through approved emergency channels.

### After Restoration

1. Incident lead confirms the system is stable and backup status is known.
2. Search before entering each downtime patient/action.
3. Enter source form number and original event time where supported.
4. Use one action/one idempotency key and wait for confirmation.
5. A second authorized person reviews medication, result, admission, and payment entry.
6. Reconcile all numbered forms; record missing/duplicate/incorrect entries.
7. Close the incident only after clinical, finance, and data owners sign off.

## 17. Routine Control Checklist

### Start Of Day

- [ ] Correct hospital/branch URL and TLS lock verified.
- [ ] Health/status and overnight incidents reviewed.
- [ ] Background jobs/migrations completed or escalated.
- [ ] Reception, clinical, lab, pharmacy, billing, and ward leads can access required modules.
- [ ] ClamAV/private file storage and backup monitoring healthy.

### End Of Day

- [ ] Queue and active encounters reviewed.
- [ ] Critical/unreviewed lab and radiology results escalated.
- [ ] Pharmacy and inventory exceptions reviewed.
- [ ] Billing/payment totals reconciled.
- [ ] Active admissions and bed state reconciled.
- [ ] Privileged/audit anomalies reviewed.
- [ ] Backup completed and monitored.

### Monthly

- [ ] Staff/role/branch access recertified.
- [ ] Leaver and dormant accounts removed.
- [ ] Restore test/security patch/dependency status reviewed.
- [ ] Data retention and migration file disposal reviewed.
- [ ] Incident, downtime, and support trends reviewed.

## 18. Go-Live Acceptance

The hospital should not approve general launch until the separate Launch Readiness
document shows closed evidence for email verification, durable password reset,
dependency security, migration/restore, private files/scanning, DNS/TLS, branch
semantics, browser role tests, load/soak, monitoring, incident response, and
independent security review.

| Acceptance area | Hospital owner | HIS.Pro owner | Result/date |
|---|---|---|---|
| Facility/branch/module configuration |  |  |  |
| Staff role and least privilege |  |  |  |
| Patient and clinical workflows |  |  |  |
| Laboratory/pharmacy/radiology/ward workflow |  |  |  |
| Billing and reconciliation |  |  |  |
| Data migration reconciliation |  |  |  |
| Security/privacy/incident procedure |  |  |  |
| Backup restore and downtime drill |  |  |  |
| Training and user acceptance |  |  |  |
| Final go/no-go |  |  |  |

## Support Information

Before issue reporting, record the time, hospital/branch, page, action, user role,
patient/invoice/order ID where permitted, exact safe error message, and whether the
action may have succeeded. Do not send passwords, tokens, full patient screenshots,
or exports through unapproved support channels.

| Contact | Hospital to complete |
|---|---|
| Internal first-line support |  |
| HIS.Pro support channel |  |
| Security incident contact |  |
| Clinical safety escalation |  |
| Finance discrepancy escalation |  |
| Data protection/privacy contact |  |
| Emergency downtime lead |  |
