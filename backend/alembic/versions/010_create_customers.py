"""create customers table and extend jobs

Revision ID: 010_create_customers
Revises: 009_upload_page_based
Create Date: 2026-07-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "010_create_customers"
down_revision = "009_upload_page_based"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    # create customers table
    if "customers" not in tables:
        op.create_table(
            "customers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("customer_number", sa.String(length=100), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("street", sa.String(length=255), nullable=True),
            sa.Column("city", sa.String(length=150), nullable=True),
            sa.Column("zip", sa.String(length=20), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("customer_number", name="uq_customers_customer_number"),
        )
        op.create_index("ix_customers_customer_number", "customers", ["customer_number"], unique=False)

    # add columns to jobs
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("customer_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("order_number", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("parser_confidence", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("attachment_id", sa.Integer(), nullable=True))

        batch_op.create_index("ix_jobs_customer_id", ["customer_id"], unique=False)
        batch_op.create_index("ix_jobs_attachment_id", ["attachment_id"], unique=False)

    # add foreign keys
    op.create_foreign_key(
        "fk_jobs_customer_id_customers",
        "jobs",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_jobs_attachment_id_uploads",
        "jobs",
        "uploads",
        ["attachment_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_jobs_attachment_id_uploads", "jobs", type_="foreignkey")
    op.drop_constraint("fk_jobs_customer_id_customers", "jobs", type_="foreignkey")

    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_index("ix_jobs_attachment_id")
        batch_op.drop_index("ix_jobs_customer_id")
        batch_op.drop_column("attachment_id")
        batch_op.drop_column("parser_confidence")
        batch_op.drop_column("order_number")
        batch_op.drop_column("customer_id")

    op.drop_index("ix_customers_customer_number", table_name="customers")
    op.drop_table("customers")
