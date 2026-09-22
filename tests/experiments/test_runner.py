"""ExperimentRunner: YAML spec -> N Monte Carlo runs -> RunResult[] + summary.

Uses an in-memory fake repository for now (Phase 8 adds Postgres behind
`ExperimentRepository`). Reproducibility is the core contract: same spec +
same seed must give identical per-run metrics and summary; a different seed
must not.
"""

import logging

import pytest

from vectorx.core.errors import ExperimentTooLargeError
from vectorx.core.rng import derived_seed_value
from vectorx.experiments.runner import MAX_OPERATIONS, run_experiment
from vectorx.experiments.spec import ExperimentSpec
from vectorx.experiments.versioning import EXPERIMENT_VERSION


def _spec(**overrides) -> ExperimentSpec:
    payload = {
        "name": "expectancy_test",
        "seed": 42,
        "runs": 5,
        "model": {"p_win": 0.55, "win_r": 2.0, "loss_r": -1.0, "n_trades": 20},
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
    }
    payload.update(overrides)
    return ExperimentSpec.model_validate(payload)


def test_same_seed_reproduces_identical_run_results_and_summary():
    spec = _spec()

    result_a = run_experiment(spec)
    result_b = run_experiment(spec)

    assert result_a.run_results == result_b.run_results
    assert result_a.summary == result_b.summary


def test_different_seed_diverges():
    result_a = run_experiment(_spec(seed=42))
    result_b = run_experiment(_spec(seed=43))

    assert result_a.run_results != result_b.run_results


def test_run_result_derived_seed_matches_core_rng_helper():
    spec = _spec(runs=3)

    result = run_experiment(spec)

    for run_result in result.run_results:
        expected = derived_seed_value(spec.seed, run_result.run_index)
        assert run_result.derived_seed == expected


def test_run_results_have_downsampled_equity_curve():
    spec = _spec(runs=1, model={"p_win": 0.55, "win_r": 2.0, "loss_r": -1.0, "n_trades": 600})

    result = run_experiment(spec)

    assert len(result.run_results[0].equity_curve) <= 500


def test_experiment_result_metadata():
    spec = _spec(runs=4)

    result = run_experiment(spec)

    assert result.name == spec.name
    assert result.seed == spec.seed
    assert result.runs == spec.runs
    assert result.experiment_version == EXPERIMENT_VERSION
    assert isinstance(result.code_version, str) and result.code_version
    assert result.status == "completed"
    assert result.duration >= 0.0
    assert len(result.run_results) == spec.runs
    assert result.spec == spec


def test_operations_limit_raises_before_running():
    spec = _spec(runs=3, model={"p_win": 0.5, "win_r": 2.0, "loss_r": -1.0, "n_trades": 1_000_000})
    assert spec.runs * spec.model.n_trades > MAX_OPERATIONS

    with pytest.raises(ExperimentTooLargeError):
        run_experiment(spec)


def test_logs_start_and_end_at_info_without_per_run_debug_spam(caplog):
    caplog.set_level(logging.DEBUG)

    run_experiment(_spec(runs=10))

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(info_records) == 2
    assert not any("derived_seed" in r.getMessage() for r in caplog.records)
