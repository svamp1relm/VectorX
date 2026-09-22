"""ExperimentSpec: YAML v1 structural validation. Domain ranges validated
elsewhere (math/simulation), not duplicated here.
"""

import pytest
from pydantic import ValidationError

from vectorx.experiments.spec import ExperimentSpec, load_experiment_spec

VALID_YAML = """
name: baseline_expectancy
seed: 42
runs: 100

model:
  p_win: 0.55
  win_r: 2.0
  loss_r: -1.0
  n_trades: 1000

portfolio:
  initial_capital: 10000
  risk_per_trade: 0.01
"""


def test_loads_valid_yaml_with_defaults_applied(tmp_path):
    path = tmp_path / "expectancy_test.yaml"
    path.write_text(VALID_YAML)

    spec = load_experiment_spec(path)

    assert spec.name == "baseline_expectancy"
    assert spec.seed == 42
    assert spec.runs == 100
    assert spec.model.p_win == 0.55
    assert spec.model.win_r == 2.0
    assert spec.model.loss_r == -1.0
    assert spec.model.n_trades == 1000
    assert spec.portfolio.initial_capital == 10000
    assert spec.portfolio.risk_per_trade == 0.01
    assert spec.portfolio.commission == 0.0
    assert spec.portfolio.slippage == 0.0
    assert spec.storage.store_trades is False


def test_explicit_commission_slippage_and_store_trades_are_respected(tmp_path):
    path = tmp_path / "spec.yaml"
    path.write_text(
        VALID_YAML
        + """
portfolio:
  initial_capital: 10000
  risk_per_trade: 0.01
  commission: 0.01
  slippage: 0.02

storage:
  store_trades: true
"""
    )

    spec = load_experiment_spec(path)

    assert spec.portfolio.commission == 0.01
    assert spec.portfolio.slippage == 0.02
    assert spec.storage.store_trades is True


def test_rejects_unknown_top_level_field():
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate(
            {
                "name": "x",
                "seed": 1,
                "runs": 1,
                "model": {"p_win": 0.5, "win_r": 2.0, "loss_r": -1.0, "n_trades": 10},
                "portfolio": {"initial_capital": 10000, "risk_per_trade": 0.01},
                "unexpected_field": True,
            }
        )


def test_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate(
            {
                "name": "x",
                "seed": 1,
                "model": {"p_win": 0.5, "win_r": 2.0, "loss_r": -1.0, "n_trades": 10},
                "portfolio": {"initial_capital": 10000, "risk_per_trade": 0.01},
            }
        )


def test_spec_is_immutable():
    spec = ExperimentSpec.model_validate(
        {
            "name": "x",
            "seed": 1,
            "runs": 1,
            "model": {"p_win": 0.5, "win_r": 2.0, "loss_r": -1.0, "n_trades": 10},
            "portfolio": {"initial_capital": 10000, "risk_per_trade": 0.01},
        }
    )

    with pytest.raises(ValidationError):
        spec.seed = 2
