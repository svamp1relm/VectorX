"""generate_walk_forward_windows/run_walk_forward: N consecutive OOS windows
(Фаза 21). Walk-forward is a sequence of Out-of-Sample (Фаза 20) splits, not
a new comparison mechanism: each window is just `run_out_of_sample` applied
to the same `base` spec with a different train/test time range.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from vectorx.core.errors import InvalidModelParametersError
from vectorx.experiments.out_of_sample import (
    OutOfSampleResult,
    OutOfSampleSpec,
    run_out_of_sample,
)
from vectorx.experiments.spec import HistoricalBacktestExperimentSpec

_MIN_GAP = timedelta(microseconds=1)
"""The smallest possible step past `train_end` that still satisfies
`OutOfSampleSpec`'s "test_start must be strictly after train_end" rule,
without needing to know the data's candle interval at window-generation time.
"""


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    """One walk-forward step's train/test boundaries."""

    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime


def generate_walk_forward_windows(
    start: datetime,
    end: datetime,
    *,
    train_window: timedelta,
    test_window: timedelta,
    step: timedelta,
) -> tuple[WalkForwardWindow, ...]:
    """Slide a fixed train/test window pair forward by `step` across `[start, end]`."""
    if train_window <= timedelta(0):
        raise InvalidModelParametersError(f"train_window must be > 0, got {train_window}")
    if test_window <= timedelta(0):
        raise InvalidModelParametersError(f"test_window must be > 0, got {test_window}")
    if step <= timedelta(0):
        raise InvalidModelParametersError(f"step must be > 0, got {step}")

    windows: list[WalkForwardWindow] = []
    train_start = start
    while True:
        train_end = train_start + train_window
        test_start = train_end + _MIN_GAP
        test_end = test_start + test_window
        if test_end > end:
            break
        windows.append(
            WalkForwardWindow(
                train_start=train_start, train_end=train_end,
                test_start=test_start, test_end=test_end,
            )
        )
        train_start += step

    return tuple(windows)


def run_walk_forward(
    base: HistoricalBacktestExperimentSpec,
    windows: tuple[WalkForwardWindow, ...],
    *,
    reference_risk_fraction: float = 0.01,
) -> tuple[OutOfSampleResult, ...]:
    """Run `run_out_of_sample` once per window, all against the same `base` spec."""
    return tuple(
        run_out_of_sample(
            OutOfSampleSpec(
                base=base,
                train_start=window.train_start,
                train_end=window.train_end,
                test_start=window.test_start,
                test_end=window.test_end,
            ),
            reference_risk_fraction=reference_risk_fraction,
        )
        for window in windows
    )
