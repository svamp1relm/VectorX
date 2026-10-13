"""Domain error hierarchy: invalid params, empty trades, portfolio ruin."""

import pytest

from vectorx.core.errors import (
    EmptyTradesError,
    ExperimentTooLargeError,
    InvalidMarketDataError,
    InvalidModelParametersError,
    PortfolioRuinedError,
    VectorXError,
)


def test_domain_errors_are_vectorx_errors():
    assert issubclass(InvalidModelParametersError, VectorXError)
    assert issubclass(EmptyTradesError, VectorXError)
    assert issubclass(PortfolioRuinedError, VectorXError)
    assert issubclass(ExperimentTooLargeError, VectorXError)
    assert issubclass(InvalidMarketDataError, VectorXError)


def test_vectorx_error_is_an_exception():
    assert issubclass(VectorXError, Exception)


def test_invalid_model_parameters_error_is_raisable_and_catchable():
    with pytest.raises(VectorXError):
        raise InvalidModelParametersError("p_win must be in [0, 1]")
