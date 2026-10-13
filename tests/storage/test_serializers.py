"""JSON-safe (de)serialization for storage: pure functions, no DB needed.

`profit_factor` (which can be `float("inf")`) is deliberately kept OUT of
any JSON blob — JSON has no `Infinity` literal, so it lives only in its own
native-float database column. `metrics_extra` carries the remaining
`Metrics` fields not already covered by dedicated `runs` columns.
"""


from vectorx.core.types import (
    EquityPoint,
    ExpectancyComparison,
    ExpectancyEstimate,
    ExperimentSummary,
    HistogramBins,
    Metrics,
    RiskDefinition,
)
from vectorx.storage.postgres.serializers import (
    equity_curve_from_json,
    equity_curve_to_json,
    metrics_extra_from_json,
    metrics_extra_to_json,
    summary_from_json,
    summary_to_json,
)


def _metrics(profit_factor: float = 2.0) -> Metrics:
    return Metrics(
        trades=4,
        wins=2,
        losses=2,
        win_rate=0.5,
        avg_win=2.0,
        avg_loss=-1.0,
        expectancy_theoretical=0.5,
        expectancy_sample=0.5,
        total_return=0.0197,
        avg_trade=49.24,
        variance=2.25,
        stdev=1.5,
        max_drawdown=0.01,
        profit_factor=profit_factor,
        ruined=False,
    )


def test_metrics_extra_round_trip_excludes_profit_factor():
    metrics = _metrics()

    extra = metrics_extra_to_json(metrics)

    assert "profit_factor" not in extra
    assert extra == {
        "trades": 4,
        "wins": 2,
        "losses": 2,
        "avg_win": 2.0,
        "avg_loss": -1.0,
        "avg_trade": 49.24,
        "variance": 2.25,
    }


def test_metrics_extra_round_trip_reconstructs_full_metrics():
    metrics = _metrics()
    extra = metrics_extra_to_json(metrics)

    rebuilt = metrics_extra_from_json(
        extra,
        expectancy_theoretical=metrics.expectancy_theoretical,
        expectancy_sample=metrics.expectancy_sample,
        win_rate=metrics.win_rate,
        total_return=metrics.total_return,
        max_drawdown=metrics.max_drawdown,
        profit_factor=metrics.profit_factor,
        stdev=metrics.stdev,
        ruined=metrics.ruined,
    )

    assert rebuilt == metrics


def test_metrics_extra_json_is_serializable_even_with_infinite_profit_factor():
    import json

    metrics = _metrics(profit_factor=float("inf"))

    extra = metrics_extra_to_json(metrics)

    json.dumps(extra)  # must not raise


def test_equity_curve_round_trip():
    curve = (
        EquityPoint(index=0, equity=10_000.0, drawdown=0.0),
        EquityPoint(index=1, equity=10_200.0, drawdown=0.0),
    )

    as_json = equity_curve_to_json(curve)
    rebuilt = equity_curve_from_json(as_json)

    assert rebuilt == curve
    import json

    json.dumps(as_json)  # must not raise


def test_summary_round_trip():
    estimate = ExpectancyEstimate(
        value=0.5,
        canonical_value=None,
        source="monte_carlo_sample",
        unit="R",
        sample_size=100_000,
        planned_sample_size=100_000,
        risk_definition=RiskDefinition(
            unit="R",
            normalization_version="r-v1",
            method="model_r",
            risk_unit_fraction=0.01,
            cost_basis="gross_r",
        ),
    )
    summary = ExperimentSummary(
        runs=4,
        mean_total_return=0.0575,
        median_total_return=0.04,
        stdev_total_return=0.099,
        p_negative=0.5,
        p_ruined=0.25,
        total_return_histogram=HistogramBins(edges=(0.0, 1.0), counts=(4,)),
        r_multiple_histogram=HistogramBins(edges=(-1.0, 2.0), counts=(2, 2)),
        expectancy=ExpectancyComparison(sample=estimate),
    )

    as_json = summary_to_json(summary)
    rebuilt = summary_from_json(as_json)

    assert rebuilt == summary
    import json

    json.dumps(as_json)  # must not raise


def test_legacy_summary_without_expectancy_loads_as_none():
    summary = ExperimentSummary(
        runs=1,
        mean_total_return=0.0,
        median_total_return=0.0,
        stdev_total_return=0.0,
        p_negative=0.0,
        p_ruined=0.0,
        total_return_histogram=HistogramBins(edges=(0.0, 1.0), counts=(1,)),
        r_multiple_histogram=HistogramBins(edges=(-1.0, 1.0), counts=(1,)),
    )
    as_json = summary_to_json(summary)
    del as_json["expectancy"]

    rebuilt = summary_from_json(as_json)

    assert rebuilt.expectancy is None
