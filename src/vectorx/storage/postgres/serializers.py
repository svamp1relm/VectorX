"""JSON-safe (de)serialization between core types and storage rows.

`profit_factor` can be `float("inf")`; JSON has no `Infinity` literal, so it
is deliberately excluded from `metrics_extra` and stored only in its own
native-float database column (see `vectorx.storage.postgres.models`).
"""

from vectorx.core.errors import VectorXError
from vectorx.core.types import (
    EquityPoint,
    ExpectancyComparison,
    ExpectancyEstimate,
    ExperimentSummary,
    HistogramBins,
    Metrics,
    RiskDefinition,
)


def metrics_extra_to_json(metrics: Metrics) -> dict:
    """The `Metrics` fields not already covered by dedicated `runs` columns."""
    return {
        "trades": metrics.trades,
        "wins": metrics.wins,
        "losses": metrics.losses,
        "avg_win": metrics.avg_win,
        "avg_loss": metrics.avg_loss,
        "avg_trade": metrics.avg_trade,
        "variance": metrics.variance,
    }


_METRICS_EXTRA_REQUIRED_KEYS = ("trades", "wins", "losses", "avg_win", "avg_loss", "avg_trade", "variance")


def metrics_extra_from_json(
    extra: dict,
    *,
    expectancy_theoretical: float | None,
    expectancy_sample: float,
    win_rate: float,
    total_return: float,
    max_drawdown: float,
    profit_factor: float,
    stdev: float,
    ruined: bool,
) -> Metrics:
    """Reassemble a full `Metrics` from `metrics_extra` plus the dedicated columns."""
    missing = [key for key in _METRICS_EXTRA_REQUIRED_KEYS if key not in extra]
    if missing:
        raise VectorXError(f"metrics_extra is missing required keys: {missing}")
    return Metrics(
        trades=extra["trades"],
        wins=extra["wins"],
        losses=extra["losses"],
        win_rate=win_rate,
        avg_win=extra["avg_win"],
        avg_loss=extra["avg_loss"],
        expectancy_theoretical=expectancy_theoretical,
        expectancy_sample=expectancy_sample,
        total_return=total_return,
        avg_trade=extra["avg_trade"],
        variance=extra["variance"],
        stdev=stdev,
        max_drawdown=max_drawdown,
        profit_factor=profit_factor,
        ruined=ruined,
    )


def equity_curve_to_json(curve: tuple[EquityPoint, ...]) -> list[dict]:
    return [{"index": p.index, "equity": p.equity, "drawdown": p.drawdown} for p in curve]


def equity_curve_from_json(data: list[dict]) -> tuple[EquityPoint, ...]:
    return tuple(
        EquityPoint(index=d["index"], equity=d["equity"], drawdown=d["drawdown"]) for d in data
    )


def _histogram_to_json(bins: HistogramBins) -> dict:
    return {"edges": list(bins.edges), "counts": list(bins.counts)}


def _histogram_from_json(data: dict) -> HistogramBins:
    return HistogramBins(edges=tuple(data["edges"]), counts=tuple(data["counts"]))


def _risk_definition_to_json(value: RiskDefinition) -> dict:
    return {
        "unit": value.unit,
        "normalization_version": value.normalization_version,
        "method": value.method,
        "risk_unit_fraction": value.risk_unit_fraction,
        "cost_basis": value.cost_basis,
    }


def _risk_definition_from_json(data: dict) -> RiskDefinition:
    return RiskDefinition(
        unit=data["unit"],
        normalization_version=data["normalization_version"],
        method=data["method"],
        risk_unit_fraction=data["risk_unit_fraction"],
        cost_basis=data["cost_basis"],
    )


def _expectancy_estimate_to_json(value: ExpectancyEstimate) -> dict:
    return {
        "value": value.value,
        "canonical_value": value.canonical_value,
        "source": value.source,
        "unit": value.unit,
        "sample_size": value.sample_size,
        "planned_sample_size": value.planned_sample_size,
        "risk_definition": _risk_definition_to_json(value.risk_definition),
    }


def _expectancy_estimate_from_json(data: dict) -> ExpectancyEstimate:
    return ExpectancyEstimate(
        value=data["value"],
        canonical_value=data.get("canonical_value"),
        source=data["source"],
        unit=data["unit"],
        sample_size=data["sample_size"],
        planned_sample_size=data["planned_sample_size"],
        risk_definition=_risk_definition_from_json(data["risk_definition"]),
    )


def expectancy_to_json(value: ExpectancyComparison | None) -> dict | None:
    if value is None:
        return None
    return {
        "theoretical": (
            _expectancy_estimate_to_json(value.theoretical) if value.theoretical else None
        ),
        "sample": _expectancy_estimate_to_json(value.sample) if value.sample else None,
        "historical": _expectancy_estimate_to_json(value.historical) if value.historical else None,
    }


def expectancy_from_json(data: dict | None) -> ExpectancyComparison | None:
    if data is None:
        return None
    return ExpectancyComparison(
        theoretical=(
            _expectancy_estimate_from_json(data["theoretical"]) if data["theoretical"] else None
        ),
        sample=_expectancy_estimate_from_json(data["sample"]) if data["sample"] else None,
        historical=(
            _expectancy_estimate_from_json(data["historical"]) if data["historical"] else None
        ),
    )


def summary_to_json(summary: ExperimentSummary) -> dict:
    return {
        "runs": summary.runs,
        "mean_total_return": summary.mean_total_return,
        "median_total_return": summary.median_total_return,
        "stdev_total_return": summary.stdev_total_return,
        "p_negative": summary.p_negative,
        "p_ruined": summary.p_ruined,
        "total_return_histogram": _histogram_to_json(summary.total_return_histogram),
        "r_multiple_histogram": _histogram_to_json(summary.r_multiple_histogram),
        "expectancy": expectancy_to_json(summary.expectancy),
    }


def summary_from_json(data: dict) -> ExperimentSummary:
    return ExperimentSummary(
        runs=data["runs"],
        mean_total_return=data["mean_total_return"],
        median_total_return=data["median_total_return"],
        stdev_total_return=data["stdev_total_return"],
        p_negative=data["p_negative"],
        p_ruined=data["p_ruined"],
        total_return_histogram=_histogram_from_json(data["total_return_histogram"]),
        r_multiple_histogram=_histogram_from_json(data["r_multiple_histogram"]),
        expectancy=expectancy_from_json(data.get("expectancy")),
    )
