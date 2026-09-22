"""Shared validation for the probabilistic trade model parameters."""

from vectorx.core.errors import InvalidModelParametersError


def validate_p_win(p_win: float) -> None:
    if not 0.0 <= p_win <= 1.0:
        raise InvalidModelParametersError(f"p_win must be in [0, 1], got {p_win}")


def validate_win_r(win_r: float) -> None:
    if win_r <= 0.0:
        raise InvalidModelParametersError(f"win_r must be > 0, got {win_r}")


def validate_loss_r(loss_r: float) -> None:
    if loss_r >= 0.0:
        raise InvalidModelParametersError(f"loss_r must be < 0, got {loss_r}")


def validate_model_parameters(p_win: float, win_r: float, loss_r: float) -> None:
    """Validate a Monte Carlo model's parameters, raising on the first violation."""
    validate_p_win(p_win)
    validate_win_r(win_r)
    validate_loss_r(loss_r)
