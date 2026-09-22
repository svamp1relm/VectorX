"""CLI (`vectorx run <config.yaml>`). MVP CLI always requires PostgreSQL —
there is no in-memory/dry-run mode.
"""

import sys

import pytest

from vectorx.cli import main
from vectorx.storage.postgres.repository import PostgresExperimentRepository

VALID_YAML = """
name: expectancy_test
seed: 42
runs: 5

model:
  p_win: 0.55
  win_r: 2.0
  loss_r: -1.0
  n_trades: 20

portfolio:
  initial_capital: 10000
  risk_per_trade: 0.01
"""


def _write_spec(tmp_path, text: str = VALID_YAML):
    path = tmp_path / "spec.yaml"
    path.write_text(text)
    return path


def test_run_requires_database_url(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("VECTORX_DATABASE_URL", raising=False)
    config_path = _write_spec(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        main(["run", str(config_path)])

    assert exc_info.value.code != 0
    assert "VECTORX_DATABASE_URL" in str(exc_info.value)


def test_missing_postgres_extra_gives_clear_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VECTORX_DATABASE_URL", "postgresql+psycopg://fake/fake")
    monkeypatch.setitem(sys.modules, "vectorx.storage.postgres.repository", None)
    config_path = _write_spec(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        main(["run", str(config_path)])

    assert exc_info.value.code == 1
    assert "postgres" in capsys.readouterr().err.lower()


def test_run_persists_experiment_and_prints_summary(
    clean_postgres_engine, tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("VECTORX_DATABASE_URL", str(clean_postgres_engine.url))
    config_path = _write_spec(tmp_path)

    exit_code = main(["run", str(config_path)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "experiment_id:" in out
    assert "name: expectancy_test" in out
    assert "runs: 5" in out

    experiment_id = int(out.splitlines()[0].split(":")[1].strip())
    repository = PostgresExperimentRepository(clean_postgres_engine)
    stored = repository.get_experiment(experiment_id)
    assert stored is not None
    assert stored.name == "expectancy_test"
    assert stored.runs == 5


def test_running_same_seed_twice_gives_same_metrics_in_db(
    clean_postgres_engine, tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("VECTORX_DATABASE_URL", str(clean_postgres_engine.url))
    config_path = _write_spec(tmp_path)
    repository = PostgresExperimentRepository(clean_postgres_engine)

    main(["run", str(config_path)])
    first_id = int(capsys.readouterr().out.splitlines()[0].split(":")[1].strip())

    main(["run", str(config_path)])
    second_id = int(capsys.readouterr().out.splitlines()[0].split(":")[1].strip())

    first = repository.get_experiment(first_id)
    second = repository.get_experiment(second_id)

    assert first.summary == second.summary
    assert [r.metrics for r in first.run_results] == [r.metrics for r in second.run_results]
