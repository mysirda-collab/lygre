"""add exclude constraint for calendar_events to prevent overlapping events per technician

Revision ID: 015_add_calendar_exclude_constraint
Revises: 014_optimize_reservation_schema_indexes
Create Date: 2026-07-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015_add_calendar_exclude_constraint'
down_revision = '014_optimize_reservation_schema_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration targets Postgres only. Add btree_gist extension and exclusion constraint.
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect != 'postgresql':
        return

    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
    # create a range column on the fly using tsrange(starts_at, ends_at)
    op.execute(
        "ALTER TABLE calendar_events ADD CONSTRAINT calendar_events_tech_time_excl EXCLUDE USING GIST (technician_id WITH =, tsrange(starts_at, ends_at) WITH &&)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect != 'postgresql':
        return

    op.execute('ALTER TABLE calendar_events DROP CONSTRAINT IF EXISTS calendar_events_tech_time_excl')
    # don't drop extension
