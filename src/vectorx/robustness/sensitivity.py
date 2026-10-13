"""run_sensitivity_analysis: parameter sensitivity over a sweep grid (Фаза 21).

Pure composition of existing building blocks: `generate_sweep_specs` (Фаза
18c) expands the grid, `run_experiment` (unchanged) runs each combination,
and expectancy/Sharpe for each combination come from its (sweep-forced) raw
trades (Фаза 18a/19). No new simulation logic — "already have all of these
pieces, run many of them and report one row per combination."
"""

from dataclasses import dataclass
from functools import reduce

from vectorx.experiments.runner import run_experiment
from vectorx.experiments.spec import ExperimentSpec
from vectorx.experiments.sweep import SweepSpec, generate_sweep_specs
from vectorx.statistics.risk_adjusted import compute_risk_adjusted_metrics


@dataclass(frozen=True, slots=True)
class SensitivityPoint:
    """One sweep combination's parameter values plus its resulting statistics."""

    params: dict
    expectancy_sample: float
    sharpe: float | None


@dataclass(frozen=True, slots=True)
class SensitivityResult:
    points: tuple[SensitivityPoint, ...]


def _get_dotted(spec: ExperimentSpec, dotted_key: str):
    return reduce(getattr, dotted_key.split("."), spec)


def run_sensitivity_analysis(sweep: SweepSpec) -> SensitivityResult:
    """Run every combination in `sweep.grid` and report expectancy/Sharpe for each."""
    specs = generate_sweep_specs(sweep)

    points = []
    for spec in specs:
        result = run_experiment(spec)
        assert result.run_trades is not None  # sweep forces storage.store_trades=true
        r_multiples = [trade.r_multiple for run_trades in result.run_trades for trade in run_trades]
        expectancy_sample = sum(r_multiples) / len(r_multiples)
        risk_adjusted = compute_risk_adjusted_metrics(
            r_multiples,
            total_return=result.summary.mean_total_return,
            max_drawdown=max(run.metrics.max_drawdown for run in result.run_results),
        )
        params = {key: _get_dotted(spec, key) for key in sweep.grid}
        points.append(
            SensitivityPoint(
                params=params, expectancy_sample=expectancy_sample, sharpe=risk_adjusted.sharpe
            )
        )

    return SensitivityResult(points=tuple(points))
