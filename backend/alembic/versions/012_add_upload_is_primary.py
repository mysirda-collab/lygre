"""add is_primary to uploads

Revision ID: 012_add_upload_is_primary
Revises: 011_unify_attachment_relation
Create Date: 2026-07-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "012_add_upload_is_primary"
down_revision = "011_unify_attachment_relation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("uploads") as batch_op:
        batch_op.add_column(sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    with op.batch_alter_table("uploads") as batch_op:
        batch_op.drop_column("is_primary")
