"""add reservations, time_slots, sms_logs, sms_templates

Revision ID: 013_add_reservations_and_sms
Revises: 012_add_upload_is_primary
Create Date: 2026-07-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '013_add_reservations_and_sms'
down_revision = '012_add_upload_is_primary'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'time_slots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('blocked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('technician', sa.String(length=150), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('note', sa.String(length=2000), nullable=True),
        sa.Column('installation_type', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'reservations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('slot_id', sa.Integer(), sa.ForeignKey('time_slots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('token', sa.String(length=128), nullable=False, unique=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('token_used', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='requested'),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confirmation_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'sms_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reservation_id', sa.Integer(), sa.ForeignKey('reservations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('error', sa.String(length=2000), nullable=True),
        sa.Column('external_message_id', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'sms_templates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False, unique=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index('ix_time_slots_start_end', 'time_slots', ['start', 'end'])
    op.create_index('ix_reservations_slot_id', 'reservations', ['slot_id'])
    op.create_index('ix_sms_logs_customer', 'sms_logs', ['customer_id'])


def downgrade() -> None:
    op.drop_index('ix_sms_logs_customer', table_name='sms_logs')
    op.drop_index('ix_reservations_slot_id', table_name='reservations')
    op.drop_index('ix_time_slots_start_end', table_name='time_slots')
    op.drop_table('sms_templates')
    op.drop_table('sms_logs')
    op.drop_table('reservations')
    op.drop_table('time_slots')
