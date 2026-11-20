"""Experiment batch and parameter sweep routes."""

from fastapi import APIRouter, Depends, HTTPException

from api.data_paths import secure_experiment_spec
from api.dependencies import get_repository
from api.serialization import (
    batch_detail_to_dict,
    batch_summary_to_dict,
    experiment_summary_to_dict,
)
from vectorx.experiments.runner import run_experiment
from vectorx.experiments.sweep import SweepSpec, generate_sweep_specs
from vectorx.storage.postgres.repository import PostgresExperimentRepository

router = APIRouter()


def _get_batch_or_404(batch_id: int, repo: PostgresExperimentRepository):
    batch = repo.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    return batch


def _batch_detail(batch, repo: PostgresExperimentRepository) -> dict:
    experiments = []
    for experiment_id in batch.experiment_ids:
        result = repo.get_experiment_summary(experiment_id)
        if result is not None:
            experiments.append(experiment_summary_to_dict(experiment_id, result))
    return batch_detail_to_dict(batch, experiments)


@router.post("/batches", status_code=201)
def create_batch(
    sweep: SweepSpec, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    specs = generate_sweep_specs(sweep)
    results = tuple(run_experiment(secure_experiment_spec(spec)) for spec in specs)
    batch_id = repo.save_batch_with_experiments(
        hypothesis=sweep.hypothesis,
        notes=sweep.notes,
        results=results,
    )
    batch = _get_batch_or_404(batch_id, repo)
    return _batch_detail(batch, repo)


@router.get("/batches")
def list_batches(repo: PostgresExperimentRepository = Depends(get_repository)) -> list[dict]:
    return [batch_summary_to_dict(batch) for batch in repo.list_batches()]


@router.get("/batches/{batch_id}")
def get_batch(
    batch_id: int, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    batch = _get_batch_or_404(batch_id, repo)
    return _batch_detail(batch, repo)
