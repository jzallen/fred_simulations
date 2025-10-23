"""Add results fields and rename url to config_url

Revision ID: 002
Revises: 001
Create Date: 2025-10-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename url → config_url for clarity
    # Note: SQLite doesn't support ALTER COLUMN RENAME directly, so we handle both cases
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.alter_column('url', new_column_name='config_url')

    # Add new results fields
    op.add_column('runs', sa.Column('results_url', sa.String(), nullable=True))
    op.add_column('runs', sa.Column('results_uploaded_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Drop new columns
    op.drop_column('runs', 'results_uploaded_at')
    op.drop_column('runs', 'results_url')

    # Rename config_url back to url
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.alter_column('config_url', new_column_name='url')
