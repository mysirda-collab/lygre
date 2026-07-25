"""add upload page-based metadata

Revision ID: 009_upload_page_based
Revises: 008_calendar_events
Create Date: 2026-07-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "009_upload_page_based"
down_revision = "008_calendar_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploads", sa.Column("source_document_id", sa.String(length=64), nullable=True))
    op.add_column("uploads", sa.Column("source_original_filename", sa.String(length=255), nullable=True))
    op.add_column("uploads", sa.Column("source_stored_filename", sa.String(length=255), nullable=True))
    op.add_column("uploads", sa.Column("source_file_path", sa.String(length=500), nullable=True))
    op.add_column("uploads", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("uploads", sa.Column("total_pages", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_uploads_source_document_id"), "uploads", ["source_document_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_uploads_source_document_id"), table_name="uploads")
    op.drop_column("uploads", "total_pages")
    op.drop_column("uploads", "page_number")
    op.drop_column("uploads", "source_file_path")
    op.drop_column("uploads", "source_stored_filename")
    op.drop_column("uploads", "source_original_filename")
    op.drop_column("uploads", "source_document_id")
