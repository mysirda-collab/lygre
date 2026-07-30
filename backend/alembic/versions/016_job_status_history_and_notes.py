"""add job status history and notes

Revision ID: 016_job_history_notes
Revises: 015_add_cal_excl
"""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa

revision = "016_job_history_notes"
down_revision = "015_add_cal_excl"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    upload_columns = {c["name"] for c in inspect(bind).get_columns("uploads")}

    if "processing_progress" not in upload_columns:
        op.add_column(
            "uploads",
            sa.Column("processing_progress", sa.Integer(), nullable=False, server_default="0"),
        )

    if "processing_message" not in upload_columns:
        op.add_column(
            "uploads",
            sa.Column("processing_message", sa.String(length=100), nullable=True),
        )
    op.create_table(
        "job_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_status_history_job_id", "job_status_history", ["job_id"])
    op.execute(
        "INSERT INTO job_status_history (job_id, previous_status, new_status, changed_at) "
        "SELECT id, NULL, status, CURRENT_TIMESTAMP FROM jobs"
    )
    op.create_table(
        "job_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_notes_job_id", "job_notes", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_notes_job_id", table_name="job_notes")
    op.drop_table("job_notes")
    op.drop_index("ix_job_status_history_job_id", table_name="job_status_history")
    op.drop_table("job_status_history")
    bind = op.get_bind()
    upload_columns = {c["name"] for c in inspect(bind).get_columns("uploads")}

    if "processing_message" in upload_columns:
        op.drop_column("uploads", "processing_message")

    if "processing_progress" in upload_columns:
        op.drop_column("uploads", "processing_progress")
