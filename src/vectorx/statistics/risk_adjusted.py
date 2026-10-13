"""compute_risk_adjusted_metrics: Sharpe/Sortino/Calmar over a run's
R-multiples + Metrics (Фаза 19, locked to
`vectorx.statistics.versioning.ANALYSIS_VERSION`).

Unannualized by design: this domain has no fixed trading frequency to
annualize against (Monte Carlo trades have no calendar time at all), so
these are plain per-trade ratios, not the conventional annualized Sharpe.
Each ratio is `None` when its denominator is undefined (zero variance, no
downside, or zero drawdown) rather than `inf`/`nan`.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from vectorx.core.errors import EmptyTradesError


@dataclass(frozen=True, slots=True)
class RiskAdjustedMetrics:
    """Per-trade Sharpe/Sortino plus run-level Calmar; each `None` if undefined."""

    sharpe: float | None
    sortino: float | None
    calmar: float | None


def compute_risk_adjusted_metrics(
    r_multiples: Sequence[float], total_return: float, max_drawdown: float
) -> RiskAdjustedMetrics:
    """Sharpe = mean(r)/stdev(r); Sortino = mean(r)/downside_deviation(r);
    Calmar = total_return/max_drawdown."""
    if not r_multiples:
        raise EmptyTradesError("compute_risk_adjusted_metrics requires at least one r_multiple")

    mean_r = sum(r_multiples) / len(r_multiples)
    variance = sum((r - mean_r) ** 2 for r in r_multiples) / len(r_multiples)
    stdev = math.sqrt(variance)
    sharpe = mean_r / stdev if stdev > 0.0 else None

    downside_variance = sum(min(r, 0.0) ** 2 for r in r_multiples) / len(r_multiples)
    downside_deviation = math.sqrt(downside_variance)
    sortino = mean_r / downside_deviation if downside_deviation > 0.0 else None

    calmar = total_return / max_drawdown if max_drawdown > 0.0 else None

    return RiskAdjustedMetrics(sharpe=sharpe, sortino=sortino, calmar=calmar)
