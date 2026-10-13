"""FastAPI routes. Handlers stay thin: validation is `ExperimentSpec`
(pydantic, reused as-is from `vectorx.experiments.spec`), execution is
`run_experiment`, persistence is `PostgresExperimentRepository` — no
business logic lives here. No auth, no websocket, no job queue.
"""

import os

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from api.dependencies import get_repository
from api.serialization import (
    batch_detail_to_dict,
    batch_summary_to_dict,
    confidence_interval_to_dict,
    equity_curve_to_dicts,
    expectancy_comparison_result_to_dict,
    experiment_detail_to_dict,
    experiment_summary_to_dict,
    out_of_sample_result_to_dict,
    risk_adjusted_metrics_to_dict,
    run_result_to_dict,
    significance_result_to_dict,
)
from vectorx.core.errors import AnalysisUnavailableError, VectorXError
from vectorx.experiments.export import render_json_report, render_markdown_report
from vectorx.experiments.out_of_sample import OutOfSampleSpec, run_out_of_sample
from vectorx.experiments.runner import run_experiment
from vectorx.experiments.spec import (
    ExperimentSpec,
    HistoricalBacktestExperimentSpec,
    MonteCarloExperimentSpec,
)
from vectorx.experiments.sweep import SweepSpec, generate_sweep_specs
from vectorx.statistics.expectancy_comparison import (
    build_expectancy_snapshot_from_run_metrics,
)
from vectorx.statistics.expectancy_comparison import (
    compare_expectancy as build_expectancy_comparison,
)
from vectorx.statistics.risk_adjusted import compute_risk_adjusted_metrics
from vectorx.statistics.significance import significance_vs_zero
from vectorx.statistics.versioning import ANALYSIS_VERSION
from vectorx.storage.postgres.repository import PostgresExperimentRepository

app = FastAPI(title="VectorX API")


class ExpectancyComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monte_carlo_experiment_id: int
    historical_experiment_id: int
    reference_risk_fraction: float = Field(default=0.01, gt=0.0, le=1.0)

# The Vue dashboard (web/) is served from Vite's dev server on a different
# origin/port than the API, so the browser needs CORS to allow it through.
# No auth exists yet (plan: no auth in MVP), so a permissive origin list
# doesn't weaken anything that isn't already unauthenticated. Origins are
# configurable so a deployment can restrict them without a code change.
_default_cors_origins = "http://localhost:5173,http://127.0.0.1:5173"
_cors_origins = [
    origin.strip()
    for origin in os.environ.get("VECTORX_CORS_ORIGINS", _default_cors_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(VectorXError)
async def domain_error_handler(_request: Request, exc: VectorXError) -> JSONResponse:
    # Covers ExperimentTooLargeError (plan: over the operations limit -> 400)
    # and any other domain validation failure: all are the client's fault.
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def _get_experiment_or_404(
    experiment_id: int, repo: PostgresExperimentRepository
):
    result = repo.get_experiment(experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    return result


def _expectancy_snapshot(result):
    if result.summary.expectancy is not None:
        return result.summary.expectancy
    run_metrics = tuple(run.metrics for run in result.run_results)
    return build_expectancy_snapshot_from_run_metrics(result.spec, run_metrics)


@app.post("/experiments", status_code=201)
def create_experiment(
    spec: ExperimentSpec, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    result = run_experiment(spec)
    experiment_id = repo.save_experiment(result)
    stored = _get_experiment_or_404(experiment_id, repo)
    return experiment_detail_to_dict(experiment_id, stored)


@app.post("/experiments/{experiment_id}/run", status_code=201)
def rerun_experiment(
    experiment_id: int, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    existing = _get_experiment_or_404(experiment_id, repo)
    result = run_experiment(existing.spec)
    new_id = repo.save_experiment(result)
    stored = _get_experiment_or_404(new_id, repo)
    return experiment_detail_to_dict(new_id, stored)


@app.get("/experiments")
def list_experiments(
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> list[dict]:
    return [
        experiment_summary_to_dict(experiment_id, repo.get_experiment(experiment_id))
        for experiment_id in repo.list_experiment_ids()
    ]


@app.get("/experiments/{experiment_id}")
def get_experiment(
    experiment_id: int, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    result = _get_experiment_or_404(experiment_id, repo)
    return experiment_detail_to_dict(experiment_id, result)


@app.get("/experiments/{experiment_id}/results")
def get_experiment_results(
    experiment_id: int, repo: PostgresExperimentRepository = Depends(get_repository)
) -> list[dict]:
    result = _get_experiment_or_404(experiment_id, repo)
    return [run_result_to_dict(run, include_equity=False) for run in result.run_results]


def _find_run_or_404(result, run_id: int):
    for run in result.run_results:
        if run.run_index == run_id:
            return run
    raise HTTPException(status_code=404, detail="run not found")


@app.get("/experiments/{experiment_id}/runs/{run_id}")
def get_run(
    experiment_id: int,
    run_id: int,
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> dict:
    result = _get_experiment_or_404(experiment_id, repo)
    run = _find_run_or_404(result, run_id)
    return run_result_to_dict(run, include_equity=True)


@app.get("/experiments/{experiment_id}/equity")
def get_equity(
    experiment_id: int,
    run_id: int = 0,
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> list[dict]:
    result = _get_experiment_or_404(experiment_id, repo)
    run = _find_run_or_404(result, run_id)
    return equity_curve_to_dicts(run.equity_curve)


@app.post("/comparisons/expectancy")
def compare_expectancy(
    payload: ExpectancyComparisonRequest,
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> dict:
    monte_carlo = _get_experiment_or_404(payload.monte_carlo_experiment_id, repo)
    historical = _get_experiment_or_404(payload.historical_experiment_id, repo)
    if not isinstance(monte_carlo.spec, MonteCarloExperimentSpec):
        raise HTTPException(status_code=422, detail="monte_carlo_experiment_id must reference a Monte Carlo experiment")
    if not isinstance(historical.spec, HistoricalBacktestExperimentSpec):
        raise HTTPException(status_code=422, detail="historical_experiment_id must reference a historical backtest experiment")

    result = build_expectancy_comparison(
        monte_carlo=_expectancy_snapshot(monte_carlo),
        historical=_expectancy_snapshot(historical),
        reference_risk_fraction=payload.reference_risk_fraction,
    )
    return expectancy_comparison_result_to_dict(result)


def _get_batch_or_404(batch_id: int, repo: PostgresExperimentRepository):
    batch = repo.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    return batch


def _batch_detail(batch, repo: PostgresExperimentRepository) -> dict:
    experiments = [
        experiment_summary_to_dict(experiment_id, repo.get_experiment(experiment_id))
        for experiment_id in batch.experiment_ids
    ]
    return batch_detail_to_dict(batch, experiments)


@app.post("/batches", status_code=201)
def create_batch(
    sweep: SweepSpec, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    specs = generate_sweep_specs(sweep)
    batch_id = repo.save_batch(hypothesis=sweep.hypothesis, notes=sweep.notes)
    for spec in specs:
        result = run_experiment(spec)
        repo.save_experiment(result, batch_id=batch_id)

    batch = _get_batch_or_404(batch_id, repo)
    return _batch_detail(batch, repo)


@app.get("/batches")
def list_batches(repo: PostgresExperimentRepository = Depends(get_repository)) -> list[dict]:
    return [
        batch_summary_to_dict(repo.get_batch(batch_id)) for batch_id in repo.list_batch_ids()
    ]


@app.get("/batches/{batch_id}")
def get_batch(
    batch_id: int, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    batch = _get_batch_or_404(batch_id, repo)
    return _batch_detail(batch, repo)


@app.get("/experiments/{experiment_id}/analysis")
def get_analysis(
    experiment_id: int,
    seed: int = 0,
    confidence: float = 0.95,
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> dict:
    result = _get_experiment_or_404(experiment_id, repo)
    if result.run_trades is None:
        raise AnalysisUnavailableError(
            "experiment was not saved with storage.store_trades=true; no raw trades to analyze"
        )

    r_multiples = [
        trade.r_multiple for run_trades in result.run_trades for trade in run_trades
    ]
    significance = significance_vs_zero(r_multiples, seed=seed, confidence=confidence)
    risk_adjusted = compute_risk_adjusted_metrics(
        r_multiples,
        total_return=result.summary.mean_total_return,
        max_drawdown=max(run.metrics.max_drawdown for run in result.run_results),
    )
    return {
        "analysis_version": ANALYSIS_VERSION,
        "confidence_interval": confidence_interval_to_dict(significance.ci),
        "risk_adjusted": risk_adjusted_metrics_to_dict(risk_adjusted),
        "significance_vs_zero": significance_result_to_dict(significance),
    }


@app.post("/out-of-sample")
def create_out_of_sample(spec: OutOfSampleSpec) -> dict:
    result = run_out_of_sample(spec)
    return out_of_sample_result_to_dict(result)


@app.get("/experiments/{experiment_id}/export")
def export_experiment(
    experiment_id: int,
    format: str = "json",
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> Response:
    result = _get_experiment_or_404(experiment_id, repo)
    batch_id = repo.get_batch_id_for_experiment(experiment_id)
    batch = repo.get_batch(batch_id) if batch_id is not None else None

    if format == "json":
        return Response(content=render_json_report(result, batch=batch), media_type="application/json")
    if format == "markdown":
        return Response(content=render_markdown_report(result, batch=batch), media_type="text/markdown")
    raise HTTPException(status_code=400, detail=f"unsupported export format: {format!r}")
