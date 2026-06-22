"""add production performance indexes

Revision ID: 6a2d8f7c9b10
Revises: 3f4b9c1d2e5a
Create Date: 2026-06-22 00:00:00.000000
"""

from alembic import op


revision = "6a2d8f7c9b10"
down_revision = "3f4b9c1d2e5a"
branch_labels = None
depends_on = None


INDEXES = [
    ("idx_patients_email", "patients", "email"),
    ("idx_patients_created_at", "patients", "created_at"),
    ("idx_patients_facility_dept", "patients", "facility_slug, department_id"),
    ("idx_patients_facility_branch", "patients", "facility_slug, branch_id"),
    ("idx_patients_facility_created", "patients", "facility_slug, created_at DESC"),
    ("idx_appointments_appointment_date", "appointments", "appointment_date DESC"),
    ("idx_appointments_scheduled_time", "appointments", "scheduled_time DESC"),
    ("idx_appointments_status", "appointments", "status"),
    ("idx_appointments_facility_dept", "appointments", "facility_slug, department_id"),
    ("idx_appointments_facility_branch", "appointments", "facility_slug, branch_id"),
    ("idx_appointments_status_facility", "appointments", "status, facility_slug"),
    ("idx_appointments_facility_date", "appointments", "facility_slug, appointment_date DESC"),
    ("idx_appointments_facility_doctor_date", "appointments", "facility_slug, doctor_id, appointment_date DESC"),
    ("idx_users_email", "users", "email"),
    ("idx_users_role", "users", "role"),
    ("idx_users_is_active", "users", "is_active"),
    ("idx_users_facility_role", "users", "facility_slug, role"),
    ("idx_users_facility_dept", "users", "facility_slug, department_id"),
    ("idx_users_facility_branch", "users", "facility_slug, branch_id"),
    ("idx_users_facility_active", "users", "facility_slug, is_active"),
    ("idx_lab_orders_status", "lab_orders", "status"),
    ("idx_lab_orders_order_date", "lab_orders", "order_date DESC"),
    ("idx_lab_orders_facility_dept", "lab_orders", "facility_slug, department_id"),
    ("idx_lab_orders_facility_branch", "lab_orders", "facility_slug, branch_id"),
    ("idx_lab_orders_status_facility", "lab_orders", "status, facility_slug"),
    ("idx_lab_orders_facility_date", "lab_orders", "facility_slug, order_date DESC"),
    ("idx_lab_orders_facility_patient", "lab_orders", "facility_slug, patient_id"),
    ("idx_lab_results_order_id", "lab_results", "order_id"),
    ("idx_radiology_orders_request_date", "radiology_orders", "request_date DESC"),
    ("idx_radiology_orders_requested_by", "radiology_orders", "requested_by"),
    ("idx_radiology_orders_radiologist_id", "radiology_orders", "radiologist_id"),
    ("idx_radiology_orders_facility_dept", "radiology_orders", "facility_slug, department_id"),
    ("idx_radiology_orders_facility_branch", "radiology_orders", "facility_slug, branch_id"),
    ("idx_radiology_orders_status_facility", "radiology_orders", "status, facility_slug"),
    ("idx_radiology_orders_facility_date", "radiology_orders", "facility_slug, request_date DESC"),
    ("idx_radiology_orders_facility_patient", "radiology_orders", "facility_slug, patient_id"),
    ("idx_invoices_status", "invoices", "status"),
    ("idx_invoices_invoice_date", "invoices", "invoice_date DESC"),
    ("idx_invoices_paid_date", "invoices", "paid_date DESC"),
    ("idx_invoices_facility_dept", "invoices", "facility_slug, department_id"),
    ("idx_invoices_facility_branch", "invoices", "facility_slug, branch_id"),
    ("idx_invoices_status_facility", "invoices", "status, facility_slug"),
    ("idx_invoices_facility_date", "invoices", "facility_slug, invoice_date DESC"),
    ("idx_invoices_facility_patient", "invoices", "facility_slug, patient_id"),
    ("idx_payments_invoice_id", "payments", "invoice_id"),
    ("idx_payments_payment_date", "payments", "payment_date DESC"),
    ("idx_medications_facility_active", "medications", "facility_slug, is_active"),
    ("idx_pharmacy_inventory_medication_id", "pharmacy_inventory", "medication_id"),
    ("idx_pharmacy_inventory_expiry_date", "pharmacy_inventory", "expiry_date"),
    ("idx_prescriptions_status", "prescriptions", "status"),
    ("idx_prescriptions_prescription_date", "prescriptions", "prescription_date DESC"),
    ("idx_prescriptions_facility_dept", "prescriptions", "facility_slug, department_id"),
    ("idx_prescriptions_facility_branch", "prescriptions", "facility_slug, branch_id"),
    ("idx_prescriptions_status_facility", "prescriptions", "status, facility_slug"),
    ("idx_prescriptions_facility_date", "prescriptions", "facility_slug, prescription_date DESC"),
    ("idx_prescriptions_facility_patient", "prescriptions", "facility_slug, patient_id"),
    ("idx_alerts_facility_created", "alerts", "facility_slug, created_at DESC"),
    ("idx_audit_logs_facility_created", "audit_logs", "facility_slug, created_at DESC"),
    ("idx_patient_queues_facility_status", "patient_queues", "facility_slug, status"),
    ("idx_suppliers_facility_active", "suppliers", "facility_slug, is_active"),
    ("idx_order_workflow_facility_patient", "order_workflow_events", "facility_slug, patient_id"),
    ("idx_order_workflow_facility_occurred", "order_workflow_events", "facility_slug, occurred_at DESC"),
    ("idx_patient_notifications_facility_patient", "patient_notifications", "facility_slug, patient_id"),
    ("idx_referrals_facility_to_dept", "referrals", "facility_slug, to_department_id"),
    ("idx_chat_conversations_facility", "chat_conversations", "facility_slug"),
    ("idx_chat_messages_facility_conversation", "chat_messages", "facility_slug, conversation_id"),
    ("idx_ward_beds_facility_branch", "ward_beds", "facility_slug, branch_id"),
    ("idx_ward_admissions_facility_patient", "ward_admissions", "facility_slug, patient_id"),
]


OPTIONAL_INDEXES = [
    ("idx_reviews_facility_created", "reviews", "facility_slug, created_at DESC"),
    ("idx_reviews_user_created", "reviews", "user_id, created_at DESC"),
    ("idx_discussions_facility_category", "discussions", "facility_slug, category"),
    ("idx_discussions_user_created", "discussions", "user_id, created_at DESC"),
    ("idx_staff_reviews_staff_facility", "staff_reviews", "staff_id, facility_slug"),
]


def _create_index_if_columns_exist(index_name: str, table_name: str, columns: str) -> None:
    column_names = [
        part.strip().split()[0]
        for part in columns.split(",")
    ]
    column_checks = " AND ".join(
        f"EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '{table_name}' AND column_name = '{column}')"
        for column in column_names
    )
    op.execute(
        f"""
        DO $$
        BEGIN
            IF to_regclass('public.{table_name}') IS NOT NULL AND {column_checks} THEN
                CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns});
            END IF;
        END
        $$;
        """
    )


def upgrade():
    for index_name, table_name, columns in INDEXES + OPTIONAL_INDEXES:
        _create_index_if_columns_exist(index_name, table_name, columns)


def downgrade():
    for index_name, _table_name, _columns in reversed(INDEXES + OPTIONAL_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
