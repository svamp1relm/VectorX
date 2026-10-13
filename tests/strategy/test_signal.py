"""Signal: a strategy's directional intent for one candle."""

from vectorx.strategy.signal import Signal


def test_signal_has_buy_sell_hold_members():
    assert Signal.BUY == "BUY"
    assert Signal.SELL == "SELL"
    assert Signal.HOLD == "HOLD"


def test_signal_members_are_distinct():
    assert len({Signal.BUY, Signal.SELL, Signal.HOLD}) == 3
