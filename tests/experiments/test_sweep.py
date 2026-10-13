"""SweepSpec/generate_sweep_specs: one hypothesis x parameter grid -> N ExperimentSpec (Фаза 18c).

Pure function — no execution, no storage. The resource guard
(`MAX_BATCH_EXPERIMENTS`) fires before any `ExperimentSpec` is even
constructed, by design (same pattern as `MAX_OPERATIONS`/`MAX_HISTORICAL_CANDLES`
in `vectorx.experiments.runner`).
"""

import pytest

from vectorx.core.errors import ExperimentTooLargeError
from vectorx.experiments.spec import HistoricalBacktestExperimentSpec, MonteCarloExperimentSpec
from vectorx.experiments.sweep import MAX_BATCH_EXPERIMENTS, SweepSpec, generate_sweep_specs

_MC_BASE = {
    "name": "sweep_test",
    "seed": 42,
    "runs": 5,
    "model": {"p_win": 0.55, "win_r": 2.0, "loss_r": -1.0, "n_trades": 20},
    "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
}

_HIST_BASE = {
    "type": "historical_backtest",
    "name": "sweep_hist_test",
    "data": {"path": "data.csv", "symbol": "BTCUSDT", "timeframe": "1h"},
    "strategy": {"fast_period": 10, "slow_period": 30, "stop_loss_pct": 0.01},
    "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
}


def test_cartesian_product_generates_one_spec_per_combination():
    sweep = SweepSpec(
        hypothesis="fast/slow period matters",
        base=_HIST_BASE,
        grid={"strategy.fast_period": [8, 10], "strategy.slow_period": [20, 30, 40]},
    )

    specs = generate_sweep_specs(sweep)

    assert len(specs) == 6
    pairs = {(s.strategy.fast_period, s.strategy.slow_period) for s in specs}
    assert pairs == {(8, 20), (8, 30), (8, 40), (10, 20), (10, 30), (10, 40)}


def test_empty_grid_generates_exactly_one_spec_from_base():
    sweep = SweepSpec(hypothesis="baseline only", base=_MC_BASE, grid={})

    specs = generate_sweep_specs(sweep)

    assert len(specs) == 1
    assert isinstance(specs[0], MonteCarloExperimentSpec)


def test_generated_specs_have_unique_names():
    sweep = SweepSpec(hypothesis="h", base=_MC_BASE, grid={"model.p_win": [0.5, 0.55, 0.6]})

    specs = generate_sweep_specs(sweep)

    assert len({s.name for s in specs}) == 3


def test_generated_specs_force_store_trades_true():
    sweep = SweepSpec(hypothesis="h", base=_MC_BASE, grid={"model.p_win": [0.5, 0.6]})

    specs = generate_sweep_specs(sweep)

    assert all(s.storage.store_trades is True for s in specs)


def test_resource_guard_blocks_before_generating():
    sweep = SweepSpec(
        hypothesis="too big",
        base=_MC_BASE,
        grid={"seed": list(range(MAX_BATCH_EXPERIMENTS + 1))},
    )

    with pytest.raises(ExperimentTooLargeError):
        generate_sweep_specs(sweep)


def test_grid_overrides_nested_fields_without_losing_sibling_fields():
    sweep = SweepSpec(
        hypothesis="h",
        base=_HIST_BASE,
        grid={"strategy.fast_period": [5, 6]},
    )

    specs = generate_sweep_specs(sweep)

    for spec in specs:
        assert isinstance(spec, HistoricalBacktestExperimentSpec)
        # slow_period/stop_loss_pct from base must survive the fast_period override
        assert spec.strategy.slow_period == 30
        assert spec.strategy.stop_loss_pct == 0.01
