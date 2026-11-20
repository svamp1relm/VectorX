"""Migrate real v1 experiment rows to the current schema without losing readability."""

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from vectorx.experiments.runner import run_experiment
from vectorx.experiments.spec import parse_experiment_spec
from vectorx.storage.postgres.repository import PostgresExperimentRepository
from vectorx.storage.postgres.serializers import (
    equity_curve_to_json,
    metrics_extra_to_json,
    summary_to_json,
)


def test_v1_rows_remain_readable_after_net_metrics_migration(clean_postgres_engine):
    original = run_experiment(
        parse_experiment_spec(
            {
                "name": "legacy_v1",
                "seed": 42,
                "runs": 1,
                "model": {"p_win": 0.5, "win_r": 2.0, "loss_r": -1.0, "n_trades": 2},
                "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
                "storage": {"store_trades": True},
            }
        )
    )
    run = original.run_results[0]
    trade = original.run_trades[0][0]
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    command.downgrade(config, "d8f3b6c20a51")

    with clean_postgres_engine.begin() as connection:
        experiment_id = connection.execute(
            text(
                """
                INSERT INTO experiments (
                    name, created_at, spec, seed, status, duration, code_version,
                    data_version, experiment_version, summary, mean_total_return,
                    median_total_return, stdev_total_return, p_negative, p_ruined
                ) VALUES (
                    :name, :created_at, CAST(:spec AS JSONB), :seed, :status, :duration,
                    :code_version, :data_version, :experiment_version, CAST(:summary AS JSONB),
                    :mean, :median, :stdev, :p_negative, :p_ruined
                ) RETURNING id
                """
            ),
            {
                "name": original.name,
                "created_at": original.created_at,
                "spec": json.dumps(original.spec.model_dump(mode="json")),
                "seed": original.seed,
                "status": original.status,
                "duration": original.duration,
                "code_version": original.code_version,
                "data_version": None,
                "experiment_version": 1,
                "summary": json.dumps(summary_to_json(original.summary)),
                "mean": original.summary.mean_total_return,
                "median": original.summary.median_total_return,
                "stdev": original.summary.stdev_total_return,
                "p_negative": original.summary.p_negative,
                "p_ruined": original.summary.p_ruined,
            },
        ).scalar_one()
        run_id = connection.execute(
            text(
                """
                INSERT INTO runs (
                    experiment_id, run_index, derived_seed, params, metrics_extra,
                    expectancy_theoretical, expectancy_sample, win_rate, total_return,
                    max_drawdown, profit_factor, stdev, ruined, equity_downsampled
                ) VALUES (
                    :experiment_id, 0, :derived_seed, CAST(:params AS JSONB),
                    CAST(:metrics AS JSONB), :theoretical, :sample, :win_rate,
                    :total_return, :max_drawdown, :profit_factor, :stdev, :ruined,
                    CAST(:equity AS JSONB)
                ) RETURNING id
                """
            ),
            {
                "experiment_id": experiment_id,
                "derived_seed": run.derived_seed,
                "params": json.dumps({"legacy": True}),
                "metrics": json.dumps(metrics_extra_to_json(run.metrics)),
                "theoretical": run.metrics.expectancy_theoretical,
                "sample": run.metrics.expectancy_sample,
                "win_rate": run.metrics.win_rate,
                "total_return": run.metrics.total_return,
                "max_drawdown": run.metrics.max_drawdown,
                "profit_factor": run.metrics.profit_factor,
                "stdev": run.metrics.stdev,
                "ruined": run.metrics.ruined,
                "equity": json.dumps(equity_curve_to_json(run.equity_curve)),
            },
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO trades (
                    run_id, trade_index, side, r_multiple, risk, entry_ts,
                    exit_ts, pnl, size, pnl_money
                ) VALUES (:run_id, 0, 'long', :r, 1.0, NULL, NULL, NULL, :size, :money)
                """
            ),
            {
                "run_id": run_id,
                "r": trade.r_multiple,
                "size": trade.size,
                "money": trade.pnl_money,
            },
        )

    command.upgrade(config, "head")
    reloaded = PostgresExperimentRepository(clean_postgres_engine).get_experiment(experiment_id)

    assert reloaded is not None
    assert reloaded.experiment_version == 1
    assert reloaded.run_results[0].metrics.expectancy_sample == run.metrics.expectancy_sample
    assert reloaded.run_results[0].metrics.expectancy_sample_net is None
    assert reloaded.run_trades[0][0].net_r_multiple is None
    assert reloaded.run_trades[0][0].r_multiple == trade.r_multiple
