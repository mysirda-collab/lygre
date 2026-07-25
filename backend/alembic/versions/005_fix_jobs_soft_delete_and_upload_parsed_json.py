from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "005_jobs_softdel_json"
down_revision = "004_add_pdf_parsing_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.execute(
        """
        ALTER TABLE uploads
        ALTER COLUMN parsed_data TYPE jsonb
        USING CASE
            WHEN parsed_data IS NULL OR parsed_data = '' THEN NULL
            ELSE parsed_data::jsonb
        END
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE uploads
        ALTER COLUMN parsed_data TYPE varchar(4000)
        USING CASE
            WHEN parsed_data IS NULL THEN NULL
            ELSE parsed_data::text
        END
        """
    )
    op.drop_column("jobs", "is_deleted")
