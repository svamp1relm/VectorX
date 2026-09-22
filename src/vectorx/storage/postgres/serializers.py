"""JSON-safe (de)serialization between core types and storage rows.

`profit_factor` can be `float("inf")`; JSON has no `Infinity` literal, so it
is deliberately excluded from `metrics_extra` and stored only in its own
native-float database column (see `vectorx.storage.postgres.models`).
"""

from vectorx.core.types import EquityPoint, ExperimentSummary, HistogramBins, Metrics


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


def metrics_extra_from_json(
    extra: dict,
    *,
    expectancy_theoretical: float,
    expectancy_sample: float,
    win_rate: float,
    total_return: float,
    max_drawdown: float,
    profit_factor: float,
    stdev: float,
    ruined: bool,
) -> Metrics:
    """Reassemble a full `Metrics` from `metrics_extra` plus the dedicated columns."""
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
    )
