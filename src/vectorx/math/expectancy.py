"""Theoretical expectancy (from model parameters) vs sample expectancy
(from realized R-multiples). These are deliberately separate functions:
one must never be substituted for the other.
"""

from collections.abc import Sequence

from vectorx.core.errors import EmptyTradesError
from vectorx.math.validation import validate_model_parameters


def expectancy_theoretical(p_win: float, win_r: float, loss_r: float) -> float:
    """E[X] = p_win * win_r + (1 - p_win) * loss_r, computed from model parameters."""
    validate_model_parameters(p_win=p_win, win_r=win_r, loss_r=loss_r)
    return p_win * win_r + (1.0 - p_win) * loss_r


def expectancy_sample(r_multiples: Sequence[float]) -> float:
    """Mean realized R-multiple across a (non-empty) sequence of trades."""
    if not r_multiples:
        raise EmptyTradesError("expectancy_sample requires at least one r_multiple")
    return sum(r_multiples) / len(r_multiples)
