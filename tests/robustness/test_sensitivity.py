"""run_sensitivity_analysis: parameter sensitivity over a sweep grid (Фаза 21).

Pure composition of existing building blocks: `generate_sweep_specs` (Фаза
18c) expands the grid, `run_experiment` (unchanged) runs each combination,
and the per-combination expectancy/Sharpe are derived from its (forced)
raw trades (Фаза 18a/19). No new simulation logic — this is "already have
these pieces, just run many of them and report a summary per combination."
"""

from datetime import UTC, datetime, timedelta

import pytest

from vectorx.core.errors import ExperimentTooLargeError
from vectorx.experiments.sweep import SweepSpec
from vectorx.robustness.sensitivity import run_sensitivity_analysis

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _write_csv(tmp_path, closes: list[float]):
    path = tmp_path / "candles.csv"
    lines = ["timestamp,open,high,low,close,volume"]
    for i, close in enumerate(closes):
        ts = (_START + timedelta(hours=i)).isoformat()
        lines.append(f"{ts},{close},{close},{close},{close},1000.0")
    path.write_text("\n".join(lines) + "\n")
    return path


def _base(csv_path) -> dict:
    return {
        "type": "historical_backtest",
        "name": "sensitivity_test",
        "data": {"path": str(csv_path), "symbol": "BTCUSDT", "timeframe": "1h"},
        "strategy": {"type": "moving_average_crossover", "fast_period": 2, "slow_period": 4, "stop_loss_pct": 0.05},
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.05},
    }


def test_one_dimensional_grid_produces_one_point_per_value(tmp_path):
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    csv_path = _write_csv(tmp_path, closes)
    sweep = SweepSpec(
        hypothesis="fast_period sensitivity",
        base=_base(csv_path),
        grid={"strategy.fast_period": [2, 3]},
    )

    result = run_sensitivity_analysis(sweep)

    assert len(result.points) == 2
    fast_periods = {point.params["strategy.fast_period"] for point in result.points}
    assert fast_periods == {2, 3}
    for point in result.points:
        assert isinstance(point.expectancy_sample, float)


def test_two_dimensional_grid_produces_cartesian_product_of_points(tmp_path):
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    csv_path = _write_csv(tmp_path, closes)
    sweep = SweepSpec(
        hypothesis="2d sensitivity",
        base=_base(csv_path),
        grid={"strategy.fast_period": [2, 3], "strategy.slow_period": [4, 5]},
    )

    result = run_sensitivity_analysis(sweep)

    assert len(result.points) == 4


def test_is_deterministic(tmp_path):
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    csv_path = _write_csv(tmp_path, closes)
    sweep = SweepSpec(
        hypothesis="determinism", base=_base(csv_path), grid={"strategy.fast_period": [2, 3]}
    )

    result_a = run_sensitivity_analysis(sweep)
    result_b = run_sensitivity_analysis(sweep)

    assert result_a == result_b


def test_resource_guard_propagates(tmp_path):
    from vectorx.experiments.sweep import MAX_BATCH_EXPERIMENTS

    csv_path = _write_csv(tmp_path, [100.0] * 5)
    sweep = SweepSpec(
        hypothesis="too big",
        base=_base(csv_path),
        grid={"seed": list(range(MAX_BATCH_EXPERIMENTS + 1))},
    )

    with pytest.raises(ExperimentTooLargeError):
        run_sensitivity_analysis(sweep)
