"""run_out_of_sample: one explicit train/test time-split validation (Фаза 20).

Two `run_experiment()` calls (train slice, test slice of the *same* CSV) plus
one `compare_train_test_expectancy` call — no second simulation/statistics
pipeline. A synthetic price path with a sharp, known trend reversal between
the train and test windows is used so the comparison's direction is
unambiguous to assert on.
"""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from vectorx.experiments.out_of_sample import OutOfSampleSpec, run_out_of_sample
from vectorx.experiments.spec import parse_experiment_spec

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _write_csv(tmp_path, closes: list[float]):
    path = tmp_path / "candles.csv"
    lines = ["timestamp,open,high,low,close,volume"]
    for i, close in enumerate(closes):
        ts = (_START + timedelta(hours=i)).isoformat()
        lines.append(f"{ts},{close},{close},{close},{close},1000.0")
    path.write_text("\n".join(lines) + "\n")
    return path


def _base_spec(csv_path, **overrides):
    payload = {
        "type": "historical_backtest",
        "name": "oos_test",
        "data": {"path": str(csv_path), "symbol": "BTCUSDT", "timeframe": "1h"},
        "strategy": {"type": "buy_and_hold", "stop_loss_pct": 1.0},
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.1},
    }
    payload.update(overrides)
    return parse_experiment_spec(payload)


def _rising_then_falling_closes(n: int) -> list[float]:
    rising = [100.0 + i * 5.0 for i in range(n)]
    falling = [rising[-1] - i * 5.0 for i in range(1, n + 1)]
    return rising + falling


def _oos_spec(csv_path, n: int) -> OutOfSampleSpec:
    base = _base_spec(csv_path)
    train_start = _START
    train_end = _START + timedelta(hours=n - 1)
    test_start = _START + timedelta(hours=n)
    test_end = _START + timedelta(hours=2 * n - 1)
    return OutOfSampleSpec(
        base=base, train_start=train_start, train_end=train_end,
        test_start=test_start, test_end=test_end,
    )


def test_detects_a_known_trend_reversal_between_train_and_test(tmp_path):
    n = 20
    closes = _rising_then_falling_closes(n)
    csv_path = _write_csv(tmp_path, closes)
    spec = _oos_spec(csv_path, n)

    result = run_out_of_sample(spec)

    assert result.train.run_results[0].metrics.trades == 1
    assert result.test.run_results[0].metrics.trades == 1
    assert result.train.run_results[0].metrics.expectancy_sample > 0.0
    assert result.test.run_results[0].metrics.expectancy_sample < 0.0
    assert result.comparison.risk_compatibility.compatible is True
    assert result.comparison.delta_train_test is not None
    assert result.comparison.delta_train_test > 0.0


def test_is_deterministic(tmp_path):
    n = 20
    closes = _rising_then_falling_closes(n)
    csv_path = _write_csv(tmp_path, closes)
    spec = _oos_spec(csv_path, n)

    result_a = run_out_of_sample(spec)
    result_b = run_out_of_sample(spec)

    assert result_a.train.run_results == result_b.train.run_results
    assert result_a.test.run_results == result_b.test.run_results
    assert result_a.comparison == result_b.comparison


def test_rejects_train_start_after_train_end(tmp_path):
    csv_path = _write_csv(tmp_path, [100.0] * 10)
    base = _base_spec(csv_path)

    with pytest.raises(ValidationError):
        OutOfSampleSpec(
            base=base,
            train_start=_START + timedelta(hours=5),
            train_end=_START,
            test_start=_START + timedelta(hours=6),
            test_end=_START + timedelta(hours=9),
        )


def test_rejects_overlapping_train_and_test_windows(tmp_path):
    csv_path = _write_csv(tmp_path, [100.0] * 10)
    base = _base_spec(csv_path)

    with pytest.raises(ValidationError):
        OutOfSampleSpec(
            base=base,
            train_start=_START,
            train_end=_START + timedelta(hours=5),
            test_start=_START + timedelta(hours=5),
            test_end=_START + timedelta(hours=9),
        )
