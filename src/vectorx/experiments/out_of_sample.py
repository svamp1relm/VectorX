"""Out-of-sample validation with in-memory slices and warm-up."""

from dataclasses import dataclass
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

from vectorx.core.types import OutOfSampleComparisonResult
from vectorx.experiments.runner import ExperimentResult, run_experiment
from vectorx.experiments.spec import HistoricalBacktestExperimentSpec
from vectorx.marketdata.csv_source import CsvDataSource, compute_market_data_content_version
from vectorx.marketdata.slicing import slice_market_data
from vectorx.marketdata.validation import validate_market_data
from vectorx.statistics.expectancy_comparison import (
    build_expectancy_snapshot_from_run_metrics,
    compare_train_test_expectancy,
)


class OutOfSampleSpec(BaseModel):
    """A historical backtest spec plus disjoint train/test time windows."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    base: HistoricalBacktestExperimentSpec
    train_start: AwareDatetime
    train_end: AwareDatetime
    test_start: AwareDatetime
    test_end: AwareDatetime

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
                "overlap (slice_market_data's bounds are inclusive on both ends)"
            )
        return self


@dataclass(frozen=True, slots=True)
class OutOfSampleResult:
    """Both scored runs, their comparison, and original-data provenance."""

    train: ExperimentResult
    test: ExperimentResult
    comparison: OutOfSampleComparisonResult
    source: OutOfSampleSpec
    source_data_version: str
    data_start: datetime


def run_out_of_sample(
    spec: OutOfSampleSpec, *, reference_risk_fraction: float = 0.01
) -> OutOfSampleResult:
    """Run train/test with pre-range indicators warm-up and compare expectancy."""
    data_source = CsvDataSource(
        path=spec.base.data.path, symbol=spec.base.data.symbol, timeframe=spec.base.data.timeframe
    )
    market_data, source_data_version = data_source.load_with_version()
    validate_market_data(market_data)

    slice_market_data(market_data, spec.train_start, spec.train_end)
    slice_market_data(market_data, spec.test_start, spec.test_end)
    train_data = slice_market_data(market_data, market_data.candles[0].timestamp, spec.train_end)
    test_data = slice_market_data(market_data, market_data.candles[0].timestamp, spec.test_end)

    ephemeral_storage = spec.base.storage.model_copy(update={"store_trades": False})
    train_spec = spec.base.model_copy(
        update={"name": f"{spec.base.name}_train", "storage": ephemeral_storage}
    )
    test_spec = spec.base.model_copy(
        update={"name": f"{spec.base.name}_test", "storage": ephemeral_storage}
    )
    train_result = run_experiment(
        train_spec,
        trade_start=spec.train_start,
        market_data=train_data,
        data_version=compute_market_data_content_version(train_data),
    )
    test_result = run_experiment(
        test_spec,
        trade_start=spec.test_start,
        market_data=test_data,
        data_version=compute_market_data_content_version(test_data),
    )

    train_snapshot = build_expectancy_snapshot_from_run_metrics(
        train_spec, tuple(run.metrics for run in train_result.run_results)
    )
    test_snapshot = build_expectancy_snapshot_from_run_metrics(
        test_spec, tuple(run.metrics for run in test_result.run_results)
    )
    comparison = compare_train_test_expectancy(
        train_snapshot.historical, test_snapshot.historical, reference_risk_fraction
    )

    return OutOfSampleResult(
        train=train_result,
        test=test_result,
        comparison=comparison,
        source=spec,
        source_data_version=source_data_version,
        data_start=market_data.candles[0].timestamp,
    )
