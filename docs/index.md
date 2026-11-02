# HIS.Pro Documentation

**Documentation baseline:** 31 July 2026  
**Product:** HIS.Pro multi-tenant hospital information system  
**Status:** pre-launch hardening; controlled pilot only until the launch gates close

This documentation is based on the current FastAPI, React, SQLAlchemy, migration,
worker, and deployment code. It does not claim features that are only planned.

## Reading Guide

| Document | Primary audience | Contents |
|---|---|---|
| [Project Overview](01_PROJECT_OVERVIEW.md) | Everyone | Purpose, users, technologies, product boundary |
| [System Architecture](02_SYSTEM_ARCHITECTURE.md) | Architects, developers, security | Runtime components, tenant routing, data and event flows |
| [Folder Structure](03_FOLDER_STRUCTURE.md) | Developers | Source tree ownership and generated assets |
| [Database Reference](04_DATABASE_REFERENCE.md) | Backend, data, operations | Every registered table, field, key, index, constraint, and ERD |
| [API Reference](05_API_REFERENCE.md) | Frontend, integrations, QA | Every registered OpenAPI operation with access and schema examples |
| [Modules and Workflows](06_MODULES_AND_WORKFLOWS.md) | Product, clinical operations, developers | Implemented features, rules, permissions, dependencies |
| [Frontend Reference](07_FRONTEND_REFERENCE.md) | Frontend, QA, support | Routes, pages, state, API behavior, tenant navigation |
| [Backend and Security](08_BACKEND_AND_SECURITY.md) | Backend, security, operations | Middleware, auth, isolation, uploads, audit, jobs, known risks |
| [Configuration and Deployment](09_CONFIGURATION_INSTALLATION_DEPLOYMENT.md) | DevOps, administrators | Local setup, environment, Docker, scaling, production topology |
| [Business Rules and User Workflows](10_BUSINESS_RULES_AND_USER_WORKFLOWS.md) | Hospital teams, QA, product | Role rules and end-to-end operational flows |
| [Implementation Notes and Roadmap](11_IMPLEMENTATION_NOTES_AND_ROADMAP.md) | Leadership, engineering | Code review, technical debt, limitations, recommended sequence |
| [Launch Readiness](12_LAUNCH_READINESS.md) | Release owner, hospital sponsor | Evidence-based go/no-go gates and sign-off criteria |
| [Hospital Operations Manual](13_HOSPITAL_OPERATIONS_MANUAL.md) | Hospital administrators and staff | Setup, daily use, security, migration, downtime, support |
| [System Migration and Account Lifecycle](SYSTEM_MIGRATION_AND_ACCOUNT_LIFECYCLE.md) | Hospital migration leads, administrators, support, operations | Import/export runbooks, restrictions, recoverable deletion, purge and retention |
| [Hospital Manual - Word](HIS_PRO_HOSPITAL_OPERATIONS_MANUAL.docx) | Hospital leadership and trainers | Distributable, editable customer operations manual |
| [Hospital Manual - PDF](../output/pdf/HIS_PRO_HOSPITAL_OPERATIONS_MANUAL.pdf) | Hospital leadership and staff | Fixed-layout customer operations manual |
| [OhmattOS Integration](ohmattos_integration.md) | Platform and integration teams | Current client-credentials/outbox contract and feature flags |
| [Tenant URL Migration](TENANT_URL_MIGRATION.md) | DevOps, support | Canonical subdomains and legacy URL redirects |
| [Hugging Face Staging](HUGGING_FACE_STAGING.md) | DevOps, staging operators | Single-container startup and required Space variables/secrets |
| [Complete App Roadmap](HIS_PRO_COMPLETE_APP_ROADMAP.md) | Product and engineering | Tickable completion roadmap |

## Status Labels

- **Implemented:** executable code and a current route or worker exist.
- **Partial:** code exists, but a production dependency, workflow, or safety control is incomplete.
- **Not implemented:** no production implementation exists in this repository.
- **Launch gate:** must be closed and evidenced before general availability.

## Source Of Truth

The generated [Database Reference](04_DATABASE_REFERENCE.md) and
[API Reference](05_API_REFERENCE.md) are refreshed with:

```bash
python scripts/generate_code_reference_docs.py
```

The implementation remains authoritative if a hand-written description and the
runtime disagree. Record such differences under Implementation Notes and update
the documentation in the same change as the code.
