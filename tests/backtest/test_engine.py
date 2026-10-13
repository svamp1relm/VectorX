"""run_historical_backtest: candle-by-candle Strategy -> Trade[] engine."""

from datetime import UTC, datetime, timedelta

import pytest

from vectorx.backtest.engine import run_historical_backtest
from vectorx.marketdata.types import MarketCandle, MarketData
from vectorx.simulation.portfolio import simulate_portfolio
from vectorx.strategy.moving_average_crossover import MovingAverageCrossoverStrategy
from vectorx.strategy.signal import Signal

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _candle(offset_minutes: int, close: float) -> MarketCandle:
    return MarketCandle(
        timestamp=_START + timedelta(minutes=offset_minutes),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000.0,
    )


def _market_data(closes: list[float]) -> MarketData:
    candles = tuple(_candle(i, close) for i, close in enumerate(closes))
    return MarketData(symbol="BTCUSDT", timeframe="1h", candles=candles)


class ScriptedStrategy:
    """Fake `Strategy` returning a fixed, pre-scripted sequence of signals."""

    def __init__(self, signals: list[Signal], stop_loss_pct: float = 0.01) -> None:
        self._signals = iter(signals)
        self.stop_loss_pct = stop_loss_pct

    def on_candle(self, candle: MarketCandle) -> Signal:
        return next(self._signals)


def test_no_trades_when_strategy_never_buys():
    market_data = _market_data([100.0, 101.0, 102.0])
    strategy = ScriptedStrategy([Signal.HOLD, Signal.HOLD, Signal.HOLD])

    trades = run_historical_backtest(market_data, strategy)

    assert trades == ()


def test_buy_then_sell_produces_one_closed_trade():
    market_data = _market_data([100.0, 105.0, 90.0])
    strategy = ScriptedStrategy([Signal.BUY, Signal.HOLD, Signal.SELL], stop_loss_pct=0.01)

    trades = run_historical_backtest(market_data, strategy)

    assert len(trades) == 1
    trade = trades[0]
    assert trade.trade_index == 0
    assert trade.side == "long"
    assert trade.risk == 1.0
    assert trade.entry_ts == market_data.candles[0].timestamp
    assert trade.exit_ts == market_data.candles[2].timestamp
    assert trade.pnl == pytest.approx(-10.0)
    assert trade.r_multiple == pytest.approx((90.0 - 100.0) / (100.0 * 0.01))


def test_open_position_is_force_closed_at_last_candle():
    market_data = _market_data([100.0, 105.0, 110.0])
    strategy = ScriptedStrategy([Signal.BUY, Signal.HOLD, Signal.HOLD], stop_loss_pct=0.02)

    trades = run_historical_backtest(market_data, strategy)

    assert len(trades) == 1
    trade = trades[0]
    assert trade.exit_ts == market_data.candles[-1].timestamp
    assert trade.pnl == pytest.approx(10.0)
    assert trade.r_multiple == pytest.approx((110.0 - 100.0) / (100.0 * 0.02))


def test_repeated_buy_signal_does_not_pyramid():
    market_data = _market_data([100.0, 100.0, 105.0])
    strategy = ScriptedStrategy([Signal.BUY, Signal.BUY, Signal.SELL], stop_loss_pct=0.01)

    trades = run_historical_backtest(market_data, strategy)

    assert len(trades) == 1
    assert trades[0].entry_ts == market_data.candles[0].timestamp


def test_sell_signal_without_open_position_is_ignored():
    market_data = _market_data([100.0, 105.0, 110.0])
    strategy = ScriptedStrategy([Signal.SELL, Signal.BUY, Signal.SELL], stop_loss_pct=0.01)

    trades = run_historical_backtest(market_data, strategy)

    assert len(trades) == 1
    assert trades[0].entry_ts == market_data.candles[1].timestamp
    assert trades[0].exit_ts == market_data.candles[2].timestamp


def test_multiple_completed_trades_have_sequential_trade_index():
    market_data = _market_data([100.0, 105.0, 100.0, 108.0])
    strategy = ScriptedStrategy(
        [Signal.BUY, Signal.SELL, Signal.BUY, Signal.SELL], stop_loss_pct=0.01
    )

    trades = run_historical_backtest(market_data, strategy)

    assert [t.trade_index for t in trades] == [0, 1]


def test_ma_crossover_trades_are_compatible_with_simulate_portfolio():
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    market_data = _market_data(closes)
    strategy = MovingAverageCrossoverStrategy(fast_period=2, slow_period=4, stop_loss_pct=0.01)

    trades = run_historical_backtest(market_data, strategy)

    assert len(trades) == 2
    result = simulate_portfolio(trades=trades, initial_capital=10_000.0, risk_per_trade=0.01)
    assert len(result.equity_curve) == len(trades) + 1
