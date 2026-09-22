"""Integration tests against a real, ephemeral, local PostgreSQL instance
(see conftest.py). Round-trips a full `run_experiment` output through
`PostgresExperimentRepository` and asserts exact reconstruction.
"""

from vectorx.experiments.runner import run_experiment
from vectorx.experiments.spec import ExperimentSpec
from vectorx.storage.postgres.repository import PostgresExperimentRepository


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


def test_save_and_get_round_trips_exactly(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)
    original = run_experiment(_spec())

    experiment_id = repo.save_experiment(original)
    reloaded = repo.get_experiment(experiment_id)

    assert reloaded is not None
    assert reloaded.name == original.name
    assert reloaded.seed == original.seed
    assert reloaded.runs == original.runs
    assert reloaded.experiment_version == original.experiment_version
    assert reloaded.code_version == original.code_version
    assert reloaded.status == original.status
    assert reloaded.duration == original.duration
    assert reloaded.created_at == original.created_at
    assert reloaded.spec == original.spec
    assert reloaded.summary == original.summary
    assert reloaded.run_results == original.run_results


def test_get_experiment_returns_none_for_unknown_id(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)

    assert repo.get_experiment(999_999) is None


def test_list_experiment_ids_reflects_insertion_order(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)

    id_a = repo.save_experiment(run_experiment(_spec(name="a", seed=1)))
    id_b = repo.save_experiment(run_experiment(_spec(name="b", seed=2)))

    assert repo.list_experiment_ids() == (id_a, id_b)


def test_infinite_profit_factor_round_trips(clean_postgres_engine):
    # p_win=1.0 with no losses over a small run guarantees profit_factor=inf,
    # which JSON cannot represent — this is the case the metrics_extra split
    # (Ruling in Phase 8) exists to handle.
    repo = PostgresExperimentRepository(clean_postgres_engine)
    spec = _spec(runs=1, model={"p_win": 1.0, "win_r": 2.0, "loss_r": -1.0, "n_trades": 10})
    original = run_experiment(spec)
    assert original.run_results[0].metrics.profit_factor == float("inf")

    experiment_id = repo.save_experiment(original)
    reloaded = repo.get_experiment(experiment_id)

    assert reloaded.run_results[0].metrics.profit_factor == float("inf")


def test_no_trades_table_exists(clean_postgres_engine):
    with clean_postgres_engine.connect() as conn:
        result = conn.exec_driver_sql(
            "SELECT to_regclass('public.trades')"
        ).scalar()
    assert result is None
