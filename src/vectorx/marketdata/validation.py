"""validate_market_data: provider-independent OHLCV/timestamp validation.

Never imports a concrete `DataSource` — works only against an already-normalized
`MarketData`, so every future source (Parquet, MEXC, CCXT, ...) shares the same
checks without duplicating them. Structural/domain violations (duplicate or
out-of-order timestamps, invalid OHLC, negative volume) raise immediately. Gaps
relative to an expected candle interval are diagnostic only and never raise:
missing candles are a normal feature of real market data, not necessarily an
error.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from vectorx.core.errors import InvalidMarketDataError
from vectorx.marketdata.types import MarketCandle, MarketData


@dataclass(frozen=True, slots=True)
class MarketDataGap:
    """A detected gap: no candle at `expected_timestamp` before `actual_timestamp`."""

    after_index: int
    expected_timestamp: datetime
    actual_timestamp: datetime


def validate_market_data(
    data: MarketData, expected_interval: timedelta | None = None
) -> tuple[MarketDataGap, ...]:
    """Validate structural/OHLCV correctness, raising on the first violation.

    Returns gaps detected relative to `expected_interval` (empty tuple if not
    given, or if none found).
    """
    if not data.candles:
        raise InvalidMarketDataError("MarketData must contain at least one candle")

    gaps: list[MarketDataGap] = []
    previous = data.candles[0]
    _validate_candle(previous, index=0)

    for index, candle in enumerate(data.candles[1:], start=1):
        _validate_candle(candle, index=index)

        if candle.timestamp <= previous.timestamp:
            raise InvalidMarketDataError(
                f"candle {index} timestamp {candle.timestamp} must be strictly after "
                f"candle {index - 1} timestamp {previous.timestamp}"
            )

        if expected_interval is not None:
            expected_timestamp = previous.timestamp + expected_interval
            if candle.timestamp > expected_timestamp:
                gaps.append(
                    MarketDataGap(
                        after_index=index - 1,
                        expected_timestamp=expected_timestamp,
                        actual_timestamp=candle.timestamp,
                    )
                )

        previous = candle

    return tuple(gaps)


def _validate_candle(candle: MarketCandle, *, index: int) -> None:
    if candle.low > candle.high:
        raise InvalidMarketDataError(
            f"candle {index}: low ({candle.low}) must be <= high ({candle.high})"
        )
    if not candle.low <= candle.open <= candle.high:
        raise InvalidMarketDataError(
            f"candle {index}: open ({candle.open}) must be within "
            f"[low, high] = [{candle.low}, {candle.high}]"
        )
    if not candle.low <= candle.close <= candle.high:
        raise InvalidMarketDataError(
            f"candle {index}: close ({candle.close}) must be within "
            f"[low, high] = [{candle.low}, {candle.high}]"
        )
    if candle.volume < 0.0:
        raise InvalidMarketDataError(f"candle {index}: volume must be >= 0, got {candle.volume}")
