from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "007_jobs_priority_indexes"
down_revision = "006_auth_users_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "audit_logs" not in tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("entity_type", sa.String(length=100), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=50), nullable=False),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    op.add_column("jobs", sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"))

    op.create_index("ix_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("ix_jobs_priority", "jobs", ["priority"], unique=False)
    op.create_index("ix_jobs_technician", "jobs", ["technician"], unique=False)
    op.create_index("ix_jobs_customer_name", "jobs", ["customer_name"], unique=False)
    op.create_index("ix_jobs_installation_date", "jobs", ["installation_date"], unique=False)
    op.create_index("ix_jobs_is_deleted", "jobs", ["is_deleted"], unique=False)

    op.create_index("ix_uploads_job_id", "uploads", ["job_id"], unique=False)
    if "audit_logs" in set(inspector.get_table_names()):
        op.create_index("ix_audit_logs_entity_type_entity_id", "audit_logs", ["entity_type", "entity_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "audit_logs" in set(inspector.get_table_names()):
        op.drop_index("ix_audit_logs_entity_type_entity_id", table_name="audit_logs")
    op.drop_index("ix_uploads_job_id", table_name="uploads")

    op.drop_index("ix_jobs_is_deleted", table_name="jobs")
    op.drop_index("ix_jobs_installation_date", table_name="jobs")
    op.drop_index("ix_jobs_customer_name", table_name="jobs")
    op.drop_index("ix_jobs_technician", table_name="jobs")
    op.drop_index("ix_jobs_priority", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")

    op.drop_column("jobs", "priority")

    if "audit_logs" in set(inspector.get_table_names()):
        op.drop_table("audit_logs")
