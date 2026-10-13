"""ExperimentRunner: YAML spec -> N Monte Carlo runs -> RunResult[] + summary.

Uses an in-memory fake repository for now (Phase 8 adds Postgres behind
`ExperimentRepository`). Reproducibility is the core contract: same spec +
same seed must give identical per-run metrics and summary; a different seed
must not.
"""

import logging
from datetime import UTC, datetime, timedelta

import pytest

from vectorx.core.errors import ExperimentTooLargeError
from vectorx.core.rng import derived_seed_value
from vectorx.experiments.runner import MAX_OPERATIONS, run_experiment
from vectorx.experiments.spec import ExperimentSpec, parse_experiment_spec
from vectorx.experiments.versioning import EXPERIMENT_VERSION

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _spec(**overrides) -> ExperimentSpec:
    payload = {
        "name": "expectancy_test",
        "seed": 42,
        "runs": 5,
        "model": {"p_win": 0.55, "win_r": 2.0, "loss_r": -1.0, "n_trades": 20},
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
    }
    payload.update(overrides)
    return parse_experiment_spec(payload)


def _write_csv(tmp_path, closes: list[float]):
    path = tmp_path / "candles.csv"
    lines = ["timestamp,open,high,low,close,volume"]
    for i, close in enumerate(closes):
        ts = (_START + timedelta(hours=i)).isoformat()
        lines.append(f"{ts},{close},{close},{close},{close},1000.0")
    path.write_text("\n".join(lines) + "\n")
    return path


def _historical_spec(csv_path, **overrides) -> ExperimentSpec:
    payload = {
        "type": "historical_backtest",
        "name": "ma_crossover_test",
        "data": {"path": str(csv_path), "symbol": "BTCUSDT", "timeframe": "1h"},
        "strategy": {"fast_period": 2, "slow_period": 4, "stop_loss_pct": 0.01},
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
    }
    payload.update(overrides)
    return parse_experiment_spec(payload)


def test_same_seed_reproduces_identical_run_results_and_summary():
    spec = _spec()

    result_a = run_experiment(spec)
    result_b = run_experiment(spec)

    assert result_a.run_results == result_b.run_results
    assert result_a.summary == result_b.summary


def test_different_seed_diverges():
    result_a = run_experiment(_spec(seed=42))
    result_b = run_experiment(_spec(seed=43))

    assert result_a.run_results != result_b.run_results


def test_run_result_derived_seed_matches_core_rng_helper():
    spec = _spec(runs=3)

    result = run_experiment(spec)

    for run_result in result.run_results:
        expected = derived_seed_value(spec.seed, run_result.run_index)
        assert run_result.derived_seed == expected


def test_run_results_have_downsampled_equity_curve():
    spec = _spec(runs=1, model={"p_win": 0.55, "win_r": 2.0, "loss_r": -1.0, "n_trades": 600})

    result = run_experiment(spec)

    assert len(result.run_results[0].equity_curve) <= 500


def test_expectancy_sample_size_counts_executed_trades_after_ruin():
    spec = _spec(
        runs=2,
        model={"p_win": 0.0, "win_r": 2.0, "loss_r": -1.0, "n_trades": 5},
        portfolio={"initial_capital": 10_000.0, "risk_per_trade": 1.0},
    )

    result = run_experiment(spec)

    assert result.summary.expectancy.sample.sample_size == 2
    assert result.summary.expectancy.sample.planned_sample_size == 10


def test_experiment_result_metadata():
    spec = _spec(runs=4)

    result = run_experiment(spec)

    assert result.name == spec.name
    assert result.seed == spec.seed
    assert result.runs == spec.runs
    assert result.experiment_version == EXPERIMENT_VERSION
    assert isinstance(result.code_version, str) and result.code_version
    assert result.status == "completed"
    assert result.duration >= 0.0
    assert len(result.run_results) == spec.runs
    assert result.spec == spec


def test_operations_limit_raises_before_running():
    spec = _spec(runs=3, model={"p_win": 0.5, "win_r": 2.0, "loss_r": -1.0, "n_trades": 1_000_000})
    assert spec.runs * spec.model.n_trades > MAX_OPERATIONS

    with pytest.raises(ExperimentTooLargeError):
        run_experiment(spec)


def test_logs_start_and_end_at_info_without_per_run_debug_spam(caplog):
    caplog.set_level(logging.DEBUG)

    run_experiment(_spec(runs=10))

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(info_records) == 2
    assert not any("derived_seed" in r.getMessage() for r in caplog.records)


def test_historical_backtest_dispatch_produces_single_run_result(tmp_path):
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    csv_path = _write_csv(tmp_path, closes)
    spec = _historical_spec(csv_path)

    result = run_experiment(spec)

    assert result.runs == 1
    assert len(result.run_results) == 1
    assert result.run_results[0].metrics.expectancy_theoretical is None
    assert result.summary.runs == 1
    assert result.spec == spec


def test_historical_backtest_is_deterministic(tmp_path):
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    csv_path = _write_csv(tmp_path, closes)
    spec = _historical_spec(csv_path)

    result_a = run_experiment(spec)
    result_b = run_experiment(spec)

    assert result_a.run_results == result_b.run_results
    assert result_a.summary == result_b.summary


def test_historical_backtest_candle_limit_raises_before_running(tmp_path, monkeypatch):
    import vectorx.experiments.runner as runner_module

    monkeypatch.setattr(runner_module, "MAX_HISTORICAL_CANDLES", 3)
    csv_path = _write_csv(tmp_path, [100.0, 101.0, 102.0, 103.0, 104.0])
    spec = _historical_spec(csv_path)

    with pytest.raises(ExperimentTooLargeError):
        run_experiment(spec)


def test_monte_carlo_data_version_is_none():
    result = run_experiment(_spec())

    assert result.data_version is None


def test_historical_backtest_data_version_is_content_hash_of_csv(tmp_path):
    from vectorx.marketdata.csv_source import compute_data_version

    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    csv_path = _write_csv(tmp_path, closes)
    spec = _historical_spec(csv_path)

    result = run_experiment(spec)

    assert result.data_version == compute_data_version(csv_path)


def test_monte_carlo_store_trades_false_leaves_run_trades_none():
    spec = _spec(storage={"store_trades": False})

    result = run_experiment(spec)

    assert result.run_trades is None


def test_monte_carlo_store_trades_true_populates_run_trades_per_run():
    spec = _spec(runs=2, storage={"store_trades": True})

    result = run_experiment(spec)

    assert result.run_trades is not None
    assert len(result.run_trades) == 2
    for run_trades in result.run_trades:
        assert len(run_trades) == spec.model.n_trades


def test_historical_backtest_store_trades_true_populates_run_trades(tmp_path):
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    csv_path = _write_csv(tmp_path, closes)
    spec = _historical_spec(csv_path, storage={"store_trades": True})

    result = run_experiment(spec)

    assert result.run_trades is not None
    assert len(result.run_trades) == 1
    assert len(result.run_trades[0]) == result.run_results[0].metrics.trades


def test_buy_and_hold_benchmark_strategy_opens_one_trade_spanning_all_candles(tmp_path):
    closes = [100.0, 105.0, 110.0, 95.0, 120.0]
    csv_path = _write_csv(tmp_path, closes)
    spec = _historical_spec(
        csv_path, strategy={"type": "buy_and_hold", "stop_loss_pct": 0.5}
    )

    result = run_experiment(spec)

    assert result.run_results[0].metrics.trades == 1


def test_random_entry_benchmark_strategy_is_deterministic_for_same_seed(tmp_path):
    closes = [100.0 + i for i in range(60)]
    csv_path = _write_csv(tmp_path, closes)
    spec = _historical_spec(
        csv_path,
        seed=7,
        strategy={
            "type": "random_entry",
            "stop_loss_pct": 0.5,
            "entry_probability": 0.3,
            "exit_probability": 0.3,
        },
    )

    result_a = run_experiment(spec)
    result_b = run_experiment(spec)

    assert result_a.run_results == result_b.run_results


def test_random_entry_benchmark_strategy_diverges_for_different_seed(tmp_path):
    closes = [100.0 + i for i in range(60)]
    csv_path = _write_csv(tmp_path, closes)
    strategy = {
        "type": "random_entry",
        "stop_loss_pct": 0.5,
        "entry_probability": 0.3,
        "exit_probability": 0.3,
    }

    result_a = run_experiment(_historical_spec(csv_path, seed=1, strategy=strategy))
    result_b = run_experiment(_historical_spec(csv_path, seed=2, strategy=strategy))

    assert result_a.run_results != result_b.run_results
