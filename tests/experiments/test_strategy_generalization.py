"""Фаза 22 litmus test: `BreakoutStrategy` runs through the entire 18-21
pipeline (sweep engine, statistical toolkit, Out-of-Sample, Robustness)
*unchanged* — exercising it here is the acceptance criterion itself: if any
of these needed a strategy-specific branch to support `breakout`, Фазы 18-21
would not have been generalized correctly.
"""

from datetime import UTC, datetime, timedelta

from vectorx.experiments.out_of_sample import OutOfSampleSpec, run_out_of_sample
from vectorx.experiments.runner import run_experiment
from vectorx.experiments.spec import parse_experiment_spec
from vectorx.experiments.sweep import SweepSpec, generate_sweep_specs
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


def _breakout_base(csv_path, **overrides) -> dict:
    payload = {
        "type": "historical_backtest",
        "name": "breakout_generalization_test",
        "data": {"path": str(csv_path), "symbol": "BTCUSDT", "timeframe": "1h"},
        "strategy": {
            "type": "breakout",
            "entry_lookback": 3,
            "exit_lookback": 3,
            "stop_loss_pct": 0.05,
        },
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.05},
    }
    payload.update(overrides)
    return payload


def _trending_closes(n: int) -> list[float]:
    return [100.0 + i * 3.0 for i in range(n)]


def test_breakout_runs_through_run_experiment_directly(tmp_path):
    csv_path = _write_csv(tmp_path, _trending_closes(20))
    spec = parse_experiment_spec(_breakout_base(csv_path))

    result = run_experiment(spec)

    assert result.spec.strategy.type == "breakout"
    assert result.summary.runs == 1


def test_breakout_runs_through_sweep_engine_unchanged(tmp_path):
    csv_path = _write_csv(tmp_path, _trending_closes(20))
    sweep = SweepSpec(
        hypothesis="breakout lookback sensitivity",
        base=_breakout_base(csv_path),
        grid={"strategy.entry_lookback": [2, 3], "strategy.exit_lookback": [2, 3]},
    )

    specs = generate_sweep_specs(sweep)

    assert len(specs) == 4
    assert all(s.strategy.type == "breakout" for s in specs)
    assert all(s.storage.store_trades is True for s in specs)
    for spec in specs:
        run_experiment(spec)  # must not raise — same execution path as any other strategy


def test_breakout_runs_through_sensitivity_analysis_unchanged(tmp_path):
    csv_path = _write_csv(tmp_path, _trending_closes(20))
    sweep = SweepSpec(
        hypothesis="breakout sensitivity",
        base=_breakout_base(csv_path),
        grid={"strategy.entry_lookback": [2, 3]},
    )

    result = run_sensitivity_analysis(sweep)

    assert len(result.points) == 2
    assert {p.params["strategy.entry_lookback"] for p in result.points} == {2, 3}


def test_breakout_runs_through_out_of_sample_unchanged(tmp_path):
    n = 10
    train_closes = _trending_closes(n)
    # Falling, then a sharp spike at the very end so the test window also
    # produces at least one breakout trade (zero-trade windows are a general
    # pipeline limitation, not something to special-case for this strategy).
    test_closes = list(reversed(_trending_closes(n)))
    test_closes[-1] += 50.0
    closes = train_closes + test_closes
    csv_path = _write_csv(tmp_path, closes)
    base = parse_experiment_spec(_breakout_base(csv_path))

    oos_spec = OutOfSampleSpec(
        base=base,
        train_start=_START,
        train_end=_START + timedelta(hours=n - 1),
        test_start=_START + timedelta(hours=n),
        test_end=_START + timedelta(hours=2 * n - 1),
    )

    result = run_out_of_sample(oos_spec)

    assert result.train.spec.strategy.type == "breakout"
    assert result.test.spec.strategy.type == "breakout"
