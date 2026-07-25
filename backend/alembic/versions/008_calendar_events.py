from alembic import op
import sqlalchemy as sa


revision = "008_calendar_events"
down_revision = "007_jobs_priority_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["technician_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_calendar_events_starts_at", "calendar_events", ["starts_at"], unique=False)
    op.create_index("ix_calendar_events_ends_at", "calendar_events", ["ends_at"], unique=False)
    op.create_index("ix_calendar_events_technician_id", "calendar_events", ["technician_id"], unique=False)
    op.create_index("ix_calendar_events_job_id", "calendar_events", ["job_id"], unique=False)
    op.create_index("ix_calendar_events_is_deleted", "calendar_events", ["is_deleted"], unique=False)
    op.create_index(
        "ix_calendar_events_technician_time",
        "calendar_events",
        ["technician_id", "starts_at", "ends_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_calendar_events_technician_time", table_name="calendar_events")
    op.drop_index("ix_calendar_events_is_deleted", table_name="calendar_events")
    op.drop_index("ix_calendar_events_job_id", table_name="calendar_events")
    op.drop_index("ix_calendar_events_technician_id", table_name="calendar_events")
    op.drop_index("ix_calendar_events_ends_at", table_name="calendar_events")
    op.drop_index("ix_calendar_events_starts_at", table_name="calendar_events")
    op.drop_table("calendar_events")
