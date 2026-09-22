"""Monte Carlo trade generation: draw i.i.d. bernoulli(p_win) outcomes.

Monte Carlo has no market calendar, so `entry_ts`/`exit_ts`/`pnl` stay
`None` on every generated trade (see `vectorx.core.types.Trade`); only
`trade_index` and `r_multiple` are meaningful here.
"""

import numpy as np

from vectorx.core.errors import InvalidModelParametersError
from vectorx.core.types import Trade
from vectorx.math.r_multiple import r_multiple_for_outcome
from vectorx.math.validation import validate_model_parameters


def generate_trades(
    p_win: float,
    win_r: float,
    loss_r: float,
    n_trades: int,
    rng: np.random.Generator,
) -> tuple[Trade, ...]:
    """Generate one run's worth of long-only Monte Carlo trades."""
    validate_model_parameters(p_win=p_win, win_r=win_r, loss_r=loss_r)
    if n_trades <= 0:
        raise InvalidModelParametersError(f"n_trades must be > 0, got {n_trades}")

    wins = rng.random(n_trades) < p_win
    return tuple(
        Trade(
            trade_index=i,
            side="long",
            r_multiple=r_multiple_for_outcome(bool(is_win), win_r, loss_r),
        )
        for i, is_win in enumerate(wins)
    )
