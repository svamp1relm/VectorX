"""Shared repository lookups for HTTP routers."""

from fastapi import HTTPException

from vectorx.storage.postgres.repository import PostgresExperimentRepository


def get_experiment_or_404(
    experiment_id: int,
    repo: PostgresExperimentRepository,
    *,
    include_trades: bool = False,
):
    result = repo.get_experiment(experiment_id, include_trades=include_trades)
    if result is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    return result
