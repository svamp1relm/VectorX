"""Equity curve downsampling for storage/UI (full curve is used for metrics)."""

from vectorx.core.types import EquityPoint
from vectorx.simulation.portfolio import downsample_equity_curve


def _curve(n: int) -> tuple[EquityPoint, ...]:
    return tuple(EquityPoint(index=i, equity=float(i), drawdown=0.0) for i in range(n))


def test_curve_at_or_below_limit_is_returned_unchanged():
    curve = _curve(10)

    assert downsample_equity_curve(curve, max_points=500) == curve


def test_curve_exactly_at_limit_is_unchanged():
    curve = _curve(500)

    assert downsample_equity_curve(curve, max_points=500) == curve


def test_curve_above_limit_is_downsampled_to_at_most_max_points():
    curve = _curve(10_000)

    result = downsample_equity_curve(curve, max_points=500)

    assert len(result) <= 500
    assert result[0] == curve[0]
    assert result[-1] == curve[-1]


def test_downsampled_indices_are_strictly_increasing():
    curve = _curve(10_000)

    result = downsample_equity_curve(curve, max_points=500)

    indices = [point.index for point in result]
    assert indices == sorted(set(indices))
