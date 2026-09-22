"""Domain error hierarchy for invalid parameters, empty data, and ruin."""


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
