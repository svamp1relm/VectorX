"""DataSource: the Protocol every market data source must satisfy structurally."""

from vectorx.marketdata.source import DataSource
from vectorx.marketdata.types import MarketData


def test_a_conforming_class_satisfies_the_protocol():
    class FakeSource:
        def load(self) -> MarketData:
            return MarketData(symbol="BTCUSDT", timeframe="1h", candles=())

    assert isinstance(FakeSource(), DataSource)


def test_a_non_conforming_class_does_not_satisfy_the_protocol():
    class NotASource:
        pass

    assert not isinstance(NotASource(), DataSource)
