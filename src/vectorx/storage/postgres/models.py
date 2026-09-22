"""SQLAlchemy ORM models for the `experiments`/`runs` tables.

`store_trades=False` is the MVP default and there is no `trades` table:
individual trades are never persisted, only per-run metrics and a
downsampled equity curve. Frequently-queried metrics are promoted to their
own columns; full round-trip fidelity for the rest comes from the JSONB
columns (see `vectorx.storage.postgres.serializers`).
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


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
    experiment_version: Mapped[int] = mapped_column(Integer, nullable=False)
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
    expectancy_theoretical: Mapped[float] = mapped_column(Float, nullable=False)
    expectancy_sample: Mapped[float] = mapped_column(Float, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    total_return: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=False)
    stdev: Mapped[float] = mapped_column(Float, nullable=False)
    ruined: Mapped[bool] = mapped_column(Boolean, nullable=False)
    equity_downsampled: Mapped[list] = mapped_column(JSONB, nullable=False)

    experiment: Mapped["ExperimentRow"] = relationship(back_populates="runs")
