"""MarketCandle/MarketData: immutable historical OHLCV containers.

Plain data containers with no computation logic, mirroring `vectorx.core.types`'s
style. `MarketCandle.timestamp` must be timezone-aware (UTC): unlike Monte
Carlo's `Trade.trade_index`, a future historical backtest engine treats these as
real market time, not an ordinal position.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MarketCandle:
    """One OHLCV bar."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class MarketData:
    """A named, ordered sequence of candles for one symbol/timeframe."""

    symbol: str
    timeframe: str
    candles: tuple[MarketCandle, ...]
