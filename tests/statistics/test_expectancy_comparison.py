from vectorx.core.types import (
    ComparisonDeltas,
    ExpectancyComparison,
    ExpectancyEstimate,
    Metrics,
    RiskDefinition,
)
from vectorx.experiments.spec import parse_experiment_spec
from vectorx.statistics.expectancy_comparison import (
    build_expectancy_snapshot,
    build_expectancy_snapshot_from_run_metrics,
    compare_expectancy,
    compare_train_test_expectancy,
)


def _monte_carlo_spec(risk_unit_fraction=0.01, n_trades=4, runs=2):
    return parse_experiment_spec(
        {
            "type": "monte_carlo",
            "name": "mc",
            "seed": 1,
            "runs": runs,
            "model": {
                "p_win": 0.5,
                "win_r": 2.0,
                "loss_r": -1.0,
                "n_trades": n_trades,
                "risk_unit_fraction": risk_unit_fraction,
            },
            "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
        }
    )


def _historical_spec(stop_loss_pct=0.02):
    return parse_experiment_spec(
        {
            "type": "historical_backtest",
            "name": "historical",
            "data": {"path": "data.csv", "symbol": "BTCUSDT", "timeframe": "1h"},
            "strategy": {
                "fast_period": 2,
                "slow_period": 4,
                "stop_loss_pct": stop_loss_pct,
            },
            "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
        }
    )


def _metrics(trades, expectancy_sample):
    return Metrics(
        trades=trades,
        wins=0,
        losses=0,
        win_rate=0.0,
        avg_win=0.0,
        avg_loss=0.0,
        expectancy_theoretical=None,
        expectancy_sample=expectancy_sample,
        total_return=0.0,
        avg_trade=0.0,
        variance=0.0,
        stdev=0.0,
        max_drawdown=0.0,
        profit_factor=0.0,
        ruined=False,
    )


def test_snapshot_sample_size_counts_trades_and_planned_sample_size_counts_plan():
    spec = _monte_carlo_spec(n_trades=5, runs=2)
    run_metrics = (_metrics(5, 0.5), _metrics(3, 0.25))
    all_r_multiples = [1.0, 1.0, 1.0, 1.0, 1.0, -1.0, -1.0, -1.0]

    snapshot = build_expectancy_snapshot(spec, run_metrics, all_r_multiples)

    assert snapshot.sample.sample_size == 8
    assert snapshot.sample.planned_sample_size == 10
    assert snapshot.sample.value == 0.25
    assert snapshot.theoretical.sample_size is None
    assert snapshot.theoretical.planned_sample_size is None


def test_snapshot_rebuilt_from_run_metrics_uses_trade_weighted_sample():
    spec = _monte_carlo_spec()
    run_metrics = (_metrics(1, 1.0), _metrics(3, -0.5))

    snapshot = build_expectancy_snapshot_from_run_metrics(spec, run_metrics)

    assert snapshot.sample.sample_size == 4
    assert snapshot.sample.planned_sample_size == 8
    assert snapshot.sample.value == -0.125


def test_snapshot_from_raw_r_multiples_and_from_run_metrics_agree():
    # build_expectancy_snapshot (raw trades) and
    # build_expectancy_snapshot_from_run_metrics (pre-aggregated Metrics) compute
    # pooled sample expectancy two different ways; they must not drift apart.
    spec = _monte_carlo_spec(n_trades=2, runs=2)
    run_1_r_multiples = [1.0, -1.0]
    run_2_r_multiples = [2.0, 0.0]
    all_r_multiples = run_1_r_multiples + run_2_r_multiples
    run_metrics = (
        _metrics(len(run_1_r_multiples), sum(run_1_r_multiples) / len(run_1_r_multiples)),
        _metrics(len(run_2_r_multiples), sum(run_2_r_multiples) / len(run_2_r_multiples)),
    )

    from_raw = build_expectancy_snapshot(spec, run_metrics, all_r_multiples)
    from_metrics = build_expectancy_snapshot_from_run_metrics(spec, run_metrics)

    assert from_raw.sample.value == from_metrics.sample.value
    assert from_raw.sample.sample_size == from_metrics.sample.sample_size


def test_comparison_converts_different_risk_units_to_reference_scale():
    monte_carlo = build_expectancy_snapshot(
        _monte_carlo_spec(risk_unit_fraction=0.01),
        (_metrics(2, 0.5),),
        [1.0, 0.0],
    )
    historical = build_expectancy_snapshot(
        _historical_spec(stop_loss_pct=0.02),
        (_metrics(2, 0.5),),
        [1.0, 0.0],
    )

    result = compare_expectancy(monte_carlo, historical, reference_risk_fraction=0.01)

    assert result.risk_compatibility.compatible is True
    assert result.risk_compatibility.same_risk_definition is False
    assert result.estimates.theoretical.canonical_value == 0.5
    assert result.estimates.sample.canonical_value == 0.5
    assert result.estimates.historical.canonical_value == 1.0
    assert result.deltas.delta_theoretical_sample == 0.0
    assert result.deltas.delta_theoretical_historical == -0.5
    assert result.deltas.delta_sample_historical == -0.5
    assert result.warnings == ("risk_definitions_converted",)


def test_incompatible_risk_definitions_return_no_deltas():
    risk_definition = RiskDefinition(
        unit="R",
        normalization_version="r-v1",
        method="unknown",
        risk_unit_fraction=0.01,
        cost_basis="gross_r",
    )
    estimate = ExpectancyEstimate(
        value=0.5,
        canonical_value=None,
        source="theoretical_model",
        unit="R",
        sample_size=None,
        planned_sample_size=None,
        risk_definition=risk_definition,
    )

    result = compare_expectancy(
        ExpectancyComparison(theoretical=estimate),
        ExpectancyComparison(),
        reference_risk_fraction=0.01,
    )

    assert result.deltas == ComparisonDeltas()
    assert result.warnings == ("risk_definitions_incompatible",)


def test_compare_train_test_expectancy_computes_delta_for_compatible_estimates():
    train = build_expectancy_snapshot(
        _historical_spec(stop_loss_pct=0.02), (_metrics(2, 1.0),), [1.0, 1.0]
    )
    test = build_expectancy_snapshot(
        _historical_spec(stop_loss_pct=0.02), (_metrics(2, -0.5),), [-0.5, -0.5]
    )

    result = compare_train_test_expectancy(train.historical, test.historical)

    assert result.risk_compatibility.compatible is True
    assert result.risk_compatibility.same_risk_definition is True
    assert result.delta_train_test == 3.0
    assert result.warnings == ()


def test_compare_train_test_expectancy_converts_different_risk_units():
    train = build_expectancy_snapshot(
        _historical_spec(stop_loss_pct=0.01), (_metrics(2, 1.0),), [1.0, 1.0]
    )
    test = build_expectancy_snapshot(
        _historical_spec(stop_loss_pct=0.02), (_metrics(2, 1.0),), [1.0, 1.0]
    )

    result = compare_train_test_expectancy(
        train.historical, test.historical, reference_risk_fraction=0.01
    )

    assert result.risk_compatibility.compatible is True
    assert result.train.canonical_value == 1.0
    assert result.test.canonical_value == 2.0
    assert result.delta_train_test == -1.0
    assert result.warnings == ("risk_definitions_converted",)


def test_compare_train_test_expectancy_incompatible_definitions_return_no_delta():
    risk_definition = RiskDefinition(
        unit="R",
        normalization_version="r-v1",
        method="unknown",
        risk_unit_fraction=0.01,
        cost_basis="gross_r",
    )
    estimate = ExpectancyEstimate(
        value=0.5,
        canonical_value=None,
        source="historical_backtest",
        unit="R",
        sample_size=None,
        planned_sample_size=None,
        risk_definition=risk_definition,
    )

    result = compare_train_test_expectancy(estimate, estimate, reference_risk_fraction=0.01)

    assert result.delta_train_test is None
    assert result.warnings == ("risk_definitions_incompatible",)
