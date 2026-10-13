"""OutOfSampleSpec/run_out_of_sample: one explicit train/test time-split
validation (Фаза 20).

Decomposes into building blocks that already exist: `slice_market_data`
(Фаза 18b) splits one CSV's `MarketData` into disjoint train/test windows;
each slice is written back to a temp CSV (`write_market_data_csv`) so the
*unchanged* `run_experiment()` historical-backtest path runs on it — no
second simulation pipeline is created for Out-of-Sample. The two resulting
`ExperimentSummary`s are compared via `compare_train_test_expectancy`
(the OOS analogue of Фаза 17's `compare_expectancy`).

The OOS result is derived, not persisted (same rule as Фаза 17's expectancy
comparison): re-running `run_out_of_sample` on the same `OutOfSampleSpec`
reproduces it deterministically, so there is nothing to store beyond the
spec itself. `train`/`test` `ExperimentResult.spec.data.path` point at
temp files that no longer exist once this function returns — they are
only valid as a historical record of what was run, not for `run_experiment`
re-execution.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import BaseModel, ConfigDict, model_validator

from vectorx.core.types import OutOfSampleComparisonResult
from vectorx.experiments.runner import ExperimentResult, run_experiment
from vectorx.experiments.spec import HistoricalBacktestExperimentSpec
from vectorx.marketdata.csv_source import CsvDataSource, write_market_data_csv
from vectorx.marketdata.slicing import slice_market_data
from vectorx.marketdata.validation import validate_market_data
from vectorx.statistics.expectancy_comparison import (
    build_expectancy_snapshot_from_run_metrics,
    compare_train_test_expectancy,
)


class OutOfSampleSpec(BaseModel):
    """A historical backtest spec plus the train/test time windows to split it into."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base: HistoricalBacktestExperimentSpec
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime

    @model_validator(mode="after")
    def _validate_ranges(self) -> "OutOfSampleSpec":
        if self.train_start > self.train_end:
            raise ValueError(
                f"train_start ({self.train_start}) must be <= train_end ({self.train_end})"
            )
        if self.test_start > self.test_end:
            raise ValueError(
                f"test_start ({self.test_start}) must be <= test_end ({self.test_end})"
            )
        if self.test_start <= self.train_end:
            raise ValueError(
                "test_start must be strictly after train_end — train/test windows must not "
                "overlap (slice_market_data's bounds are inclusive on both ends, Фаза 18b)"
            )
        return self


@dataclass(frozen=True, slots=True)
class OutOfSampleResult:
    """Both runs plus their derived comparison."""

    train: ExperimentResult
    test: ExperimentResult
    comparison: OutOfSampleComparisonResult


def run_out_of_sample(
    spec: OutOfSampleSpec, *, reference_risk_fraction: float = 0.01
) -> OutOfSampleResult:
    """Two `run_experiment()` calls (train/test slices of one dataset) + one comparison."""
    data_source = CsvDataSource(
        path=spec.base.data.path, symbol=spec.base.data.symbol, timeframe=spec.base.data.timeframe
    )
    market_data = data_source.load()
    validate_market_data(market_data)

    train_data = slice_market_data(market_data, spec.train_start, spec.train_end)
    test_data = slice_market_data(market_data, spec.test_start, spec.test_end)

    with TemporaryDirectory() as tmp_dir:
        train_path = Path(tmp_dir) / "train.csv"
        test_path = Path(tmp_dir) / "test.csv"
        write_market_data_csv(train_data, train_path)
        write_market_data_csv(test_data, test_path)

        train_spec = spec.base.model_copy(
            update={
                "name": f"{spec.base.name}_train",
                "data": spec.base.data.model_copy(update={"path": str(train_path)}),
            }
        )
        test_spec = spec.base.model_copy(
            update={
                "name": f"{spec.base.name}_test",
                "data": spec.base.data.model_copy(update={"path": str(test_path)}),
            }
        )

        train_result = run_experiment(train_spec)
        test_result = run_experiment(test_spec)

    train_snapshot = build_expectancy_snapshot_from_run_metrics(
        train_spec, tuple(run.metrics for run in train_result.run_results)
    )
    test_snapshot = build_expectancy_snapshot_from_run_metrics(
        test_spec, tuple(run.metrics for run in test_result.run_results)
    )
    comparison = compare_train_test_expectancy(
        train_snapshot.historical, test_snapshot.historical, reference_risk_fraction
    )

    return OutOfSampleResult(train=train_result, test=test_result, comparison=comparison)
