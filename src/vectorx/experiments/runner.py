"""ExperimentRunner: orchestrates one experiment end to end.

`ExperimentSpec` (YAML) -> N Monte Carlo runs (each with its own derived
seed) -> Portfolio -> Metrics -> `ExperimentSummary`. No YAML/Postgres/HTTP
concerns leak in beyond `spec` itself; storage (Phase 8) will persist
whatever this returns without needing to recompute anything.

`run_experiment` dispatches on `spec.type` (Фаза 16a): a `MonteCarloExperimentSpec`
runs the original Monte Carlo pipeline unchanged; a `HistoricalBacktestExperimentSpec`
loads real market data (Фаза 12), replays it through a `Strategy` (Фазы 13-14) via
`run_historical_backtest` (Фаза 15), and then funnels the resulting `Trade[]` through
the *same* `simulate_portfolio`/`compute_metrics`/`compute_experiment_summary` calls —
no second statistics pipeline exists for historical experiments.
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from vectorx.backtest.engine import run_historical_backtest
from vectorx.core.errors import ExperimentTooLargeError
from vectorx.core.rng import derived_rng, derived_seed_value
from vectorx.core.types import ExperimentSummary, Metrics, RunResult, Trade
from vectorx.experiments.spec import (
    BreakoutStrategySpec,
    BuyAndHoldStrategySpec,
    ExperimentSpec,
    HistoricalBacktestExperimentSpec,
    HistoricalStrategySpec,
    MonteCarloExperimentSpec,
    MovingAverageCrossoverStrategySpec,
    RandomEntryStrategySpec,
)
from vectorx.experiments.versioning import EXPERIMENT_VERSION, get_code_version
from vectorx.marketdata.csv_source import CsvDataSource, compute_data_version
from vectorx.marketdata.validation import validate_market_data
from vectorx.simulation.monte_carlo import generate_trades
from vectorx.simulation.portfolio import downsample_equity_curve, simulate_portfolio
from vectorx.statistics.expectancy_comparison import build_expectancy_snapshot
from vectorx.statistics.experiment_summary import compute_experiment_summary
from vectorx.statistics.metrics import compute_metrics
from vectorx.strategy.benchmarks import BuyAndHoldStrategy, RandomEntryStrategy
from vectorx.strategy.breakout import BreakoutStrategy
from vectorx.strategy.moving_average_crossover import MovingAverageCrossoverStrategy
from vectorx.strategy.protocol import Strategy

logger = logging.getLogger(__name__)

MAX_OPERATIONS = 2_000_000
"""Pre-flight limit on runs * n_trades for one Monte Carlo experiment (MVP safety guard)."""

MAX_HISTORICAL_CANDLES = 500_000
"""Limit on the number of candles a historical backtest experiment may load.

Monte Carlo's `runs * n_trades` guard has no equivalent for historical data:
there is exactly one deterministic pass, so the resource that needs bounding
is the size of the loaded `MarketData`, not a runs multiplier.
"""


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    """Everything one experiment execution produced, ready for storage."""

    name: str
    seed: int
    runs: int
    experiment_version: int
    code_version: str
    data_version: str | None
    created_at: datetime
    duration: float
    status: str
    spec: ExperimentSpec
    run_results: tuple[RunResult, ...]
    run_trades: tuple[tuple[Trade, ...], ...] | None
    summary: ExperimentSummary


def run_experiment(spec: ExperimentSpec) -> ExperimentResult:
    """Dispatch to the Monte Carlo or historical backtest runner by `spec.type`."""
    if isinstance(spec, MonteCarloExperimentSpec):
        return _run_monte_carlo_experiment(spec)
    return _run_historical_backtest_experiment(spec)


def _run_monte_carlo_experiment(spec: MonteCarloExperimentSpec) -> ExperimentResult:
    """Run `spec.runs` Monte Carlo runs and aggregate them into a summary."""
    n_operations = spec.runs * spec.model.n_trades
    if n_operations > MAX_OPERATIONS:
        raise ExperimentTooLargeError(
            f"runs*n_trades={n_operations} exceeds the MVP limit of {MAX_OPERATIONS}"
        )

    logger.info(
        "starting experiment name=%s seed=%s runs=%s", spec.name, spec.seed, spec.runs
    )
    created_at = datetime.now(UTC)
    started_at = time.perf_counter()

    run_results: list[RunResult] = []
    run_metrics: list[Metrics] = []
    all_r_multiples: list[float] = []
    run_trades: list[tuple[Trade, ...]] | None = [] if spec.storage.store_trades else None

    for run_index in range(spec.runs):
        rng = derived_rng(spec.seed, run_index)
        trades = generate_trades(
            p_win=spec.model.p_win,
            win_r=spec.model.win_r,
            loss_r=spec.model.loss_r,
            n_trades=spec.model.n_trades,
            rng=rng,
        )
        portfolio_result = simulate_portfolio(
            trades=trades,
            initial_capital=spec.portfolio.initial_capital,
            risk_per_trade=spec.portfolio.risk_per_trade,
            commission_r=spec.portfolio.commission,
            slippage_r=spec.portfolio.slippage,
        )
        metrics = compute_metrics(
            trades=portfolio_result.trades,
            equity_curve=portfolio_result.equity_curve,
            initial_capital=spec.portfolio.initial_capital,
            p_win=spec.model.p_win,
            win_r=spec.model.win_r,
            loss_r=spec.model.loss_r,
            ruined=portfolio_result.ruined,
        )

        run_results.append(
            RunResult(
                run_index=run_index,
                derived_seed=derived_seed_value(spec.seed, run_index),
                metrics=metrics,
                equity_curve=downsample_equity_curve(portfolio_result.equity_curve),
            )
        )
        run_metrics.append(metrics)
        all_r_multiples.extend(trade.r_multiple for trade in portfolio_result.trades)
        if run_trades is not None:
            run_trades.append(portfolio_result.trades)

    expectancy = build_expectancy_snapshot(spec, tuple(run_metrics), all_r_multiples)
    summary = compute_experiment_summary(
        tuple(run_metrics), all_r_multiples, expectancy=expectancy
    )
    duration = time.perf_counter() - started_at

    logger.info(
        "finished experiment name=%s duration=%.3fs status=completed", spec.name, duration
    )

    return ExperimentResult(
        name=spec.name,
        seed=spec.seed,
        runs=spec.runs,
        experiment_version=EXPERIMENT_VERSION,
        code_version=get_code_version(),
        data_version=None,
        created_at=created_at,
        duration=duration,
        status="completed",
        spec=spec,
        run_results=tuple(run_results),
        run_trades=tuple(run_trades) if run_trades is not None else None,
        summary=summary,
    )


def _build_strategy(strategy_spec: HistoricalStrategySpec, seed: int) -> Strategy:
    """Dispatch to the concrete `Strategy` by `strategy_spec.type` (Фаза 19 benchmarks,
    Фаза 22 additional strategy)."""
    if isinstance(strategy_spec, MovingAverageCrossoverStrategySpec):
        return MovingAverageCrossoverStrategy(
            fast_period=strategy_spec.fast_period,
            slow_period=strategy_spec.slow_period,
            stop_loss_pct=strategy_spec.stop_loss_pct,
        )
    if isinstance(strategy_spec, BuyAndHoldStrategySpec):
        return BuyAndHoldStrategy(stop_loss_pct=strategy_spec.stop_loss_pct)
    if isinstance(strategy_spec, BreakoutStrategySpec):
        return BreakoutStrategy(
            entry_lookback=strategy_spec.entry_lookback,
            exit_lookback=strategy_spec.exit_lookback,
            stop_loss_pct=strategy_spec.stop_loss_pct,
        )
    assert isinstance(strategy_spec, RandomEntryStrategySpec)
    return RandomEntryStrategy(
        stop_loss_pct=strategy_spec.stop_loss_pct,
        seed=seed,
        entry_probability=strategy_spec.entry_probability,
        exit_probability=strategy_spec.exit_probability,
    )


def _run_historical_backtest_experiment(
    spec: HistoricalBacktestExperimentSpec,
) -> ExperimentResult:
    """Run one deterministic historical backtest pass over `spec.data`/`spec.strategy`."""
    logger.info(
        "starting experiment name=%s seed=%s runs=%s", spec.name, spec.seed, spec.runs
    )
    created_at = datetime.now(UTC)
    started_at = time.perf_counter()

    data_source = CsvDataSource(
        path=spec.data.path, symbol=spec.data.symbol, timeframe=spec.data.timeframe
    )
    market_data = data_source.load()
    validate_market_data(market_data)
    data_version = compute_data_version(spec.data.path)

    if len(market_data.candles) > MAX_HISTORICAL_CANDLES:
        raise ExperimentTooLargeError(
            f"candle count={len(market_data.candles)} exceeds the MVP limit of "
            f"{MAX_HISTORICAL_CANDLES}"
        )

    strategy = _build_strategy(spec.strategy, spec.seed)
    trades = run_historical_backtest(market_data, strategy)

    portfolio_result = simulate_portfolio(
        trades=trades,
        initial_capital=spec.portfolio.initial_capital,
        risk_per_trade=spec.portfolio.risk_per_trade,
        commission_r=spec.portfolio.commission,
        slippage_r=spec.portfolio.slippage,
    )
    metrics = compute_metrics(
        trades=portfolio_result.trades,
        equity_curve=portfolio_result.equity_curve,
        initial_capital=spec.portfolio.initial_capital,
        ruined=portfolio_result.ruined,
    )
    run_result = RunResult(
        run_index=0,
        derived_seed=spec.seed,
        metrics=metrics,
        equity_curve=downsample_equity_curve(portfolio_result.equity_curve),
    )
    all_r_multiples = [trade.r_multiple for trade in portfolio_result.trades]
    expectancy = build_expectancy_snapshot(spec, (metrics,), all_r_multiples)
    summary = compute_experiment_summary((metrics,), all_r_multiples, expectancy=expectancy)
    duration = time.perf_counter() - started_at

    logger.info(
        "finished experiment name=%s duration=%.3fs status=completed", spec.name, duration
    )

    return ExperimentResult(
        name=spec.name,
        seed=spec.seed,
        runs=1,
        experiment_version=EXPERIMENT_VERSION,
        code_version=get_code_version(),
        data_version=data_version,
        created_at=created_at,
        duration=duration,
        status="completed",
        spec=spec,
        run_results=(run_result,),
        run_trades=(portfolio_result.trades,) if spec.storage.store_trades else None,
        summary=summary,
    )
