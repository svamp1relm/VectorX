"""Pydantic request models shared by HTTP routers."""

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from vectorx.experiments.spec import HistoricalBacktestExperimentSpec


class ExpectancyComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    monte_carlo_experiment_id: int
    historical_experiment_id: int
    reference_risk_fraction: float = Field(default=0.01, gt=0.0, le=1.0)


class WalkForwardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    base: HistoricalBacktestExperimentSpec
    start: AwareDatetime
    end: AwareDatetime
    train_window_days: float = Field(gt=0.0)
    test_window_days: float = Field(gt=0.0)
    step_days: float = Field(gt=0.0)
    reference_risk_fraction: float = Field(default=0.01, gt=0.0, le=1.0)
