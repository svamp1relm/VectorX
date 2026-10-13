"""make runs.expectancy_theoretical nullable

Revision ID: 91ad64596bcc
Revises: 588e5c05d5ab
Create Date: 2026-09-23 00:53:46.614587

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '91ad64596bcc'
down_revision: str | Sequence[str] | None = '588e5c05d5ab'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Historical backtest runs (Фаза 16a) have no p_win/win_r/loss_r model to
    # derive a theoretical expectancy from, so this column must accept NULL.
    op.alter_column('runs', 'expectancy_theoretical', existing_type=sa.Float(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Historical backtest runs (added alongside this column becoming nullable)
    # have no theoretical expectancy and store NULL here. Enforcing NOT NULL
    # again would silently violate the constraint on any such row, so refuse
    # the downgrade explicitly instead of letting Postgres raise a generic error.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM runs WHERE expectancy_theoretical IS NULL) THEN
                RAISE EXCEPTION 'Cannot downgrade: runs table contains historical backtest '
                    'rows with NULL expectancy_theoretical. Remove or backfill them first.';
            END IF;
        END $$;
        """
    )
    op.alter_column('runs', 'expectancy_theoretical', existing_type=sa.Float(), nullable=False)
