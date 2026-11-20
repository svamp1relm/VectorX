"""DataSource: the provider-independent contract every market data source implements.

Mirrors `vectorx.storage.repository.ExperimentRepository`'s Protocol pattern:
this module stays free of any concrete provider's dependencies so a future
backtest engine never needs to know which source produced a `MarketData`.
"""

from typing import Protocol, runtime_checkable

from vectorx.marketdata.types import MarketData


@runtime_checkable
class DataSource(Protocol):
    """Loads one fully-materialized `MarketData` set."""

    def load(self) -> MarketData:
        """Load and normalize this source's candles into a `MarketData`."""
        ...
