"""ExperimentSpec: YAML v1 schema. One YAML = one model x N runs, no grid.

Structural validation only (types, required fields, unknown-key rejection)
lives here via pydantic. Domain-range validation (p_win in [0,1], win_r>0,
risk_per_trade in (0,1], ...) is intentionally NOT duplicated here — it is
owned exclusively by `vectorx.math`/`vectorx.simulation`, which already run
it the moment a spec is actually simulated. Two YAML section names use
short external names (`commission`/`slippage`) that differ from the
internal `simulate_portfolio` parameter names (`commission_r`/`slippage_r`);
the runner is the adapter between the two.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class ExperimentModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    p_win: float
    win_r: float
    loss_r: float
    n_trades: int


class ExperimentPortfolioSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    initial_capital: float
    risk_per_trade: float
    commission: float = 0.0
    slippage: float = 0.0


class ExperimentStorageSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    store_trades: bool = False


class ExperimentSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    seed: int
    runs: int
    model: ExperimentModelSpec
    portfolio: ExperimentPortfolioSpec
    storage: ExperimentStorageSpec = ExperimentStorageSpec()


def load_experiment_spec(path: str | Path) -> ExperimentSpec:
    """Load and structurally validate an experiment spec from a YAML file."""
    raw = yaml.safe_load(Path(path).read_text())
    return ExperimentSpec.model_validate(raw)

