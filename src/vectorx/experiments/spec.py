"""ExperimentSpec: polymorphic YAML schema for Monte Carlo and historical
backtest experiments.

Structural validation only (types, required fields, unknown-key rejection)
lives here via pydantic. Domain-range validation (p_win in [0,1], win_r>0,
risk_per_trade in (0,1], ...) is intentionally NOT duplicated here — it is
owned exclusively by `vectorx.math`/`vectorx.simulation`, which already run
it the moment a spec is actually simulated. Two YAML section names use
short external names (`commission`/`slippage`) that differ from the
internal `simulate_portfolio` parameter names (`commission_r`/`slippage_r`);
the runner is the adapter between the two.

`ExperimentSpec` is a discriminated union on `type`, not a class: existing
YAML v1 files have no `type` field at all, so `parse_experiment_spec`
defaults a missing `type` to `"monte_carlo"` before dispatching — every
pre-Фаза-16a YAML/JSON payload keeps parsing to the exact same
`MonteCarloExperimentSpec` it always did, byte for byte. `EXPERIMENT_VERSION`
stays at 1: adding `type` with a back-compat default is additive, not a
breaking schema change (see `vectorx.experiments.versioning`).
"""

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter, model_validator


class ExperimentModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    p_win: float
    win_r: float
    loss_r: float
    n_trades: int
    risk_unit_fraction: float = Field(default=0.01, gt=0.0, le=1.0)


class ExperimentPortfolioSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    initial_capital: float
    risk_per_trade: float
    commission: float = 0.0
    slippage: float = 0.0


class ExperimentStorageSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    store_trades: bool = False


class MonteCarloExperimentSpec(BaseModel):
    """YAML v1 shape, unchanged since the MVP plan; `type` defaults for back-compat."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["monte_carlo"] = "monte_carlo"
    name: str
    seed: int
    runs: int
    model: ExperimentModelSpec
    portfolio: ExperimentPortfolioSpec
    storage: ExperimentStorageSpec = ExperimentStorageSpec()


class HistoricalDataSpec(BaseModel):
    """Only a CSV `DataSource` exists so far (Фаза 12); `source` is fixed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: Literal["csv"] = "csv"
    path: str
    symbol: str
    timeframe: str


class MovingAverageCrossoverStrategySpec(BaseModel):
    """The first strategy (Фаза 14); `type` defaults for back-compat with
    pre-Фаза-19 historical specs that predate benchmark strategies."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["moving_average_crossover"] = "moving_average_crossover"
    fast_period: int = Field(gt=0)
    slow_period: int = Field(gt=0)
    stop_loss_pct: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_period_ordering(self) -> "MovingAverageCrossoverStrategySpec":
        if self.fast_period >= self.slow_period:
            raise ValueError(
                f"fast_period ({self.fast_period}) must be < slow_period ({self.slow_period})"
            )
        return self


class BuyAndHoldStrategySpec(BaseModel):
    """`BuyAndHoldStrategy` benchmark (Фаза 19)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["buy_and_hold"]
    stop_loss_pct: float = Field(gt=0.0, le=1.0)


class RandomEntryStrategySpec(BaseModel):
    """`RandomEntryStrategy` benchmark (Фаза 19); seeded off the experiment's own `seed`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["random_entry"]
    stop_loss_pct: float = Field(gt=0.0, le=1.0)
    entry_probability: float = Field(default=0.1, gt=0.0, le=1.0)
    exit_probability: float = Field(default=0.1, gt=0.0, le=1.0)


class BreakoutStrategySpec(BaseModel):
    """`BreakoutStrategy` (Фаза 22) — the pipeline-generalization litmus test strategy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["breakout"]
    entry_lookback: int = Field(gt=0)
    exit_lookback: int = Field(gt=0)
    stop_loss_pct: float = Field(gt=0.0, le=1.0)


def _default_strategy_type(raw: object) -> object:
    """A missing `type` key means a pre-Фаза-19 moving-average-crossover spec."""
    if isinstance(raw, dict) and "type" not in raw:
        return {**raw, "type": "moving_average_crossover"}
    return raw


HistoricalStrategySpec = Annotated[
    MovingAverageCrossoverStrategySpec
    | BuyAndHoldStrategySpec
    | RandomEntryStrategySpec
    | BreakoutStrategySpec,
    Field(discriminator="type"),
    BeforeValidator(_default_strategy_type),
]
"""Discriminated union on `type`; every consumer type-hints against this, not a class."""


class HistoricalBacktestExperimentSpec(BaseModel):
    """A historical backtest is always one deterministic pass: `runs` is fixed at 1."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["historical_backtest"]
    name: str
    seed: int = 0
    runs: Literal[1] = 1
    data: HistoricalDataSpec
    strategy: HistoricalStrategySpec
    portfolio: ExperimentPortfolioSpec
    storage: ExperimentStorageSpec = ExperimentStorageSpec()


def _default_experiment_type(raw: object) -> object:
    """A missing `type` key means a pre-Фаза-16a Monte Carlo YAML v1 spec."""
    if isinstance(raw, dict) and "type" not in raw:
        return {**raw, "type": "monte_carlo"}
    return raw


ExperimentSpec = Annotated[
    MonteCarloExperimentSpec | HistoricalBacktestExperimentSpec,
    Field(discriminator="type"),
    BeforeValidator(_default_experiment_type),
]
"""The type every consumer (runner, storage, API) type-hints against.

Not a class — a discriminated Union annotation. Validate raw dicts with
`parse_experiment_spec`, not `ExperimentSpec.model_validate` (Union types have
no such classmethod).
"""

_experiment_spec_adapter: TypeAdapter = TypeAdapter(ExperimentSpec)


def parse_experiment_spec(
    raw: dict,
) -> MonteCarloExperimentSpec | HistoricalBacktestExperimentSpec:
    """Validate a raw dict (from YAML or a JSON request body) into the right subtype."""
    return _experiment_spec_adapter.validate_python(raw)


def load_experiment_spec(
    path: str | Path,
) -> MonteCarloExperimentSpec | HistoricalBacktestExperimentSpec:
    """Load and structurally validate an experiment spec from a YAML file."""
    raw = yaml.safe_load(Path(path).read_text())
    return parse_experiment_spec(raw)

