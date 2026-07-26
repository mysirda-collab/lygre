"""optimize reservation schema indexes and constraints

Revision ID: 014_res_schema_idx_opt
Revises: 013_add_reservations_and_sms
Create Date: 2026-07-26 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "014_res_schema_idx_opt"
down_revision = "013_add_reservations_and_sms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_time_slots_enabled_blocked_start",
        "time_slots",
        ["enabled", "blocked", "start"],
    )
    op.create_index(
        "ix_time_slots_technician_start_end",
        "time_slots",
        ["technician", "start", "end"],
    )
    op.create_index(
        "ix_time_slots_location_start",
        "time_slots",
        ["location", "start"],
    )

    op.create_index(
        "ix_reservations_customer_status_created",
        "reservations",
        ["customer_id", "status", "created_at"],
    )
    op.create_index(
        "ix_reservations_status_slot",
        "reservations",
        ["status", "slot_id"],
    )
    op.create_index(
        "ix_reservations_token_used_expires",
        "reservations",
        ["token_used", "token_expires_at"],
    )
    op.create_index(
        "ix_reservations_job_created",
        "reservations",
        ["job_id", "created_at"],
    )

    op.create_index(
        "ix_sms_logs_reservation_created",
        "sms_logs",
        ["reservation_id", "created_at"],
    )
    op.create_index(
        "ix_sms_logs_status_created",
        "sms_logs",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_sms_logs_provider_external_message_id",
        "sms_logs",
        ["provider", "external_message_id"],
        unique=True,
        postgresql_where=sa.text("external_message_id IS NOT NULL"),
    )

    op.create_check_constraint(
        "ck_time_slots_start_before_end",
        "time_slots",
        sa.text('"start" < "end"'),
    )
    op.create_check_constraint(
        "ck_time_slots_capacity_positive",
        "time_slots",
        sa.text("capacity >= 1"),
    )


def downgrade() -> None:
    op.drop_constraint("ck_time_slots_capacity_positive", "time_slots", type_="check")
    op.drop_constraint("ck_time_slots_start_before_end", "time_slots", type_="check")

    op.drop_index("ix_sms_logs_provider_external_message_id", table_name="sms_logs")
    op.drop_index("ix_sms_logs_status_created", table_name="sms_logs")
    op.drop_index("ix_sms_logs_reservation_created", table_name="sms_logs")

    op.drop_index("ix_reservations_job_created", table_name="reservations")
    op.drop_index("ix_reservations_token_used_expires", table_name="reservations")
    op.drop_index("ix_reservations_status_slot", table_name="reservations")
    op.drop_index("ix_reservations_customer_status_created", table_name="reservations")

    op.drop_index("ix_time_slots_location_start", table_name="time_slots")
    op.drop_index("ix_time_slots_technician_start_end", table_name="time_slots")
    op.drop_index("ix_time_slots_enabled_blocked_start", table_name="time_slots")
