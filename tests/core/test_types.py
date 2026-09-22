"""Core domain types: Trade, EquityPoint, Metrics, RunResult, ExperimentSummary."""

from vectorx.core.types import (
    EquityPoint,
    ExperimentSummary,
    HistogramBins,
    Metrics,
    RunResult,
    Trade,
)


def test_trade_minimal_construction_has_expected_defaults():
    trade = Trade(trade_index=0, side="long", r_multiple=2.0)

    assert trade.trade_index == 0
    assert trade.side == "long"
    assert trade.r_multiple == 2.0
    assert trade.risk == 1.0
    assert trade.id is None
    assert trade.entry_ts is None
    assert trade.exit_ts is None
    assert trade.pnl is None
    assert trade.size is None
    assert trade.pnl_money is None


def test_trade_is_immutable():
    trade = Trade(trade_index=0, side="long", r_multiple=2.0)
    try:
        trade.r_multiple = 3.0
    except AttributeError:
        pass
    else:
        raise AssertionError("Trade must be immutable")


def test_equity_point_construction():
    point = EquityPoint(index=0, equity=10_000.0, drawdown=0.0)

    assert point.index == 0
    assert point.equity == 10_000.0
    assert point.drawdown == 0.0


def test_metrics_construction():
    metrics = Metrics(
        trades=100,
        wins=55,
        losses=45,
        win_rate=0.55,
        avg_win=2.0,
        avg_loss=-1.0,
        expectancy_theoretical=0.65,
        expectancy_sample=0.6,
        total_return=0.25,
        avg_trade=0.006,
        variance=1.2,
        stdev=1.0954,
        max_drawdown=0.1,
        profit_factor=1.5,
        ruined=False,
    )

    assert metrics.trades == 100
    assert metrics.expectancy_theoretical == 0.65
    assert metrics.ruined is False


def test_histogram_bins_construction():
    bins = HistogramBins(edges=(0.0, 1.0, 2.0), counts=(3, 5))

    assert bins.edges == (0.0, 1.0, 2.0)
    assert bins.counts == (3, 5)


def test_run_result_construction():
    metrics = Metrics(
        trades=1,
        wins=1,
        losses=0,
        win_rate=1.0,
        avg_win=2.0,
        avg_loss=0.0,
        expectancy_theoretical=0.65,
        expectancy_sample=2.0,
        total_return=0.02,
        avg_trade=2.0,
        variance=0.0,
        stdev=0.0,
        max_drawdown=0.0,
        profit_factor=float("inf"),
        ruined=False,
    )
    equity_curve = (EquityPoint(index=0, equity=10_000.0, drawdown=0.0),)

    result = RunResult(
        run_index=0,
        derived_seed=123,
        metrics=metrics,
        equity_curve=equity_curve,
    )

    assert result.run_index == 0
    assert result.derived_seed == 123
    assert result.metrics is metrics
    assert result.equity_curve == equity_curve


def test_experiment_summary_construction():
    total_return_hist = HistogramBins(edges=(0.0, 1.0), counts=(1,))
    r_multiple_hist = HistogramBins(edges=(-1.0, 2.0), counts=(1,))

    summary = ExperimentSummary(
        runs=100,
        mean_total_return=0.1,
        median_total_return=0.09,
        stdev_total_return=0.05,
        p_negative=0.2,
        p_ruined=0.0,
        total_return_histogram=total_return_hist,
        r_multiple_histogram=r_multiple_hist,
    )

    assert summary.runs == 100
    assert summary.p_negative == 0.2
    assert summary.p_ruined == 0.0
    assert summary.total_return_histogram is total_return_hist
    assert summary.r_multiple_histogram is r_multiple_hist
