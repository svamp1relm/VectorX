"""PostgreSQL persistence with targeted reads and bounded trade inserts."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from vectorx.core.types import RunResult, Trade
from vectorx.experiments.batch import ExperimentBatch
from vectorx.experiments.runner import ExperimentResult
from vectorx.experiments.spec import (
    ExperimentSpec,
    HistoricalBacktestExperimentSpec,
    MonteCarloExperimentSpec,
    parse_experiment_spec,
)
from vectorx.storage.postgres.models import ExperimentBatchRow, ExperimentRow, RunRow, TradeRow
from vectorx.storage.postgres.serializers import (
    equity_curve_from_json,
    equity_curve_to_json,
    metrics_extra_from_json,
    metrics_extra_to_json,
    summary_from_json,
    summary_to_json,
)

_TRADE_INSERT_CHUNK_SIZE = 5_000


def _params_from_spec(spec: ExperimentSpec) -> dict:
    if isinstance(spec, MonteCarloExperimentSpec):
        return {**spec.model.model_dump(mode="json"), **spec.portfolio.model_dump(mode="json")}
    assert isinstance(spec, HistoricalBacktestExperimentSpec)
    return {
        **spec.data.model_dump(mode="json"),
        **spec.strategy.model_dump(mode="json"),
        **spec.portfolio.model_dump(mode="json"),
    }


def _trade_to_row(trade: Trade, run_id: int) -> TradeRow:
    return TradeRow(
        run_id=run_id,
        trade_index=trade.trade_index,
        side=trade.side,
        r_multiple=trade.r_multiple,
        net_r_multiple=trade.net_r_multiple,
        risk=trade.risk,
        entry_ts=trade.entry_ts,
        exit_ts=trade.exit_ts,
        pnl=trade.pnl,
        size=trade.size,
        pnl_money=trade.pnl_money,
    )


def _trade_from_row(row: TradeRow) -> Trade:
    return Trade(
        trade_index=row.trade_index,
        side=row.side,
        r_multiple=row.r_multiple,
        net_r_multiple=row.net_r_multiple,
        risk=row.risk,
        entry_ts=row.entry_ts,
        exit_ts=row.exit_ts,
        pnl=row.pnl,
        size=row.size,
        pnl_money=row.pnl_money,
    )


def _experiment_to_row(result: ExperimentResult, batch_id: int | None) -> ExperimentRow:
    params = _params_from_spec(result.spec)
    row = ExperimentRow(
        name=result.name,
        created_at=result.created_at,
        spec=result.spec.model_dump(mode="json"),
        seed=result.seed,
        status=result.status,
        duration=result.duration,
        code_version=result.code_version,
        data_version=result.data_version,
        experiment_version=result.experiment_version,
        batch_id=batch_id,
        summary=summary_to_json(result.summary),
        mean_total_return=result.summary.mean_total_return,
        median_total_return=result.summary.median_total_return,
        stdev_total_return=result.summary.stdev_total_return,
        p_negative=result.summary.p_negative,
        p_ruined=result.summary.p_ruined,
    )
    for run_result in result.run_results:
        metrics = run_result.metrics
        row.runs.append(
            RunRow(
                run_index=run_result.run_index,
                derived_seed=run_result.derived_seed,
                params=params,
                metrics_extra=metrics_extra_to_json(metrics),
                expectancy_theoretical=metrics.expectancy_theoretical,
                expectancy_sample=metrics.expectancy_sample,
                expectancy_sample_net=metrics.expectancy_sample_net,
                win_rate=metrics.win_rate,
                win_rate_net=metrics.win_rate_net,
                total_return=metrics.total_return,
                max_drawdown=metrics.max_drawdown,
                profit_factor=metrics.profit_factor,
                profit_factor_net=metrics.profit_factor_net,
                stdev=metrics.stdev,
                ruined=metrics.ruined,
                equity_downsampled=equity_curve_to_json(run_result.equity_curve),
            )
        )
    return row


def _save_experiment_in_session(
    session: Session,
    result: ExperimentResult,
    batch_id: int | None = None,
) -> int:
    experiment_row = _experiment_to_row(result, batch_id)
    session.add(experiment_row)
    session.flush()

    run_trades = result.run_trades if result.run_trades is not None else (None,) * len(
        result.run_results
    )
    for run_row, trades in zip(experiment_row.runs, run_trades, strict=True):
        if trades is None:
            continue
        for offset in range(0, len(trades), _TRADE_INSERT_CHUNK_SIZE):
            chunk = [
                _trade_to_row(trade, run_row.id)
                for trade in trades[offset : offset + _TRADE_INSERT_CHUNK_SIZE]
            ]
            session.add_all(chunk)
            session.flush()
            for trade_row in chunk:
                session.expunge(trade_row)
    return experiment_row.id


def _result_from_row(
    row: ExperimentRow,
    *,
    include_runs: bool,
    include_trades: bool,
) -> ExperimentResult:
    sorted_runs = sorted(row.runs, key=lambda run: run.run_index) if include_runs else []
    run_results = tuple(
        RunResult(
            run_index=run_row.run_index,
            derived_seed=run_row.derived_seed,
            metrics=metrics_extra_from_json(
                run_row.metrics_extra,
                expectancy_theoretical=run_row.expectancy_theoretical,
                expectancy_sample=run_row.expectancy_sample,
                expectancy_sample_net=run_row.expectancy_sample_net,
                win_rate=run_row.win_rate,
                win_rate_net=run_row.win_rate_net,
                total_return=run_row.total_return,
                max_drawdown=run_row.max_drawdown,
                profit_factor=run_row.profit_factor,
                profit_factor_net=run_row.profit_factor_net,
                stdev=run_row.stdev,
                ruined=run_row.ruined,
            ),
            equity_curve=equity_curve_from_json(run_row.equity_downsampled),
        )
        for run_row in sorted_runs
    )
    run_trades = None
    if include_trades:
        run_trades = (
            tuple(
                tuple(_trade_from_row(trade_row) for trade_row in run_row.trades)
                for run_row in sorted_runs
            )
            if any(run_row.trades for run_row in sorted_runs)
            else None
        )

    return ExperimentResult(
        name=row.name,
        seed=row.seed,
        runs=len(run_results) if include_runs else row.summary["runs"],
        experiment_version=row.experiment_version,
        code_version=row.code_version,
        data_version=row.data_version,
        created_at=row.created_at,
        duration=row.duration,
        status=row.status,
        spec=parse_experiment_spec(row.spec),
        run_results=run_results,
        run_trades=run_trades,
        summary=summary_from_json(row.summary),
    )


class PostgresExperimentRepository:
    """`ExperimentRepository` backed by a SQLAlchemy `Engine`."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_experiment(self, result: ExperimentResult, batch_id: int | None = None) -> int:
        with Session(self._engine) as session:
            experiment_id = _save_experiment_in_session(session, result, batch_id)
            session.commit()
            return experiment_id

    def save_batch_with_experiments(
        self,
        hypothesis: str,
        notes: str | None,
        results: tuple[ExperimentResult, ...],
    ) -> int:
        with Session(self._engine) as session:
            batch_row = ExperimentBatchRow(
                hypothesis=hypothesis,
                notes=notes,
                created_at=datetime.now(UTC),
            )
            session.add(batch_row)
            session.flush()
            for result in results:
                _save_experiment_in_session(session, result, batch_row.id)
            session.commit()
            return batch_row.id

    def get_experiment(
        self,
        experiment_id: int,
        *,
        include_trades: bool = True,
    ) -> ExperimentResult | None:
        with Session(self._engine) as session:
            row = session.get(ExperimentRow, experiment_id)
            if row is None:
                return None
            return _result_from_row(row, include_runs=True, include_trades=include_trades)

    def get_experiment_summary(self, experiment_id: int) -> ExperimentResult | None:
        with Session(self._engine) as session:
            row = session.get(ExperimentRow, experiment_id)
            if row is None:
                return None
            return _result_from_row(row, include_runs=False, include_trades=False)

    def list_experiment_summaries(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[tuple[int, ExperimentResult], ...]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(ExperimentRow).order_by(ExperimentRow.id).offset(offset).limit(limit)
            ).scalars()
            return tuple(
                (row.id, _result_from_row(row, include_runs=False, include_trades=False))
                for row in rows
            )

    def list_experiment_ids(self) -> tuple[int, ...]:
        with Session(self._engine) as session:
            rows = session.execute(select(ExperimentRow.id).order_by(ExperimentRow.id)).scalars()
            return tuple(rows)

    def get_batch_id_for_experiment(self, experiment_id: int) -> int | None:
        with Session(self._engine) as session:
            row = session.get(ExperimentRow, experiment_id)
            return row.batch_id if row is not None else None

    def save_batch(self, hypothesis: str, notes: str | None = None) -> int:
        batch_row = ExperimentBatchRow(
            hypothesis=hypothesis, notes=notes, created_at=datetime.now(UTC)
        )
        with Session(self._engine) as session:
            session.add(batch_row)
            session.commit()
            return batch_row.id

    def get_batch(self, batch_id: int) -> ExperimentBatch | None:
        with Session(self._engine) as session:
            row = session.get(ExperimentBatchRow, batch_id)
            if row is None:
                return None

            experiment_ids = tuple(
                session.execute(
                    select(ExperimentRow.id)
                    .where(ExperimentRow.batch_id == batch_id)
                    .order_by(ExperimentRow.id)
                ).scalars()
            )
            return ExperimentBatch(
                id=row.id,
                hypothesis=row.hypothesis,
                notes=row.notes,
                created_at=row.created_at,
                experiment_ids=experiment_ids,
            )

    def list_batch_ids(self) -> tuple[int, ...]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(ExperimentBatchRow.id).order_by(ExperimentBatchRow.id)
            ).scalars()
            return tuple(rows)

    def list_batches(self) -> tuple[ExperimentBatch, ...]:
        with Session(self._engine) as session:
            batch_rows = tuple(
                session.execute(select(ExperimentBatchRow).order_by(ExperimentBatchRow.id))
                .scalars()
                .all()
            )
            experiment_links = session.execute(
                select(ExperimentRow.id, ExperimentRow.batch_id).order_by(ExperimentRow.id)
            ).all()
            ids_by_batch: dict[int, list[int]] = {}
            for experiment_id, batch_id in experiment_links:
                if batch_id is not None:
                    ids_by_batch.setdefault(batch_id, []).append(experiment_id)
            return tuple(
                ExperimentBatch(
                    id=row.id,
                    hypothesis=row.hypothesis,
                    notes=row.notes,
                    created_at=row.created_at,
                    experiment_ids=tuple(ids_by_batch.get(row.id, [])),
                )
                for row in batch_rows
            )
