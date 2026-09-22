"""Thin JSON-shaping helpers: domain dataclasses -> plain dicts.

No business logic here, only field selection. `profit_factor` can be
`float("inf")`; JSON (and Starlette's default encoder, `allow_nan=False`)
has no `Infinity` literal, so it is rendered as the string `"Infinity"`
here — the same issue and the same fix as `vectorx.storage.postgres`'s
metrics_extra split, applied at the API boundary instead of storage.
"""

import math

from vectorx.core.types import EquityPoint, HistogramBins, Metrics, RunResult
from vectorx.experiments.runner import ExperimentResult


def _json_safe_float(value: float) -> float | str:
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if math.isnan(value):
        return "NaN"
    return value


def _equity_point_to_dict(point: EquityPoint) -> dict:
    return {"index": point.index, "equity": point.equity, "drawdown": point.drawdown}


def _histogram_to_dict(bins: HistogramBins) -> dict:
    return {"edges": list(bins.edges), "counts": list(bins.counts)}


def _summary_to_dict(summary) -> dict:
    return {
        "runs": summary.runs,
        "mean_total_return": summary.mean_total_return,
        "median_total_return": summary.median_total_return,
        "stdev_total_return": summary.stdev_total_return,
        "p_negative": summary.p_negative,
        "p_ruined": summary.p_ruined,
        "total_return_histogram": _histogram_to_dict(summary.total_return_histogram),
        "r_multiple_histogram": _histogram_to_dict(summary.r_multiple_histogram),
    }


def _metrics_to_dict(metrics: Metrics) -> dict:
    return {
        "trades": metrics.trades,
        "wins": metrics.wins,
        "losses": metrics.losses,
        "win_rate": metrics.win_rate,
        "avg_win": metrics.avg_win,
        "avg_loss": metrics.avg_loss,
        "expectancy_theoretical": metrics.expectancy_theoretical,
        "expectancy_sample": metrics.expectancy_sample,
        "total_return": metrics.total_return,
        "avg_trade": metrics.avg_trade,
        "variance": metrics.variance,
        "stdev": metrics.stdev,
        "max_drawdown": metrics.max_drawdown,
        "profit_factor": _json_safe_float(metrics.profit_factor),
        "ruined": metrics.ruined,
    }


def equity_curve_to_dicts(curve: tuple[EquityPoint, ...]) -> list[dict]:
    return [_equity_point_to_dict(point) for point in curve]


def run_result_to_dict(run_result: RunResult, *, include_equity: bool) -> dict:
    payload = {
        "run_index": run_result.run_index,
        "derived_seed": run_result.derived_seed,
        "metrics": _metrics_to_dict(run_result.metrics),
    }
    if include_equity:
        payload["equity_curve"] = equity_curve_to_dicts(run_result.equity_curve)
    return payload


def experiment_summary_to_dict(experiment_id: int, result: ExperimentResult) -> dict:
    return {
        "id": experiment_id,
        "name": result.name,
        "seed": result.seed,
        "runs": result.runs,
        "status": result.status,
        "created_at": result.created_at.isoformat(),
        "experiment_version": result.experiment_version,
        "code_version": result.code_version,
        "mean_total_return": result.summary.mean_total_return,
        "median_total_return": result.summary.median_total_return,
        "stdev_total_return": result.summary.stdev_total_return,
        "p_negative": result.summary.p_negative,
        "p_ruined": result.summary.p_ruined,
    }


def experiment_detail_to_dict(experiment_id: int, result: ExperimentResult) -> dict:
    return {
        "id": experiment_id,
        "name": result.name,
        "seed": result.seed,
        "runs": result.runs,
        "status": result.status,
        "created_at": result.created_at.isoformat(),
        "duration": result.duration,
        "experiment_version": result.experiment_version,
        "code_version": result.code_version,
        "spec": result.spec.model_dump(mode="json"),
        "summary": _summary_to_dict(result.summary),
    }
