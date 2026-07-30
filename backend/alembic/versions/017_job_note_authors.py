"""add authors and edit metadata to job notes

Revision ID: 017_job_note_authors
Revises: 016_job_history_notes
"""
from alembic import op
import sqlalchemy as sa

revision = "017_job_note_authors"
down_revision = "016_job_history_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_notes", sa.Column("author_user_id", sa.Integer(), nullable=True))
    op.add_column("job_notes", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_notes", sa.Column("updated_by_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_job_notes_author_user_id_users",
        "job_notes",
        "users",
        ["author_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_job_notes_updated_by_user_id_users",
        "job_notes",
        "users",
        ["updated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_job_notes_updated_by_user_id_users", "job_notes", type_="foreignkey")
    op.drop_constraint("fk_job_notes_author_user_id_users", "job_notes", type_="foreignkey")
    op.drop_column("job_notes", "updated_by_user_id")
    op.drop_column("job_notes", "updated_at")
    op.drop_column("job_notes", "author_user_id")
