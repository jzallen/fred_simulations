"""Initial migration - create jobs and runs tables

Revision ID: 001
Revises:
Create Date: 2025-09-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create jobs table
    op.create_table('jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('status', sa.Enum('CREATED', 'SUBMITTED', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', name='jobstatusenum'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('input_location', sa.String(), nullable=True),
        sa.Column('config_location', sa.String(), nullable=True),
        sa.Column('job_metadata', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_created_at'), 'jobs', ['created_at'], unique=False)
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
    op.create_index(op.f('ix_jobs_user_id'), 'jobs', ['user_id'], unique=False)

    # Create runs table
    op.create_table('runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('request', sa.JSON(), nullable=False),
        sa.Column('pod_phase', sa.Enum('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'UNKNOWN', name='podphaseenum'), nullable=False),
        sa.Column('container_status', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('QUEUED', 'NOT_STARTED', 'RUNNING', 'ERROR', 'DONE', 'SUBMITTED', 'RUNNING_LEGACY', 'FAILED', 'CANCELLED', name='runstatusenum'), nullable=False),
        sa.Column('user_deleted', sa.Integer(), nullable=False),
        sa.Column('epx_client_version', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_runs_created_at'), 'runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_runs_job_id'), 'runs', ['job_id'], unique=False)
    op.create_index(op.f('ix_runs_status'), 'runs', ['status'], unique=False)
    op.create_index(op.f('ix_runs_user_id'), 'runs', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop runs table
    op.drop_index(op.f('ix_runs_user_id'), table_name='runs')
    op.drop_index(op.f('ix_runs_status'), table_name='runs')
    op.drop_index(op.f('ix_runs_job_id'), table_name='runs')
    op.drop_index(op.f('ix_runs_created_at'), table_name='runs')
    op.drop_table('runs')

    # Drop jobs table
    op.drop_index(op.f('ix_jobs_user_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_status'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_created_at'), table_name='jobs')
    op.drop_table('jobs')

    # Drop enums
    sa.Enum(name='runstatusenum').drop(op.get_bind(), checkfirst=False)
    sa.Enum(name='podphaseenum').drop(op.get_bind(), checkfirst=False)
    sa.Enum(name='jobstatusenum').drop(op.get_bind(), checkfirst=False)