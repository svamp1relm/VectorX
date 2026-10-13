"""Fundamental data types shared by simulation, statistics, and storage.

These are plain immutable data containers with no computation logic.
Values are always instantiated by the layer that produces them: `simulation`
fills `Trade`/`EquityPoint`, `statistics` fills `Metrics`/`ExperimentSummary`.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True, slots=True)
class Trade:
    """One simulated trade outcome, expressed primarily in R-multiples.

    `trade_index` is the ordinal position of the trade within its run
    (0..n-1); it is never a timestamp. `entry_ts`/`exit_ts` hold real market
    timestamps and are always `None` for Monte Carlo trades, since Monte
    Carlo has no market calendar. A future historical backtest engine fills
    them with real timestamps. `pnl` mirrors that rule: it is the raw,
    price-based PnL a backtest engine would compute, and stays `None` for
    Monte Carlo. `size`/`pnl_money` are filled by the portfolio simulator
    once a trade is sized against real capital.
    """

    trade_index: int
    side: str
    r_multiple: float
    risk: float = 1.0
    id: int | None = None
    entry_ts: datetime | None = None
    exit_ts: datetime | None = None
    pnl: float | None = None
    size: float | None = None
    pnl_money: float | None = None


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """One point of a (possibly downsampled) equity curve."""

    index: int
    equity: float
    drawdown: float


@dataclass(frozen=True, slots=True)
class RiskDefinition:
    """How one source defines and expresses a unit of trading risk."""

    unit: Literal["R"]
    normalization_version: Literal["r-v1"]
    method: Literal["model_r", "entry_price_stop_loss_fraction"]
    risk_unit_fraction: float
    cost_basis: Literal["gross_r"]


@dataclass(frozen=True, slots=True)
class ExpectancyEstimate:
    """One expectancy estimate with its sample accounting and risk semantics."""

    value: float
    canonical_value: float | None
    source: Literal["theoretical_model", "monte_carlo_sample", "historical_backtest"]
    unit: Literal["R"]
    sample_size: int | None
    planned_sample_size: int | None
    risk_definition: RiskDefinition


@dataclass(frozen=True, slots=True)
class ExpectancyComparison:
    """The expectancy estimates associated with one experiment snapshot."""

    theoretical: ExpectancyEstimate | None = None
    sample: ExpectancyEstimate | None = None
    historical: ExpectancyEstimate | None = None


@dataclass(frozen=True, slots=True)
class RiskCompatibility:
    """Whether source risk definitions can be converted to one reference scale."""

    compatible: bool
    same_risk_definition: bool
    reference_risk_fraction: float
    mismatches: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ComparisonDeltas:
    """First-minus-second expectancy deltas on the common reference scale."""

    delta_theoretical_sample: float | None = None
    delta_theoretical_historical: float | None = None
    delta_sample_historical: float | None = None


@dataclass(frozen=True, slots=True)
class ExpectancyComparisonResult:
    """Derived cross-experiment comparison; never a second source of metrics."""

    estimates: ExpectancyComparison
    risk_compatibility: RiskCompatibility
    deltas: ComparisonDeltas
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OutOfSampleComparisonResult:
    """Train vs test expectancy comparison for one time-split (Фаза 20).

    Not `ExpectancyComparisonResult`: that type hardcodes "theoretical/sample"
    (Monte Carlo) vs "historical" roles, which doesn't fit two historical
    estimates from disjoint time windows of the same spec.
    """

    train: ExpectancyEstimate
    test: ExpectancyEstimate
    risk_compatibility: RiskCompatibility
    delta_train_test: float | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Metrics:
    """Per-run statistics computed from a run's trades and equity curve."""

    trades: int
    wins: int
    losses: int
    win_rate: float
    avg_win: float
    avg_loss: float
    expectancy_theoretical: float | None
    expectancy_sample: float
    total_return: float
    avg_trade: float
    variance: float
    stdev: float
    max_drawdown: float
    profit_factor: float
    ruined: bool


@dataclass(frozen=True, slots=True)
class RunResult:
    """Outcome of a single Monte Carlo run: metrics plus a downsampled curve."""

    run_index: int
    derived_seed: int
    metrics: Metrics
    equity_curve: tuple[EquityPoint, ...]


@dataclass(frozen=True, slots=True)
class HistogramBins:
    """Pre-computed histogram: bin edges and per-bin counts.

    Always produced by `vectorx.statistics`; consumers (API/UI) only render
    `edges`/`counts` and never recompute them.
    """

    edges: tuple[float, ...]
    counts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ExperimentSummary:
    """Cross-run aggregates for one experiment."""

    runs: int
    mean_total_return: float
    median_total_return: float
    stdev_total_return: float
    p_negative: float
    p_ruined: float
    total_return_histogram: HistogramBins
    r_multiple_histogram: HistogramBins
    expectancy: ExpectancyComparison | None = None
