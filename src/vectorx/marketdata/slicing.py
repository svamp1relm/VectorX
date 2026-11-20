"""Time-range slicing: `MarketData` -> subset by `[start, end]` (both inclusive).

Needed by Out-of-Sample (Фаза 20) and Robustness/walk-forward (Фаза 21) to
split one historical dataset into non-overlapping time windows. Both ends
are inclusive by design: callers split a dataset by picking the exact
timestamps of two adjacent candles (e.g. train ends at `candles[k-1].timestamp`,
test begins at `candles[k].timestamp`) rather than a half-open interval, so
two adjacent slices reconstruct the original candle set exactly, with no
gap and no duplicate candle at the boundary.
"""

from datetime import datetime

from vectorx.core.errors import InvalidMarketDataError
from vectorx.marketdata.types import MarketData


def slice_market_data(data: MarketData, start: datetime, end: datetime) -> MarketData:
    """Return a new `MarketData` with only the candles in `[start, end]`.

    Raises `InvalidMarketDataError` if `start > end` or no candle falls in
    the range — an empty slice is always a caller error, never silent.
    """
    if start > end:
        raise InvalidMarketDataError(f"start ({start}) must be <= end ({end})")

    candles = tuple(candle for candle in data.candles if start <= candle.timestamp <= end)
    if not candles:
        raise InvalidMarketDataError(
            f"no candles in range [{start}, {end}] for {data.symbol}/{data.timeframe}"
        )

    return MarketData(symbol=data.symbol, timeframe=data.timeframe, candles=candles)
