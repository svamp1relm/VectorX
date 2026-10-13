"""add experiment_batches table and experiments.batch_id

Revision ID: d8f3b6c20a51
Revises: c7e2a4f91b36
Create Date: 2026-10-02 00:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd8f3b6c20a51'
down_revision: str | Sequence[str] | None = 'c7e2a4f91b36'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Фаза 18c: groups many experiments under one research hypothesis.
    # `batch_id` is nullable/SET NULL on delete — deleting a batch must not
    # destroy the experiment data it grouped.
    op.create_table(
        'experiment_batches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('hypothesis', sa.String(), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('experiments', sa.Column('batch_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_experiments_batch_id',
        'experiments',
        'experiment_batches',
        ['batch_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_experiments_batch_id', 'experiments', ['batch_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_experiments_batch_id', table_name='experiments')
    op.drop_constraint('fk_experiments_batch_id', 'experiments', type_='foreignkey')
    op.drop_column('experiments', 'batch_id')
    op.drop_table('experiment_batches')
