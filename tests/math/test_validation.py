"""Model parameter validation shared by expectancy and Monte Carlo."""

import pytest

from vectorx.core.errors import InvalidModelParametersError
from vectorx.math.validation import validate_model_parameters


def test_valid_parameters_pass_silently():
    validate_model_parameters(p_win=0.55, win_r=2.0, loss_r=-1.0)


def test_p_win_boundaries_are_valid():
    validate_model_parameters(p_win=0.0, win_r=2.0, loss_r=-1.0)
    validate_model_parameters(p_win=1.0, win_r=2.0, loss_r=-1.0)


def test_p_win_below_zero_is_invalid():
    with pytest.raises(InvalidModelParametersError):
        validate_model_parameters(p_win=-0.0001, win_r=2.0, loss_r=-1.0)


def test_p_win_above_one_is_invalid():
    with pytest.raises(InvalidModelParametersError):
        validate_model_parameters(p_win=1.0001, win_r=2.0, loss_r=-1.0)


def test_win_r_must_be_strictly_positive():
    with pytest.raises(InvalidModelParametersError):
        validate_model_parameters(p_win=0.5, win_r=0.0, loss_r=-1.0)
    with pytest.raises(InvalidModelParametersError):
        validate_model_parameters(p_win=0.5, win_r=-2.0, loss_r=-1.0)


def test_loss_r_must_be_strictly_negative():
    with pytest.raises(InvalidModelParametersError):
        validate_model_parameters(p_win=0.5, win_r=2.0, loss_r=0.0)
    with pytest.raises(InvalidModelParametersError):
        validate_model_parameters(p_win=0.5, win_r=2.0, loss_r=1.0)
