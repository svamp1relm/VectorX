"""ExperimentRunner: orchestrates one experiment end to end.

`ExperimentSpec` (YAML) -> N Monte Carlo runs (each with its own derived
seed) -> Portfolio -> Metrics -> `ExperimentSummary`. No YAML/Postgres/HTTP
concerns leak in beyond `spec` itself; storage (Phase 8) will persist
whatever this returns without needing to recompute anything.
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from vectorx.core.errors import ExperimentTooLargeError
from vectorx.core.rng import derived_rng, derived_seed_value
from vectorx.core.types import ExperimentSummary, Metrics, RunResult
from vectorx.experiments.spec import ExperimentSpec
from vectorx.experiments.versioning import EXPERIMENT_VERSION, get_code_version
from vectorx.simulation.monte_carlo import generate_trades
from vectorx.simulation.portfolio import downsample_equity_curve, simulate_portfolio
from vectorx.statistics.experiment_summary import compute_experiment_summary
from vectorx.statistics.metrics import compute_metrics

logger = logging.getLogger(__name__)

MAX_OPERATIONS = 2_000_000
"""Pre-flight limit on runs * n_trades for one experiment (MVP safety guard)."""


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    """Everything one experiment execution produced, ready for storage."""

    name: str
    seed: int
    runs: int
    experiment_version: int
    code_version: str
    created_at: datetime
    duration: float
    status: str
    spec: ExperimentSpec
    run_results: tuple[RunResult, ...]
    summary: ExperimentSummary


def run_experiment(spec: ExperimentSpec) -> ExperimentResult:
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

    summary = compute_experiment_summary(tuple(run_metrics), all_r_multiples)
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
        created_at=created_at,
        duration=duration,
        status="completed",
        spec=spec,
        run_results=tuple(run_results),
        summary=summary,
    )
