"""add net metrics and allow empty historical runs

Revision ID: f4b8d2c61a90
Revises: d8f3b6c20a51
Create Date: 2026-11-18 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4b8d2c61a90"
down_revision: str | Sequence[str] | None = "d8f3b6c20a51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trades", sa.Column("net_r_multiple", sa.Float(), nullable=True))
    op.add_column("runs", sa.Column("expectancy_sample_net", sa.Float(), nullable=True))
    op.add_column("runs", sa.Column("win_rate_net", sa.Float(), nullable=True))
    op.add_column("runs", sa.Column("profit_factor_net", sa.Float(), nullable=True))
    op.alter_column("runs", "expectancy_sample", nullable=True)
    op.alter_column("runs", "win_rate", nullable=True)
    op.alter_column("runs", "profit_factor", nullable=True)
    op.alter_column("runs", "stdev", nullable=True)


def downgrade() -> None:
    op.execute(
        "UPDATE runs SET expectancy_sample = 0.0 WHERE expectancy_sample IS NULL"
    )
    op.execute("UPDATE runs SET win_rate = 0.0 WHERE win_rate IS NULL")
    op.execute("UPDATE runs SET profit_factor = 0.0 WHERE profit_factor IS NULL")
    op.execute("UPDATE runs SET stdev = 0.0 WHERE stdev IS NULL")
    op.alter_column("runs", "stdev", nullable=False)
    op.alter_column("runs", "profit_factor", nullable=False)
    op.alter_column("runs", "win_rate", nullable=False)
    op.alter_column("runs", "expectancy_sample", nullable=False)
    op.drop_column("runs", "profit_factor_net")
    op.drop_column("runs", "win_rate_net")
    op.drop_column("runs", "expectancy_sample_net")
    op.drop_column("trades", "net_r_multiple")
