"""Histogram bins v1 — locked to `experiment_version=1`, do not change silently.

Algorithm: `numpy.histogram(values, bins=50, range=(vmin, vmax))` where
`vmin, vmax = min(values), max(values)`; if `vmin == vmax`, the range widens
to `(vmin - 0.5, vmax + 0.5)` so a degenerate sample still produces a valid
histogram. Any change to this algorithm must bump `experiment_version`.
"""

from collections.abc import Sequence

import numpy as np

from vectorx.core.errors import EmptyTradesError
from vectorx.core.types import HistogramBins


def compute_histogram_bins(values: Sequence[float], bins: int = 50) -> HistogramBins:
    """Compute a fixed-bin-count histogram over `values`."""
    if not values:
        raise EmptyTradesError("compute_histogram_bins requires at least one value")

    vmin = min(values)
    vmax = max(values)
    value_range = (vmin - 0.5, vmax + 0.5) if vmin == vmax else (vmin, vmax)

    counts, edges = np.histogram(values, bins=bins, range=value_range)
    return HistogramBins(
        edges=tuple(float(e) for e in edges),
        counts=tuple(int(c) for c in counts),
    )
