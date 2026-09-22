"""Deterministic R-multiple resolution: outcome -> win_r or loss_r."""

import pytest

from vectorx.core.errors import InvalidModelParametersError
from vectorx.math.r_multiple import r_multiple_for_outcome


def test_win_outcome_resolves_to_win_r():
    assert r_multiple_for_outcome(is_win=True, win_r=2.0, loss_r=-1.0) == 2.0


def test_loss_outcome_resolves_to_loss_r():
    assert r_multiple_for_outcome(is_win=False, win_r=2.0, loss_r=-1.0) == -1.0


def test_rejects_invalid_win_r():
    with pytest.raises(InvalidModelParametersError):
        r_multiple_for_outcome(is_win=True, win_r=-2.0, loss_r=-1.0)


def test_rejects_invalid_loss_r():
    with pytest.raises(InvalidModelParametersError):
        r_multiple_for_outcome(is_win=False, win_r=2.0, loss_r=1.0)
