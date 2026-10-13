"""Domain error hierarchy for invalid parameters, empty data, ruin, and market data."""


class VectorXError(Exception):
    """Base class for all VectorX domain errors."""


class InvalidModelParametersError(VectorXError):
    """Raised when a probability/model parameter is outside its valid domain."""


class EmptyTradesError(VectorXError):
    """Raised when statistics are requested for an empty trade sequence."""


class PortfolioRuinedError(VectorXError):
    """Raised when a simulated portfolio's equity reaches zero or below."""


class ExperimentTooLargeError(VectorXError):
    """Raised when runs * n_trades exceeds the MVP's pre-flight operation limit."""


class InvalidMarketDataError(VectorXError):
    """Raised when historical market data fails structural or OHLCV validation."""


class AnalysisUnavailableError(VectorXError):
    """Raised when statistical analysis is requested for an experiment with no
    raw trades stored (i.e. `storage.store_trades=false`, Фаза 18a)."""
