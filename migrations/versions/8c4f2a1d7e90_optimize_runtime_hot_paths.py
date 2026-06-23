"""optimize runtime hot paths

Revision ID: 8c4f2a1d7e90
Revises: 6a2d8f7c9b10
Create Date: 2026-06-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "8c4f2a1d7e90"
down_revision = "6a2d8f7c9b10"
branch_labels = None
depends_on = None


INDEXES = [
    ("idx_chat_conversations_facility_participant", "chat_conversations", ["facility_slug", "participant_key"], True),
    ("idx_chat_conversations_facility_last_message", "chat_conversations", ["facility_slug", "last_message_at"], False),
    ("idx_chat_messages_conversation_created", "chat_messages", ["facility_slug", "conversation_id", "created_at"], False),
    ("idx_chat_messages_unread", "chat_messages", ["facility_slug", "conversation_id", "is_read", "sender_id"], False),
    ("idx_patient_queues_facility_branch_status", "patient_queues", ["facility_slug", "branch_id", "status"], False),
    ("idx_patient_queues_facility_created", "patient_queues", ["facility_slug", "created_at"], False),
    ("idx_patient_queues_facility_patient", "patient_queues", ["facility_slug", "patient_id"], False),
    ("idx_alerts_facility_unread", "alerts", ["facility_slug", "is_read", "expires_at"], False),
    ("idx_alerts_facility_recipient_unread", "alerts", ["facility_slug", "recipient_id", "is_read"], False),
    ("idx_audit_logs_facility_user_created", "audit_logs", ["facility_slug", "user_id", "created_at"], False),
    ("idx_inventory_facility_active", "inventory", ["facility_slug", "is_active"], False),
    ("idx_inventory_facility_category_active", "inventory", ["facility_slug", "category", "is_active"], False),
    ("idx_inventory_facility_sku", "inventory", ["facility_slug", "sku"], False),
    ("idx_suppliers_facility_name", "suppliers", ["facility_slug", "name"], False),
    ("idx_user_sessions_user_active", "user_sessions", ["user_id", "is_active", "expires_at"], False),
    ("idx_user_sessions_active_expiry", "user_sessions", ["is_active", "expires_at"], False),
    ("idx_referrals_facility_to_status", "referrals", ["facility_slug", "to_department_id", "status"], False),
    ("idx_referrals_facility_patient_created", "referrals", ["facility_slug", "patient_id", "created_at"], False),
]


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in set(_inspector().get_table_names())


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def upgrade():
    if _table_exists("chat_conversations") and "participant_key" not in _column_names("chat_conversations"):
        op.add_column("chat_conversations", sa.Column("participant_key", sa.String(length=80), nullable=True))

    for index_name, table_name, columns, unique in INDEXES:
        if not _table_exists(table_name):
            continue
        if not set(columns).issubset(_column_names(table_name)):
            continue
        if index_name in _index_names(table_name):
            continue
        op.create_index(index_name, table_name, columns, unique=unique)


def downgrade():
    for index_name, table_name, _columns, _unique in reversed(INDEXES):
        if _table_exists(table_name) and index_name in _index_names(table_name):
            op.drop_index(index_name, table_name=table_name)
    if _table_exists("chat_conversations") and "participant_key" in _column_names("chat_conversations"):
        op.drop_column("chat_conversations", "participant_key")
