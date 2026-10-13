"""generate_walk_forward_windows/run_walk_forward: N consecutive OOS windows
(Фаза 21). Walk-forward reuses `run_out_of_sample` (Фаза 20) as its building
block — no second train/test comparison mechanism is created.
"""

from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from vectorx.core.errors import InvalidModelParametersError
from vectorx.experiments.spec import parse_experiment_spec
from vectorx.robustness.walk_forward import generate_walk_forward_windows, run_walk_forward

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _write_csv(tmp_path, closes: list[float]):
    path = tmp_path / "candles.csv"
    lines = ["timestamp,open,high,low,close,volume"]
    for i, close in enumerate(closes):
        ts = (_START + timedelta(hours=i)).isoformat()
        lines.append(f"{ts},{close},{close},{close},{close},1000.0")
    path.write_text("\n".join(lines) + "\n")
    return path


def test_generates_non_overlapping_windows_that_advance_by_step():
    windows = generate_walk_forward_windows(
        start=_START,
        end=_START + timedelta(hours=100),
        train_window=timedelta(hours=10),
        test_window=timedelta(hours=5),
        step=timedelta(hours=5),
    )

    assert len(windows) > 1
    for window in windows:
        assert window.train_start < window.train_end
        assert window.test_start > window.train_end
        assert window.test_start < window.test_end

    for earlier, later in pairwise(windows):
        assert later.train_start == earlier.train_start + timedelta(hours=5)


def test_stops_before_exceeding_end():
    windows = generate_walk_forward_windows(
        start=_START,
        end=_START + timedelta(hours=20),
        train_window=timedelta(hours=10),
        test_window=timedelta(hours=5),
        step=timedelta(hours=5),
    )

    for window in windows:
        assert window.test_end <= _START + timedelta(hours=20)


def test_rejects_non_positive_windows_or_step():
    with pytest.raises(InvalidModelParametersError):
        generate_walk_forward_windows(
            start=_START, end=_START + timedelta(hours=10),
            train_window=timedelta(0), test_window=timedelta(hours=1), step=timedelta(hours=1),
        )
    with pytest.raises(InvalidModelParametersError):
        generate_walk_forward_windows(
            start=_START, end=_START + timedelta(hours=10),
            train_window=timedelta(hours=1), test_window=timedelta(0), step=timedelta(hours=1),
        )
    with pytest.raises(InvalidModelParametersError):
        generate_walk_forward_windows(
            start=_START, end=_START + timedelta(hours=10),
            train_window=timedelta(hours=1), test_window=timedelta(hours=1), step=timedelta(0),
        )


def test_run_walk_forward_produces_one_oos_result_per_window(tmp_path):
    closes = [100.0 + i for i in range(60)]
    csv_path = _write_csv(tmp_path, closes)
    base = parse_experiment_spec(
        {
            "type": "historical_backtest",
            "name": "walk_forward_test",
            "data": {"path": str(csv_path), "symbol": "BTCUSDT", "timeframe": "1h"},
            "strategy": {"type": "buy_and_hold", "stop_loss_pct": 1.0},
            "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.1},
        }
    )
    windows = generate_walk_forward_windows(
        start=_START,
        end=_START + timedelta(hours=59),
        train_window=timedelta(hours=20),
        test_window=timedelta(hours=10),
        step=timedelta(hours=10),
    )

    results = run_walk_forward(base, windows)

    assert len(results) == len(windows)
    for result in results:
        assert result.train.run_results[0].metrics.trades == 1
        assert result.test.run_results[0].metrics.trades == 1
