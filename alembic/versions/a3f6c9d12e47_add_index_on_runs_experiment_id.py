"""add index on runs.experiment_id

Revision ID: a3f6c9d12e47
Revises: 91ad64596bcc
Create Date: 2026-10-01 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3f6c9d12e47'
down_revision: str | Sequence[str] | None = '91ad64596bcc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # `runs.experiment_id` has a FK to `experiments.id` but no index, so
    # get_experiment()/cascade deletes full-scan `runs` as it grows.
    op.create_index('ix_runs_experiment_id', 'runs', ['experiment_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_runs_experiment_id', table_name='runs')
