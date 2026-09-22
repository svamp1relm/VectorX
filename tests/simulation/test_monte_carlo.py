"""Monte Carlo trade generation: reproducible, R-multiple only, no market time.

`generate_trades` consumes an already-built `numpy.random.Generator` (see
`vectorx.core.rng.derived_rng`) rather than a seed itself, so simulation
stays decoupled from seed-derivation policy.
"""

import numpy as np
import pytest

from vectorx.core.errors import InvalidModelParametersError
from vectorx.core.rng import derived_rng
from vectorx.simulation.monte_carlo import generate_trades


def test_generates_the_requested_number_of_trades():
    rng = derived_rng(experiment_seed=1, run_index=0)

    trades = generate_trades(p_win=0.55, win_r=2.0, loss_r=-1.0, n_trades=10, rng=rng)

    assert len(trades) == 10


def test_trades_have_sequential_index_long_side_and_no_market_time():
    rng = derived_rng(experiment_seed=1, run_index=0)

    trades = generate_trades(p_win=0.55, win_r=2.0, loss_r=-1.0, n_trades=5, rng=rng)

    for i, trade in enumerate(trades):
        assert trade.trade_index == i
        assert trade.side == "long"
        assert trade.entry_ts is None
        assert trade.exit_ts is None
        assert trade.pnl is None


def test_r_multiple_is_always_win_r_or_loss_r():
    rng = derived_rng(experiment_seed=7, run_index=0)

    trades = generate_trades(p_win=0.5, win_r=2.0, loss_r=-1.0, n_trades=200, rng=rng)

    assert all(t.r_multiple in (2.0, -1.0) for t in trades)


def test_same_derived_rng_reproduces_identical_r_multiples():
    trades_a = generate_trades(
        p_win=0.55, win_r=2.0, loss_r=-1.0, n_trades=100,
        rng=derived_rng(experiment_seed=42, run_index=0),
    )
    trades_b = generate_trades(
        p_win=0.55, win_r=2.0, loss_r=-1.0, n_trades=100,
        rng=derived_rng(experiment_seed=42, run_index=0),
    )

    assert [t.r_multiple for t in trades_a] == [t.r_multiple for t in trades_b]


def test_different_run_index_diverges():
    trades_a = generate_trades(
        p_win=0.55, win_r=2.0, loss_r=-1.0, n_trades=100,
        rng=derived_rng(experiment_seed=42, run_index=0),
    )
    trades_b = generate_trades(
        p_win=0.55, win_r=2.0, loss_r=-1.0, n_trades=100,
        rng=derived_rng(experiment_seed=42, run_index=1),
    )

    assert [t.r_multiple for t in trades_a] != [t.r_multiple for t in trades_b]


def test_rejects_invalid_model_parameters():
    rng = derived_rng(experiment_seed=1, run_index=0)

    with pytest.raises(InvalidModelParametersError):
        generate_trades(p_win=1.5, win_r=2.0, loss_r=-1.0, n_trades=10, rng=rng)


def test_rejects_non_positive_n_trades():
    rng = derived_rng(experiment_seed=1, run_index=0)

    with pytest.raises(InvalidModelParametersError):
        generate_trades(p_win=0.5, win_r=2.0, loss_r=-1.0, n_trades=0, rng=rng)


def test_empirical_win_rate_converges_to_p_win_at_scale():
    """Statistical check at 50k trades — separate from the small shape tests above."""
    p_win = 0.55
    n_trades = 50_000
    rng = derived_rng(experiment_seed=99, run_index=0)

    trades = generate_trades(p_win=p_win, win_r=2.0, loss_r=-1.0, n_trades=n_trades, rng=rng)

    empirical_win_rate = np.mean([t.r_multiple == 2.0 for t in trades])
    assert empirical_win_rate == pytest.approx(p_win, abs=0.02)
