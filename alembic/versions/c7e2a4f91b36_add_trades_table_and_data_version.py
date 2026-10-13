"""add trades table and experiments.data_version

Revision ID: c7e2a4f91b36
Revises: a3f6c9d12e47
Create Date: 2026-10-02 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7e2a4f91b36'
down_revision: str | Sequence[str] | None = 'a3f6c9d12e47'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Фаза 18a: raw per-trade persistence, gated by `storage.store_trades`
    # (default false — most experiments still create zero rows here).
    op.add_column('experiments', sa.Column('data_version', sa.String(), nullable=True))
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('trade_index', sa.Integer(), nullable=False),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('r_multiple', sa.Float(), nullable=False),
        sa.Column('risk', sa.Float(), nullable=False),
        sa.Column('entry_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('size', sa.Float(), nullable=True),
        sa.Column('pnl_money', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trades_run_id', 'trades', ['run_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_trades_run_id', table_name='trades')
    op.drop_table('trades')
    op.drop_column('experiments', 'data_version')
