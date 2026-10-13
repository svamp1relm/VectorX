"""Thin JSON-shaping helpers: domain dataclasses -> plain dicts.

No business logic here, only field selection. `profit_factor` can be
`float("inf")`; JSON (and Starlette's default encoder, `allow_nan=False`)
has no `Infinity` literal, so it is rendered as the string `"Infinity"`
here — the same issue and the same fix as `vectorx.storage.postgres`'s
metrics_extra split, applied at the API boundary instead of storage.
"""

import math

from vectorx.core.types import (
    EquityPoint,
    ExpectancyComparison,
    ExpectancyComparisonResult,
    ExpectancyEstimate,
    HistogramBins,
    Metrics,
    RiskDefinition,
    RunResult,
)
from vectorx.experiments.batch import ExperimentBatch
from vectorx.experiments.runner import ExperimentResult
from vectorx.statistics.confidence import ConfidenceInterval
from vectorx.statistics.risk_adjusted import RiskAdjustedMetrics
from vectorx.statistics.significance import SignificanceResult


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


def _risk_definition_to_dict(value: RiskDefinition) -> dict:
    return {
        "unit": value.unit,
        "normalization_version": value.normalization_version,
        "method": value.method,
        "risk_unit_fraction": value.risk_unit_fraction,
        "cost_basis": value.cost_basis,
    }


def _expectancy_estimate_to_dict(value: ExpectancyEstimate) -> dict:
    return {
        "value": value.value,
        "canonical_value": value.canonical_value,
        "source": value.source,
        "unit": value.unit,
        "sample_size": value.sample_size,
        "planned_sample_size": value.planned_sample_size,
        "risk_definition": _risk_definition_to_dict(value.risk_definition),
    }


def _expectancy_comparison_to_dict(value: ExpectancyComparison | None) -> dict | None:
    if value is None:
        return None
    return {
        "theoretical": (
            _expectancy_estimate_to_dict(value.theoretical) if value.theoretical else None
        ),
        "sample": _expectancy_estimate_to_dict(value.sample) if value.sample else None,
        "historical": _expectancy_estimate_to_dict(value.historical) if value.historical else None,
    }


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
        "expectancy": _expectancy_comparison_to_dict(summary.expectancy),
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
        "spec_type": result.spec.type,
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


def batch_summary_to_dict(batch: ExperimentBatch) -> dict:
    return {
        "id": batch.id,
        "hypothesis": batch.hypothesis,
        "notes": batch.notes,
        "created_at": batch.created_at.isoformat(),
        "experiment_count": len(batch.experiment_ids),
    }


def batch_detail_to_dict(batch: ExperimentBatch, experiments: list[dict]) -> dict:
    return {
        "id": batch.id,
        "hypothesis": batch.hypothesis,
        "notes": batch.notes,
        "created_at": batch.created_at.isoformat(),
        "experiments": experiments,
    }


def confidence_interval_to_dict(ci: ConfidenceInterval) -> dict:
    return {
        "point_estimate": ci.point_estimate,
        "lower": ci.lower,
        "upper": ci.upper,
        "confidence": ci.confidence,
        "n_resamples": ci.n_resamples,
    }


def risk_adjusted_metrics_to_dict(metrics: RiskAdjustedMetrics) -> dict:
    return {"sharpe": metrics.sharpe, "sortino": metrics.sortino, "calmar": metrics.calmar}


def significance_result_to_dict(result: SignificanceResult) -> dict:
    return {"ci": confidence_interval_to_dict(result.ci), "significant": result.significant}


def _risk_compatibility_to_dict(compatibility) -> dict:
    return {
        "compatible": compatibility.compatible,
        "same_risk_definition": compatibility.same_risk_definition,
        "reference_risk_fraction": compatibility.reference_risk_fraction,
        "mismatches": list(compatibility.mismatches),
    }


def expectancy_comparison_result_to_dict(result: ExpectancyComparisonResult) -> dict:
    return {
        "estimates": _expectancy_comparison_to_dict(result.estimates),
        "risk_compatibility": _risk_compatibility_to_dict(result.risk_compatibility),
        "deltas": {
            "delta_theoretical_sample": result.deltas.delta_theoretical_sample,
            "delta_theoretical_historical": result.deltas.delta_theoretical_historical,
            "delta_sample_historical": result.deltas.delta_sample_historical,
        },
        "warnings": list(result.warnings),
    }


def _run_experiment_result_to_dict(result: ExperimentResult) -> dict:
    """No `id` — used for ephemeral results (Фаза 20 OOS) that are never persisted."""
    return {
        "name": result.name,
        "seed": result.seed,
        "runs": result.runs,
        "status": result.status,
        "spec": result.spec.model_dump(mode="json"),
        "summary": _summary_to_dict(result.summary),
    }


def out_of_sample_result_to_dict(result) -> dict:
    return {
        "train": _run_experiment_result_to_dict(result.train),
        "test": _run_experiment_result_to_dict(result.test),
        "comparison": {
            "train": _expectancy_estimate_to_dict(result.comparison.train),
            "test": _expectancy_estimate_to_dict(result.comparison.test),
            "risk_compatibility": _risk_compatibility_to_dict(result.comparison.risk_compatibility),
            "delta_train_test": result.comparison.delta_train_test,
            "warnings": list(result.comparison.warnings),
        },
    }
