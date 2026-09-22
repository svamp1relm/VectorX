"""PostgresExperimentRepository: the concrete `ExperimentRepository` backend.

Sits behind the `[postgres]` extra; the rest of the library never imports
this module. Serialization details (JSONB shapes, the profit_factor/JSON
Infinity issue) live in `vectorx.storage.postgres.serializers`.
"""

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from vectorx.core.types import RunResult
from vectorx.experiments.runner import ExperimentResult
from vectorx.experiments.spec import ExperimentSpec
from vectorx.storage.postgres.models import ExperimentRow, RunRow
from vectorx.storage.postgres.serializers import (
    equity_curve_from_json,
    equity_curve_to_json,
    metrics_extra_from_json,
    metrics_extra_to_json,
    summary_from_json,
    summary_to_json,
)


def _params_from_spec(spec: ExperimentSpec) -> dict:
    return {**spec.model.model_dump(mode="json"), **spec.portfolio.model_dump(mode="json")}


class PostgresExperimentRepository:
    """`ExperimentRepository` backed by a SQLAlchemy `Engine`."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_experiment(self, result: ExperimentResult) -> int:
        params = _params_from_spec(result.spec)
        experiment_row = ExperimentRow(
            name=result.name,
            created_at=result.created_at,
            spec=result.spec.model_dump(mode="json"),
            seed=result.seed,
            status=result.status,
            duration=result.duration,
            code_version=result.code_version,
            experiment_version=result.experiment_version,
            summary=summary_to_json(result.summary),
            mean_total_return=result.summary.mean_total_return,
            median_total_return=result.summary.median_total_return,
            stdev_total_return=result.summary.stdev_total_return,
            p_negative=result.summary.p_negative,
            p_ruined=result.summary.p_ruined,
        )
        for run_result in result.run_results:
            metrics = run_result.metrics
            experiment_row.runs.append(
                RunRow(
                    run_index=run_result.run_index,
                    derived_seed=run_result.derived_seed,
                    params=params,
                    metrics_extra=metrics_extra_to_json(metrics),
                    expectancy_theoretical=metrics.expectancy_theoretical,
                    expectancy_sample=metrics.expectancy_sample,
                    win_rate=metrics.win_rate,
                    total_return=metrics.total_return,
                    max_drawdown=metrics.max_drawdown,
                    profit_factor=metrics.profit_factor,
                    stdev=metrics.stdev,
                    ruined=metrics.ruined,
                    equity_downsampled=equity_curve_to_json(run_result.equity_curve),
                )
            )

        with Session(self._engine) as session:
            session.add(experiment_row)
            session.commit()
            return experiment_row.id

    def get_experiment(self, experiment_id: int) -> ExperimentResult | None:
        with Session(self._engine) as session:
            row = session.get(ExperimentRow, experiment_id)
            if row is None:
                return None

            run_results = tuple(
                RunResult(
                    run_index=run_row.run_index,
                    derived_seed=run_row.derived_seed,
                    metrics=metrics_extra_from_json(
                        run_row.metrics_extra,
                        expectancy_theoretical=run_row.expectancy_theoretical,
                        expectancy_sample=run_row.expectancy_sample,
                        win_rate=run_row.win_rate,
                        total_return=run_row.total_return,
                        max_drawdown=run_row.max_drawdown,
                        profit_factor=run_row.profit_factor,
                        stdev=run_row.stdev,
                        ruined=run_row.ruined,
                    ),
                    equity_curve=equity_curve_from_json(run_row.equity_downsampled),
                )
                for run_row in sorted(row.runs, key=lambda r: r.run_index)
            )

            return ExperimentResult(
                name=row.name,
                seed=row.seed,
                runs=len(run_results),
                experiment_version=row.experiment_version,
                code_version=row.code_version,
                created_at=row.created_at,
                duration=row.duration,
                status=row.status,
                spec=ExperimentSpec.model_validate(row.spec),
                run_results=run_results,
                summary=summary_from_json(row.summary),
            )

    def list_experiment_ids(self) -> tuple[int, ...]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(ExperimentRow.id).order_by(ExperimentRow.id)
            ).scalars()
            return tuple(rows)
