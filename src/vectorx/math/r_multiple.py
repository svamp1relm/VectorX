"""Deterministic mapping from a win/loss outcome to its R-multiple.

Randomness (deciding whether a trade wins) belongs to `simulation`; this
module only resolves an already-decided outcome to its R value.
"""

from vectorx.math.validation import validate_loss_r, validate_win_r


def r_multiple_for_outcome(is_win: bool, win_r: float, loss_r: float) -> float:
    """Return `win_r` for a winning outcome, `loss_r` otherwise."""
    validate_win_r(win_r)
    validate_loss_r(loss_r)
    return win_r if is_win else loss_r
