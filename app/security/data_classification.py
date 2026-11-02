"""A small, enforceable classification registry for HIS.Pro data."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class DataClassification(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


# Classifications deliberately follow the data, not a screen name. The registry
# is used in export manifests and to keep security telemetry free of PHI.
EXPORT_ENTITY_CLASSIFICATION: dict[str, DataClassification] = {
    "facility": DataClassification.CONFIDENTIAL,
    "branches": DataClassification.CONFIDENTIAL,
    "users": DataClassification.CONFIDENTIAL,
    "patients": DataClassification.RESTRICTED,
    "appointments": DataClassification.RESTRICTED,
    "medical_records": DataClassification.RESTRICTED,
    "clinical_notes": DataClassification.RESTRICTED,
    "lab_tests": DataClassification.CONFIDENTIAL,
    "lab_orders": DataClassification.RESTRICTED,
    "lab_results": DataClassification.RESTRICTED,
    "medications": DataClassification.CONFIDENTIAL,
    "pharmacy_inventory": DataClassification.CONFIDENTIAL,
    "prescriptions": DataClassification.RESTRICTED,
    "prescription_items": DataClassification.RESTRICTED,
    "invoices": DataClassification.CONFIDENTIAL,
    "invoice_items": DataClassification.CONFIDENTIAL,
    "payments": DataClassification.CONFIDENTIAL,
    "insurance_claims": DataClassification.RESTRICTED,
    "inventory": DataClassification.CONFIDENTIAL,
    "suppliers": DataClassification.CONFIDENTIAL,
    "radiology_orders": DataClassification.RESTRICTED,
    "ward_beds": DataClassification.CONFIDENTIAL,
    "ward_admissions": DataClassification.RESTRICTED,
    "patient_queues": DataClassification.RESTRICTED,
    "patient_notifications": DataClassification.RESTRICTED,
    "order_workflow_events": DataClassification.RESTRICTED,
    "referrals": DataClassification.RESTRICTED,
    "chat_conversations": DataClassification.CONFIDENTIAL,
    "chat_messages": DataClassification.CONFIDENTIAL,
    "audit_logs": DataClassification.CONFIDENTIAL,
}

SECRET_FIELD_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "refresh_jti",
    "idempotency_payload_hash",
)


def classification_for_export_entity(entity: str) -> DataClassification:
    return EXPORT_ENTITY_CLASSIFICATION.get(entity, DataClassification.CONFIDENTIAL)


def redact_secrets(value: Any) -> Any:
    """Recursively remove credentials from a value destined for a log/export."""
    if isinstance(value, dict):
        return {
            key: redact_secrets(item)
            for key, item in value.items()
            if not any(fragment in key.lower() for fragment in SECRET_FIELD_FRAGMENTS)
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value
