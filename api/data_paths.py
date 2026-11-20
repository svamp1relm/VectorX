"""Restrict server-side CSV access to the configured local data root."""

import os
from pathlib import Path

from fastapi import HTTPException

from vectorx.experiments.spec import (
    ExperimentSpec,
    HistoricalBacktestExperimentSpec,
    parse_experiment_spec,
)
from vectorx.experiments.sweep import SweepSpec


def resolve_api_data_path(path: str) -> str:
    root = Path(os.environ.get("VECTORX_DATA_ROOT", "configs/experiments/data")).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="CSV path is outside VECTORX_DATA_ROOT") from exc
    return str(resolved)


def secure_experiment_spec(spec: ExperimentSpec) -> ExperimentSpec:
    if isinstance(spec, HistoricalBacktestExperimentSpec):
        return spec.model_copy(
            update={
                "data": spec.data.model_copy(
                    update={"path": resolve_api_data_path(spec.data.path)}
                )
            }
        )
    return spec


def secure_sweep(sweep: SweepSpec) -> SweepSpec:
    base = secure_experiment_spec(parse_experiment_spec(sweep.base))
    return sweep.model_copy(update={"base": base.model_dump(mode="json")})
