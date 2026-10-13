"""SQLAlchemy ORM models for the `experiments`/`runs`/`trades` tables.

`store_trades=False` is still the MVP/default behavior: `TradeRow` rows only
exist for experiments whose spec set `storage.store_trades=true` (Фаза 18a)
— the runner only populates `ExperimentResult.run_trades` in that case, and
the repository only writes `trades` rows when that field is not `None`.
Frequently-queried metrics are promoted to their own columns; full
round-trip fidelity for the rest comes from the JSONB columns (see
`vectorx.storage.postgres.serializers`).
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ExperimentBatchRow(Base):
    """A research hypothesis grouping many `ExperimentRow`s (Фаза 18c)."""

    __tablename__ = "experiment_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hypothesis: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExperimentRow(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    spec: Mapped[dict] = mapped_column(JSONB, nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    code_version: Mapped[str] = mapped_column(String, nullable=False)
    data_version: Mapped[str | None] = mapped_column(String, nullable=True)
    experiment_version: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("experiment_batches.id", ondelete="SET NULL"), nullable=True
    )
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    mean_total_return: Mapped[float] = mapped_column(Float, nullable=False)
    median_total_return: Mapped[float] = mapped_column(Float, nullable=False)
    stdev_total_return: Mapped[float] = mapped_column(Float, nullable=False)
    p_negative: Mapped[float] = mapped_column(Float, nullable=False)
    p_ruined: Mapped[float] = mapped_column(Float, nullable=False)

    runs: Mapped[list["RunRow"]] = relationship(
        back_populates="experiment",
        order_by="RunRow.run_index",
        cascade="all, delete-orphan",
    )


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    run_index: Mapped[int] = mapped_column(Integer, nullable=False)
    derived_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metrics_extra: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expectancy_theoretical: Mapped[float | None] = mapped_column(Float, nullable=True)
    expectancy_sample: Mapped[float] = mapped_column(Float, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    total_return: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=False)
    stdev: Mapped[float] = mapped_column(Float, nullable=False)
    ruined: Mapped[bool] = mapped_column(Boolean, nullable=False)
    equity_downsampled: Mapped[list] = mapped_column(JSONB, nullable=False)

    experiment: Mapped["ExperimentRow"] = relationship(back_populates="runs")
    trades: Mapped[list["TradeRow"]] = relationship(
        back_populates="run",
        order_by="TradeRow.trade_index",
        cascade="all, delete-orphan",
    )


class TradeRow(Base):
    """One raw trade (`store_trades=true` only, Фаза 18a) — never created by default."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    trade_index: Mapped[int] = mapped_column(Integer, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    r_multiple: Mapped[float] = mapped_column(Float, nullable=False)
    risk: Mapped[float] = mapped_column(Float, nullable=False)
    entry_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    size: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_money: Mapped[float | None] = mapped_column(Float, nullable=True)

    run: Mapped["RunRow"] = relationship(back_populates="trades")
