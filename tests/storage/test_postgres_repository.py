"""Integration tests against a real, ephemeral, local PostgreSQL instance
(see conftest.py). Round-trips a full `run_experiment` output through
`PostgresExperimentRepository` and asserts exact reconstruction.
"""

from datetime import UTC, datetime, timedelta

from vectorx.experiments.runner import run_experiment
from vectorx.experiments.spec import ExperimentSpec, parse_experiment_spec
from vectorx.storage.postgres.repository import PostgresExperimentRepository

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _spec(**overrides) -> ExperimentSpec:
    payload = {
        "name": "expectancy_test",
        "seed": 42,
        "runs": 5,
        "model": {"p_win": 0.55, "win_r": 2.0, "loss_r": -1.0, "n_trades": 20},
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
    }
    payload.update(overrides)
    return parse_experiment_spec(payload)


def _write_csv(tmp_path, closes: list[float]):
    path = tmp_path / "candles.csv"
    lines = ["timestamp,open,high,low,close,volume"]
    for i, close in enumerate(closes):
        ts = (_START + timedelta(hours=i)).isoformat()
        lines.append(f"{ts},{close},{close},{close},{close},1000.0")
    path.write_text("\n".join(lines) + "\n")
    return path


def _historical_spec(csv_path, **overrides) -> ExperimentSpec:
    payload = {
        "type": "historical_backtest",
        "name": "ma_crossover_test",
        "data": {"path": str(csv_path), "symbol": "BTCUSDT", "timeframe": "1h"},
        "strategy": {"fast_period": 2, "slow_period": 4, "stop_loss_pct": 0.01},
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
    }
    payload.update(overrides)
    return parse_experiment_spec(payload)


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


def test_store_trades_false_creates_no_trade_rows(clean_postgres_engine):
    # store_trades=false (default) must still create zero rows in `trades` —
    # regression on the invariant from before the `trades` table existed.
    repo = PostgresExperimentRepository(clean_postgres_engine)
    original = run_experiment(_spec())
    assert original.run_trades is None

    repo.save_experiment(original)

    with clean_postgres_engine.connect() as conn:
        count = conn.exec_driver_sql("SELECT count(*) FROM trades").scalar()
    assert count == 0


def test_store_trades_true_round_trips_raw_trades_bitwise(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)
    spec = _spec(runs=2, storage={"store_trades": True})
    original = run_experiment(spec)
    assert original.run_trades is not None

    experiment_id = repo.save_experiment(original)
    reloaded = repo.get_experiment(experiment_id)

    assert reloaded is not None
    assert reloaded.run_trades == original.run_trades

    with clean_postgres_engine.connect() as conn:
        count = conn.exec_driver_sql("SELECT count(*) FROM trades").scalar()
    assert count == sum(len(run_trades) for run_trades in original.run_trades)


def test_monte_carlo_data_version_round_trips_as_none(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)
    original = run_experiment(_spec())
    assert original.data_version is None

    experiment_id = repo.save_experiment(original)
    reloaded = repo.get_experiment(experiment_id)

    assert reloaded.data_version is None


def test_historical_backtest_data_version_round_trips(clean_postgres_engine, tmp_path):
    repo = PostgresExperimentRepository(clean_postgres_engine)
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    csv_path = _write_csv(tmp_path, closes)
    original = run_experiment(_historical_spec(csv_path))
    assert original.data_version is not None

    experiment_id = repo.save_experiment(original)
    reloaded = repo.get_experiment(experiment_id)

    assert reloaded.data_version == original.data_version


def test_get_batch_id_for_experiment_returns_batch_id_when_in_a_batch(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)
    batch_id = repo.save_batch(hypothesis="h", notes=None)
    experiment_id = repo.save_experiment(run_experiment(_spec()), batch_id=batch_id)

    assert repo.get_batch_id_for_experiment(experiment_id) == batch_id


def test_get_batch_id_for_experiment_returns_none_when_not_in_a_batch(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)
    experiment_id = repo.save_experiment(run_experiment(_spec()))

    assert repo.get_batch_id_for_experiment(experiment_id) is None


def test_historical_backtest_round_trips_with_null_expectancy_theoretical(
    clean_postgres_engine, tmp_path
):
    repo = PostgresExperimentRepository(clean_postgres_engine)
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    csv_path = _write_csv(tmp_path, closes)
    original = run_experiment(_historical_spec(csv_path))
    assert original.run_results[0].metrics.expectancy_theoretical is None

    experiment_id = repo.save_experiment(original)
    reloaded = repo.get_experiment(experiment_id)

    assert reloaded is not None
    assert reloaded.spec == original.spec
    assert reloaded.run_results[0].metrics.expectancy_theoretical is None
    assert reloaded.run_results == original.run_results


def test_save_batch_and_get_batch_round_trips(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)

    batch_id = repo.save_batch(hypothesis="fast period matters", notes="first sweep")
    batch = repo.get_batch(batch_id)

    assert batch is not None
    assert batch.id == batch_id
    assert batch.hypothesis == "fast period matters"
    assert batch.notes == "first sweep"
    assert batch.experiment_ids == ()


def test_get_batch_returns_none_for_unknown_id(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)

    assert repo.get_batch(999_999) is None


def test_save_experiment_with_batch_id_appears_in_batch_experiment_ids(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)
    batch_id = repo.save_batch(hypothesis="h", notes=None)

    id_a = repo.save_experiment(run_experiment(_spec(name="a", seed=1)), batch_id=batch_id)
    id_b = repo.save_experiment(run_experiment(_spec(name="b", seed=2)), batch_id=batch_id)
    repo.save_experiment(run_experiment(_spec(name="not_in_batch", seed=3)))

    batch = repo.get_batch(batch_id)

    assert batch.experiment_ids == (id_a, id_b)


def test_list_batch_ids_reflects_insertion_order(clean_postgres_engine):
    repo = PostgresExperimentRepository(clean_postgres_engine)

    id_a = repo.save_batch(hypothesis="a", notes=None)
    id_b = repo.save_batch(hypothesis="b", notes=None)

    assert repo.list_batch_ids() == (id_a, id_b)
