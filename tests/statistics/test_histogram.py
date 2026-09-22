"""Histogram bins v1: numpy.histogram(bins=50), locked to experiment_version.

Backend computes bins; consumers (API/UI) only render `edges`/`counts`.
"""

import pytest

from vectorx.core.errors import EmptyTradesError
from vectorx.statistics.histogram import compute_histogram_bins


def test_histogram_shape_matches_locked_algorithm():
    values = [float(i) for i in range(100)]

    bins = compute_histogram_bins(values)

    assert len(bins.edges) == 51
    assert len(bins.counts) == 50
    assert sum(bins.counts) == len(values)
    assert bins.edges[0] == pytest.approx(0.0)
    assert bins.edges[-1] == pytest.approx(99.0)


def test_histogram_respects_custom_bin_count():
    values = [1.0, 2.0, 3.0]

    bins = compute_histogram_bins(values, bins=10)

    assert len(bins.edges) == 11
    assert len(bins.counts) == 10


def test_degenerate_single_value_widens_range_by_half():
    bins = compute_histogram_bins([5.0, 5.0, 5.0])

    assert bins.edges[0] == pytest.approx(4.5)
    assert bins.edges[-1] == pytest.approx(5.5)
    assert sum(bins.counts) == 3


def test_empty_values_raises_empty_trades_error():
    with pytest.raises(EmptyTradesError):
        compute_histogram_bins([])
