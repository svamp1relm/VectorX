"""Experiment CRUD, metrics, analysis, comparison, and export routes."""

from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.data_paths import secure_experiment_spec
from api.dependencies import get_repository
from api.routers.common import get_experiment_or_404
from api.schemas import ExpectancyComparisonRequest
from api.serialization import (
    confidence_interval_to_dict,
    equity_curve_to_dicts,
    expectancy_comparison_result_to_dict,
    experiment_detail_to_dict,
    experiment_summary_to_dict,
    risk_adjusted_metrics_to_dict,
    run_result_to_dict,
    significance_result_to_dict,
)
from vectorx.core.errors import AnalysisUnavailableError, ExperimentTooLargeError
from vectorx.experiments.export import render_json_report, render_markdown_report
from vectorx.experiments.runner import run_experiment
from vectorx.experiments.spec import (
    ExperimentSpec,
    HistoricalBacktestExperimentSpec,
    MonteCarloExperimentSpec,
)
from vectorx.statistics.expectancy_comparison import (
    build_expectancy_snapshot_from_run_metrics,
)
from vectorx.statistics.expectancy_comparison import (
    compare_expectancy as build_expectancy_comparison,
)
from vectorx.statistics.risk_adjusted import compute_calmar_ratio, compute_risk_adjusted_metrics
from vectorx.statistics.significance import significance_vs_zero
from vectorx.statistics.versioning import ANALYSIS_VERSION
from vectorx.storage.postgres.repository import PostgresExperimentRepository

router = APIRouter()
MAX_BOOTSTRAP_WORK = 20_000_000


@router.post("/experiments", status_code=201)
def create_experiment(
    spec: ExperimentSpec, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    result = run_experiment(secure_experiment_spec(spec))
    experiment_id = repo.save_experiment(result)
    return experiment_detail_to_dict(experiment_id, result)


@router.post("/experiments/{experiment_id}/run", status_code=201)
def rerun_experiment(
    experiment_id: int, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    existing = get_experiment_or_404(experiment_id, repo)
    result = run_experiment(existing.spec)
    new_id = repo.save_experiment(result)
    return experiment_detail_to_dict(new_id, result)


@router.get("/experiments")
def list_experiments(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, gt=0, le=100),
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> list[dict]:
    return [
        experiment_summary_to_dict(experiment_id, result)
        for experiment_id, result in repo.list_experiment_summaries(
            offset=offset,
            limit=limit,
        )
    ]


@router.get("/experiments/{experiment_id}")
def get_experiment(
    experiment_id: int, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    result = get_experiment_or_404(experiment_id, repo)
    return experiment_detail_to_dict(experiment_id, result)


@router.get("/experiments/{experiment_id}/results")
def get_experiment_results(
    experiment_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, gt=0, le=100),
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> list[dict]:
    result = get_experiment_or_404(experiment_id, repo)
    runs = result.run_results[offset : offset + limit]
    return [run_result_to_dict(run, include_equity=False) for run in runs]


def _find_run_or_404(result, run_id: int):
    for run in result.run_results:
        if run.run_index == run_id:
            return run
    raise HTTPException(status_code=404, detail="run not found")


@router.get("/experiments/{experiment_id}/runs/{run_id}")
def get_run(
    experiment_id: int,
    run_id: int,
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> dict:
    result = get_experiment_or_404(experiment_id, repo)
    run = _find_run_or_404(result, run_id)
    return run_result_to_dict(run, include_equity=True)


@router.get("/experiments/{experiment_id}/equity")
def get_equity(
    experiment_id: int,
    run_id: int = 0,
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> list[dict]:
    result = get_experiment_or_404(experiment_id, repo)
    run = _find_run_or_404(result, run_id)
    return equity_curve_to_dicts(run.equity_curve)


@router.post("/comparisons/expectancy")
def compare_expectancy(
    payload: ExpectancyComparisonRequest,
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> dict:
    monte_carlo = get_experiment_or_404(payload.monte_carlo_experiment_id, repo)
    historical = get_experiment_or_404(payload.historical_experiment_id, repo)
    if not isinstance(monte_carlo.spec, MonteCarloExperimentSpec):
        raise HTTPException(
            status_code=422,
            detail="monte_carlo_experiment_id must reference a Monte Carlo experiment",
        )
    if not isinstance(historical.spec, HistoricalBacktestExperimentSpec):
        raise HTTPException(
            status_code=422,
            detail="historical_experiment_id must reference a historical backtest experiment",
        )

    result = build_expectancy_comparison(
        monte_carlo=_expectancy_snapshot(monte_carlo),
        historical=_expectancy_snapshot(historical),
        reference_risk_fraction=payload.reference_risk_fraction,
    )
    return expectancy_comparison_result_to_dict(result)


def _expectancy_snapshot(result):
    if result.summary.expectancy is not None:
        return result.summary.expectancy
    run_metrics = tuple(run.metrics for run in result.run_results)
    return build_expectancy_snapshot_from_run_metrics(result.spec, run_metrics)


@router.get("/experiments/{experiment_id}/analysis")
def get_analysis(
    experiment_id: int,
    seed: int = Query(default=0, ge=0),
    confidence: float = Query(default=0.95, gt=0.0, lt=1.0),
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> dict:
    result = get_experiment_or_404(experiment_id, repo)
    if not result.spec.storage.store_trades:
        raise AnalysisUnavailableError(
            "experiment was not saved with storage.store_trades=true; no raw trades to analyze"
        )

    trade_runs = repo.get_analysis_trade_runs(experiment_id)
    sample_size = sum(len(run) for run in trade_runs)
    if sample_size * 2000 > MAX_BOOTSTRAP_WORK:
        raise ExperimentTooLargeError(
            f"analysis work budget exceeded: {sample_size} trades * 2000 resamples"
        )
    r_multiples = [gross for run in trade_runs for gross, _net in run]
    net_r_multiples = [
        net if net is not None else gross
        for run in trade_runs
        for gross, net in run
    ]
    significance = significance_vs_zero(r_multiples, seed=seed, confidence=confidence)
    significance_net = significance_vs_zero(net_r_multiples, seed=seed, confidence=confidence)
    max_drawdown = max(run.metrics.max_drawdown for run in result.run_results)
    risk_adjusted = compute_risk_adjusted_metrics(
        r_multiples,
        total_return=result.summary.mean_total_return,
        max_drawdown=max_drawdown,
    )
    risk_adjusted_net = compute_risk_adjusted_metrics(
        net_r_multiples,
        total_return=result.summary.mean_total_return,
        max_drawdown=max_drawdown,
    )
    if len(result.run_results) > 1:
        risk_adjusted = replace(risk_adjusted, calmar=None)
        risk_adjusted_net = replace(risk_adjusted_net, calmar=None)
    calmar_by_run = [
        {
            "run_index": run.run_index,
            "calmar": compute_calmar_ratio(
                run.metrics.total_return,
                run.metrics.max_drawdown,
            ),
        }
        for run in result.run_results
    ]
    return {
        "analysis_version": ANALYSIS_VERSION,
        "confidence_interval": confidence_interval_to_dict(significance.ci),
        "risk_adjusted": risk_adjusted_metrics_to_dict(risk_adjusted),
        "significance_vs_zero": significance_result_to_dict(significance),
        "confidence_interval_net": confidence_interval_to_dict(significance_net.ci),
        "risk_adjusted_net": risk_adjusted_metrics_to_dict(risk_adjusted_net),
        "significance_vs_zero_net": significance_result_to_dict(significance_net),
        "calmar_by_run": calmar_by_run,
    }


@router.get("/experiments/{experiment_id}/export")
def export_experiment(
    experiment_id: int,
    format: str = "json",
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> Response:
    result = get_experiment_or_404(experiment_id, repo)
    batch_id = repo.get_batch_id_for_experiment(experiment_id)
    batch = repo.get_batch(batch_id) if batch_id is not None else None

    if format == "json":
        return Response(content=render_json_report(result, batch=batch), media_type="application/json")
    if format == "markdown":
        return Response(
            content=render_markdown_report(result, batch=batch),
            media_type="text/markdown",
        )
    raise HTTPException(status_code=400, detail=f"unsupported export format: {format!r}")
