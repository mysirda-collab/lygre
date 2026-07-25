from alembic import op
import sqlalchemy as sa


revision = "004_add_pdf_parsing_fields"
down_revision = "003_add_uploads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploads", sa.Column("extracted_text", sa.Text(), nullable=True))
    op.add_column("uploads", sa.Column("parsed_data", sa.String(length=4000), nullable=True))
    op.add_column("uploads", sa.Column("job_id", sa.Integer(), nullable=True))
    op.add_column("uploads", sa.Column("processing_status", sa.String(length=50), nullable=False, server_default="Hotovo"))


def downgrade() -> None:
    op.drop_column("uploads", "processing_status")
    op.drop_column("uploads", "job_id")
    op.drop_column("uploads", "parsed_data")
    op.drop_column("uploads", "extracted_text")
