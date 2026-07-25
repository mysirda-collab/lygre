"""unify attachment relation: drop jobs.attachment_id and ensure parser_confidence not null

Revision ID: 011_unify_attachment_relation
Revises: 010_create_customers
Create Date: 2026-07-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "011_unify_attachment_relation"
down_revision = "010_create_customers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # drop foreign key, index and column attachment_id from jobs
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_constraint("fk_jobs_attachment_id_uploads", type_="foreignkey")
        batch_op.drop_index("ix_jobs_attachment_id")
        batch_op.drop_column("attachment_id")
    # make parser_confidence non-nullable with default 0.0
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.alter_column("parser_confidence",
                              existing_type=sa.Float(),
                              nullable=False,
                              server_default=sa.text("0.0"))


def downgrade() -> None:
    # revert parser_confidence
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.alter_column("parser_confidence",
                              existing_type=sa.Float(),
                              nullable=True,
                              server_default=None)
    # add attachment_id column back
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("attachment_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_jobs_attachment_id", ["attachment_id"], unique=False)
        batch_op.create_foreign_key("fk_jobs_attachment_id_uploads", "uploads", ["attachment_id"], ["id"], ondelete="SET NULL")
