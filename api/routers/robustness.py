"""Out-of-sample and robustness analysis routes."""

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query

from api.data_paths import secure_experiment_spec, secure_sweep
from api.dependencies import get_repository
from api.routers.common import get_experiment_or_404
from api.schemas import WalkForwardRequest
from api.serialization import (
    confidence_interval_to_dict,
    out_of_sample_result_to_dict,
    sensitivity_result_to_dict,
    walk_forward_result_to_dict,
)
from vectorx.core.errors import (
    AnalysisUnavailableError,
    ExperimentTooLargeError,
    InvalidModelParametersError,
)
from vectorx.experiments.out_of_sample import OutOfSampleSpec, run_out_of_sample
from vectorx.experiments.spec import HistoricalBacktestExperimentSpec
from vectorx.experiments.sweep import SweepSpec
from vectorx.robustness.block_bootstrap import block_bootstrap_confidence_interval_by_run
from vectorx.robustness.sensitivity import run_sensitivity_analysis
from vectorx.robustness.walk_forward import generate_walk_forward_windows, run_walk_forward
from vectorx.statistics.versioning import ANALYSIS_VERSION
from vectorx.storage.postgres.repository import PostgresExperimentRepository

router = APIRouter()
MAX_WALK_FORWARD_WINDOWS = 100
MAX_BOOTSTRAP_WORK = 20_000_000


@router.post("/out-of-sample")
def create_out_of_sample(spec: OutOfSampleSpec) -> dict:
    base = secure_experiment_spec(spec.base)
    assert isinstance(base, HistoricalBacktestExperimentSpec)
    result = run_out_of_sample(spec.model_copy(update={"base": base}))
    return out_of_sample_result_to_dict(result)


@router.post("/robustness/sensitivity")
def create_sensitivity_analysis(sweep: SweepSpec) -> dict:
    return sensitivity_result_to_dict(run_sensitivity_analysis(secure_sweep(sweep)))


@router.post("/robustness/walk-forward")
def create_walk_forward(spec: WalkForwardRequest) -> dict:
    windows = generate_walk_forward_windows(
        spec.start,
        spec.end,
        train_window=timedelta(days=spec.train_window_days),
        test_window=timedelta(days=spec.test_window_days),
        step=timedelta(days=spec.step_days),
    )
    if not windows:
        raise InvalidModelParametersError(
            "walk-forward ranges produce no complete train/test windows"
        )
    if len(windows) > MAX_WALK_FORWARD_WINDOWS:
        raise ExperimentTooLargeError(
            f"walk-forward would generate {len(windows)} windows, exceeding the "
            f"limit of {MAX_WALK_FORWARD_WINDOWS}"
        )
    base = secure_experiment_spec(spec.base)
    assert isinstance(base, HistoricalBacktestExperimentSpec)
    results = run_walk_forward(
        base,
        windows,
        reference_risk_fraction=spec.reference_risk_fraction,
    )
    return walk_forward_result_to_dict(windows, results)


@router.get("/experiments/{experiment_id}/robustness/block-bootstrap")
def get_block_bootstrap(
    experiment_id: int,
    block_size: int = Query(gt=0),
    seed: int = Query(default=0, ge=0),
    confidence: float = Query(default=0.95, gt=0.0, lt=1.0),
    n_resamples: int = Query(default=2000, gt=0, le=20_000),
    cost_basis: Literal["gross_r", "net_r"] = "gross_r",
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> dict:
    result = get_experiment_or_404(experiment_id, repo)
    if not result.spec.storage.store_trades:
        raise AnalysisUnavailableError(
            "experiment was not saved with storage.store_trades=true; no raw trades to analyze"
        )
    trade_runs = repo.get_analysis_trade_runs(experiment_id)
    sample_size = sum(len(run) for run in trade_runs)
    if sample_size * n_resamples > MAX_BOOTSTRAP_WORK:
        raise ExperimentTooLargeError(
            f"bootstrap work budget exceeded: {sample_size} trades * {n_resamples} resamples"
        )
    run_values = [
        [
            net if cost_basis == "net_r" and net is not None else gross
            for gross, net in run
        ]
        for run in trade_runs
    ]
    interval = block_bootstrap_confidence_interval_by_run(
        run_values,
        block_size=block_size,
        seed=seed,
        confidence=confidence,
        n_resamples=n_resamples,
    )
    return {
        "analysis_version": ANALYSIS_VERSION,
        "block_size": block_size,
        "cost_basis": cost_basis,
        "confidence_interval": confidence_interval_to_dict(interval),
    }
