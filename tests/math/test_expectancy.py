"""Theoretical vs sample expectancy — two distinct, non-interchangeable values."""

import pytest

from vectorx.core.errors import EmptyTradesError, InvalidModelParametersError
from vectorx.math.expectancy import expectancy_sample, expectancy_theoretical


def test_expectancy_theoretical_known_value():
    result = expectancy_theoretical(p_win=0.55, win_r=2.0, loss_r=-1.0)

    assert result == pytest.approx(0.65)


def test_expectancy_theoretical_rejects_invalid_p_win():
    with pytest.raises(InvalidModelParametersError):
        expectancy_theoretical(p_win=1.5, win_r=2.0, loss_r=-1.0)


def test_expectancy_theoretical_rejects_non_positive_win_r():
    with pytest.raises(InvalidModelParametersError):
        expectancy_theoretical(p_win=0.5, win_r=0.0, loss_r=-1.0)


def test_expectancy_theoretical_rejects_non_negative_loss_r():
    with pytest.raises(InvalidModelParametersError):
        expectancy_theoretical(p_win=0.5, win_r=2.0, loss_r=0.0)


def test_expectancy_sample_is_mean_of_r_multiples():
    result = expectancy_sample([2.0, -1.0, 2.0, -1.0])

    assert result == pytest.approx(0.5)


def test_expectancy_sample_single_value():
    assert expectancy_sample([3.0]) == pytest.approx(3.0)


def test_expectancy_sample_empty_raises_empty_trades_error():
    with pytest.raises(EmptyTradesError):
        expectancy_sample([])
