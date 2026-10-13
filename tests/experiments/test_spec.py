"""ExperimentSpec: YAML v1 structural validation. Domain ranges validated
elsewhere (math/simulation), not duplicated here.
"""

import pytest
from pydantic import ValidationError

from vectorx.experiments.spec import (
    HistoricalBacktestExperimentSpec,
    MonteCarloExperimentSpec,
    load_experiment_spec,
    parse_experiment_spec,
)

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

VALID_HISTORICAL_DICT = {
    "type": "historical_backtest",
    "name": "ma_crossover_btc_1h",
    "data": {"path": "data.csv", "symbol": "BTCUSDT", "timeframe": "1h"},
    "strategy": {"fast_period": 10, "slow_period": 30, "stop_loss_pct": 0.01},
    "portfolio": {"initial_capital": 10000, "risk_per_trade": 0.01},
}


def test_loads_valid_yaml_with_defaults_applied(tmp_path):
    path = tmp_path / "expectancy_test.yaml"
    path.write_text(VALID_YAML)

    spec = load_experiment_spec(path)

    assert isinstance(spec, MonteCarloExperimentSpec)
    assert spec.type == "monte_carlo"
    assert spec.name == "baseline_expectancy"
    assert spec.seed == 42
    assert spec.runs == 100
    assert spec.model.p_win == 0.55
    assert spec.model.win_r == 2.0
    assert spec.model.loss_r == -1.0
    assert spec.model.n_trades == 1000
    assert spec.model.risk_unit_fraction == 0.01
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
        parse_experiment_spec(
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
        parse_experiment_spec(
            {
                "name": "x",
                "seed": 1,
                "model": {"p_win": 0.5, "win_r": 2.0, "loss_r": -1.0, "n_trades": 10},
                "portfolio": {"initial_capital": 10000, "risk_per_trade": 0.01},
            }
        )


def test_spec_is_immutable():
    spec = parse_experiment_spec(
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


def test_missing_type_defaults_to_monte_carlo():
    # The exact back-compat guarantee: every pre-Фаза-16a YAML/JSON payload
    # (no `type` key at all) must still resolve to MonteCarloExperimentSpec.
    spec = parse_experiment_spec(
        {
            "name": "x",
            "seed": 1,
            "runs": 1,
            "model": {"p_win": 0.5, "win_r": 2.0, "loss_r": -1.0, "n_trades": 10},
            "portfolio": {"initial_capital": 10000, "risk_per_trade": 0.01},
        }
    )

    assert isinstance(spec, MonteCarloExperimentSpec)
    assert spec.type == "monte_carlo"


def test_explicit_monte_carlo_type_is_accepted():
    spec = parse_experiment_spec(
        {
            "type": "monte_carlo",
            "name": "x",
            "seed": 1,
            "runs": 1,
            "model": {"p_win": 0.5, "win_r": 2.0, "loss_r": -1.0, "n_trades": 10},
            "portfolio": {"initial_capital": 10000, "risk_per_trade": 0.01},
        }
    )

    assert isinstance(spec, MonteCarloExperimentSpec)


def test_monte_carlo_risk_unit_fraction_must_be_positive():
    with pytest.raises(ValidationError):
        parse_experiment_spec(
            {
                "type": "monte_carlo",
                "name": "x",
                "seed": 1,
                "runs": 1,
                "model": {
                    "p_win": 0.5,
                    "win_r": 2.0,
                    "loss_r": -1.0,
                    "n_trades": 10,
                    "risk_unit_fraction": 0.0,
                },
                "portfolio": {"initial_capital": 10000, "risk_per_trade": 0.01},
            }
        )


def test_parses_historical_backtest_spec():
    spec = parse_experiment_spec(VALID_HISTORICAL_DICT)

    assert isinstance(spec, HistoricalBacktestExperimentSpec)
    assert spec.type == "historical_backtest"
    assert spec.runs == 1
    assert spec.data.source == "csv"
    assert spec.data.path == "data.csv"
    assert spec.data.symbol == "BTCUSDT"
    assert spec.data.timeframe == "1h"
    assert spec.strategy.type == "moving_average_crossover"
    assert spec.strategy.fast_period == 10
    assert spec.strategy.slow_period == 30
    assert spec.strategy.stop_loss_pct == 0.01
    assert spec.portfolio.initial_capital == 10000


def test_historical_backtest_runs_cannot_be_overridden():
    with pytest.raises(ValidationError):
        parse_experiment_spec({**VALID_HISTORICAL_DICT, "runs": 5})


def test_historical_backtest_rejects_fast_period_not_less_than_slow_period():
    with pytest.raises(ValidationError):
        parse_experiment_spec(
            {
                **VALID_HISTORICAL_DICT,
                "strategy": {**VALID_HISTORICAL_DICT["strategy"], "fast_period": 30,
                             "slow_period": 10},
            }
        )


def test_historical_backtest_rejects_non_positive_periods():
    with pytest.raises(ValidationError):
        parse_experiment_spec(
            {
                **VALID_HISTORICAL_DICT,
                "strategy": {**VALID_HISTORICAL_DICT["strategy"], "fast_period": 0},
            }
        )


def test_historical_backtest_rejects_missing_data_section():
    payload = {k: v for k, v in VALID_HISTORICAL_DICT.items() if k != "data"}

    with pytest.raises(ValidationError):
        parse_experiment_spec(payload)


def test_unknown_experiment_type_is_rejected():
    with pytest.raises(ValidationError):
        parse_experiment_spec({**VALID_HISTORICAL_DICT, "type": "not_a_real_type"})


def test_parses_buy_and_hold_strategy_spec():
    spec = parse_experiment_spec(
        {
            **VALID_HISTORICAL_DICT,
            "strategy": {"type": "buy_and_hold", "stop_loss_pct": 0.05},
        }
    )

    assert spec.strategy.type == "buy_and_hold"
    assert spec.strategy.stop_loss_pct == 0.05


def test_parses_random_entry_strategy_spec_with_defaults():
    spec = parse_experiment_spec(
        {
            **VALID_HISTORICAL_DICT,
            "strategy": {"type": "random_entry", "stop_loss_pct": 0.05},
        }
    )

    assert spec.strategy.type == "random_entry"
    assert spec.strategy.stop_loss_pct == 0.05
    assert spec.strategy.entry_probability == 0.1
    assert spec.strategy.exit_probability == 0.1


def test_random_entry_strategy_spec_rejects_out_of_range_probabilities():
    with pytest.raises(ValidationError):
        parse_experiment_spec(
            {
                **VALID_HISTORICAL_DICT,
                "strategy": {
                    "type": "random_entry",
                    "stop_loss_pct": 0.05,
                    "entry_probability": 0.0,
                },
            }
        )


def test_missing_strategy_type_still_defaults_to_moving_average_crossover():
    spec = parse_experiment_spec(
        {
            **VALID_HISTORICAL_DICT,
            "strategy": {"fast_period": 10, "slow_period": 30, "stop_loss_pct": 0.01},
        }
    )

    assert spec.strategy.type == "moving_average_crossover"


def test_unknown_strategy_type_is_rejected():
    with pytest.raises(ValidationError):
        parse_experiment_spec(
            {**VALID_HISTORICAL_DICT, "strategy": {"type": "not_a_real_strategy"}}
        )


def test_parses_breakout_strategy_spec():
    spec = parse_experiment_spec(
        {
            **VALID_HISTORICAL_DICT,
            "strategy": {
                "type": "breakout",
                "entry_lookback": 20,
                "exit_lookback": 10,
                "stop_loss_pct": 0.03,
            },
        }
    )

    assert spec.strategy.type == "breakout"
    assert spec.strategy.entry_lookback == 20
    assert spec.strategy.exit_lookback == 10
    assert spec.strategy.stop_loss_pct == 0.03


def test_breakout_strategy_spec_rejects_non_positive_lookback():
    with pytest.raises(ValidationError):
        parse_experiment_spec(
            {
                **VALID_HISTORICAL_DICT,
                "strategy": {
                    "type": "breakout",
                    "entry_lookback": 0,
                    "exit_lookback": 10,
                    "stop_loss_pct": 0.03,
                },
            }
        )
