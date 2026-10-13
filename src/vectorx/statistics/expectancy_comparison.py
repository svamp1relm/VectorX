"""Expectancy snapshots and cross-experiment comparison on a common R scale."""

from dataclasses import replace
from math import isclose

from vectorx.core.errors import EmptyTradesError, InvalidModelParametersError
from vectorx.core.types import (
    ComparisonDeltas,
    ExpectancyComparison,
    ExpectancyComparisonResult,
    ExpectancyEstimate,
    Metrics,
    OutOfSampleComparisonResult,
    RiskCompatibility,
    RiskDefinition,
)
from vectorx.experiments.spec import (
    HistoricalBacktestExperimentSpec,
    MonteCarloExperimentSpec,
)
from vectorx.math.expectancy import expectancy_theoretical

CANONICAL_RISK_FRACTION = 0.01
RISK_NORMALIZATION_VERSION = "r-v1"
SUPPORTED_RISK_METHODS = {"model_r", "entry_price_stop_loss_fraction"}


def risk_definition_for_spec(
    spec: MonteCarloExperimentSpec | HistoricalBacktestExperimentSpec,
) -> RiskDefinition:
    if isinstance(spec, MonteCarloExperimentSpec):
        method = "model_r"
        risk_unit_fraction = spec.model.risk_unit_fraction
    else:
        method = "entry_price_stop_loss_fraction"
        risk_unit_fraction = spec.strategy.stop_loss_pct
    return RiskDefinition(
        unit="R",
        normalization_version=RISK_NORMALIZATION_VERSION,
        method=method,
        risk_unit_fraction=risk_unit_fraction,
        cost_basis="gross_r",
    )


def build_expectancy_snapshot(
    spec: MonteCarloExperimentSpec | HistoricalBacktestExperimentSpec,
    run_metrics: tuple[Metrics, ...],
    all_r_multiples: tuple[float, ...] | list[float],
) -> ExpectancyComparison:
    if not run_metrics:
        raise EmptyTradesError("build_expectancy_snapshot requires at least one run")
    if not all_r_multiples:
        raise EmptyTradesError("build_expectancy_snapshot requires at least one trade")

    risk_definition = risk_definition_for_spec(spec)
    sample_size = len(all_r_multiples)
    sample_value = sum(all_r_multiples) / sample_size

    if isinstance(spec, MonteCarloExperimentSpec):
        theoretical = ExpectancyEstimate(
            value=expectancy_theoretical(
                p_win=spec.model.p_win,
                win_r=spec.model.win_r,
                loss_r=spec.model.loss_r,
            ),
            canonical_value=None,
            source="theoretical_model",
            unit="R",
            sample_size=None,
            planned_sample_size=None,
            risk_definition=risk_definition,
        )
        sample = ExpectancyEstimate(
            value=sample_value,
            canonical_value=None,
            source="monte_carlo_sample",
            unit="R",
            sample_size=sample_size,
            planned_sample_size=spec.runs * spec.model.n_trades,
            risk_definition=risk_definition,
        )
        return ExpectancyComparison(theoretical=theoretical, sample=sample)

    historical = ExpectancyEstimate(
        value=sample_value,
        canonical_value=None,
        source="historical_backtest",
        unit="R",
        sample_size=sample_size,
        planned_sample_size=None,
        risk_definition=risk_definition,
    )
    return ExpectancyComparison(historical=historical)


def build_expectancy_snapshot_from_run_metrics(
    spec: MonteCarloExperimentSpec | HistoricalBacktestExperimentSpec,
    run_metrics: tuple[Metrics, ...],
) -> ExpectancyComparison:
    if not run_metrics:
        raise EmptyTradesError("build_expectancy_snapshot requires at least one run")
    sample_size = sum(metrics.trades for metrics in run_metrics)
    if sample_size == 0:
        raise EmptyTradesError("build_expectancy_snapshot requires at least one trade")
    pooled_sample = sum(metrics.expectancy_sample * metrics.trades for metrics in run_metrics)
    pooled_sample /= sample_size

    risk_definition = risk_definition_for_spec(spec)
    if isinstance(spec, MonteCarloExperimentSpec):
        theoretical = ExpectancyEstimate(
            value=expectancy_theoretical(
                p_win=spec.model.p_win,
                win_r=spec.model.win_r,
                loss_r=spec.model.loss_r,
            ),
            canonical_value=None,
            source="theoretical_model",
            unit="R",
            sample_size=None,
            planned_sample_size=None,
            risk_definition=risk_definition,
        )
        sample = ExpectancyEstimate(
            value=pooled_sample,
            canonical_value=None,
            source="monte_carlo_sample",
            unit="R",
            sample_size=sample_size,
            planned_sample_size=spec.runs * spec.model.n_trades,
            risk_definition=risk_definition,
        )
        return ExpectancyComparison(theoretical=theoretical, sample=sample)

    historical = ExpectancyEstimate(
        value=pooled_sample,
        canonical_value=None,
        source="historical_backtest",
        unit="R",
        sample_size=sample_size,
        planned_sample_size=None,
        risk_definition=risk_definition,
    )
    return ExpectancyComparison(historical=historical)


def canonicalize_estimate(
    estimate: ExpectancyEstimate, reference_risk_fraction: float
) -> ExpectancyEstimate:
    if reference_risk_fraction <= 0.0:
        raise InvalidModelParametersError("reference_risk_fraction must be > 0")
    factor = estimate.risk_definition.risk_unit_fraction / reference_risk_fraction
    return replace(estimate, canonical_value=estimate.value * factor)


def compare_expectancy(
    monte_carlo: ExpectancyComparison,
    historical: ExpectancyComparison,
    reference_risk_fraction: float = CANONICAL_RISK_FRACTION,
) -> ExpectancyComparisonResult:
    estimates = ExpectancyComparison(
        theoretical=monte_carlo.theoretical,
        sample=monte_carlo.sample,
        historical=historical.historical,
    )
    definitions = [
        estimate.risk_definition
        for estimate in (estimates.theoretical, estimates.sample, estimates.historical)
        if estimate is not None
    ]
    compatibility = _risk_compatibility(definitions, reference_risk_fraction)

    if not compatibility.compatible:
        return ExpectancyComparisonResult(
            estimates=estimates,
            risk_compatibility=compatibility,
            deltas=ComparisonDeltas(),
            warnings=("risk_definitions_incompatible",),
        )

    canonical_estimates = _canonicalize_comparison(estimates, reference_risk_fraction)
    deltas = ComparisonDeltas(
        delta_theoretical_sample=_delta(canonical_estimates.theoretical, canonical_estimates.sample),
        delta_theoretical_historical=_delta(
            canonical_estimates.theoretical, canonical_estimates.historical
        ),
        delta_sample_historical=_delta(canonical_estimates.sample, canonical_estimates.historical),
    )
    warnings = () if compatibility.same_risk_definition else ("risk_definitions_converted",)
    return ExpectancyComparisonResult(
        estimates=canonical_estimates,
        risk_compatibility=compatibility,
        deltas=deltas,
        warnings=warnings,
    )


def _canonicalize_comparison(
    estimates: ExpectancyComparison, reference_risk_fraction: float
) -> ExpectancyComparison:
    return ExpectancyComparison(
        theoretical=(
            canonicalize_estimate(estimates.theoretical, reference_risk_fraction)
            if estimates.theoretical
            else None
        ),
        sample=(
            canonicalize_estimate(estimates.sample, reference_risk_fraction)
            if estimates.sample
            else None
        ),
        historical=(
            canonicalize_estimate(estimates.historical, reference_risk_fraction)
            if estimates.historical
            else None
        ),
    )


def _risk_compatibility(
    definitions: list[RiskDefinition], reference_risk_fraction: float
) -> RiskCompatibility:
    if reference_risk_fraction <= 0.0:
        raise InvalidModelParametersError("reference_risk_fraction must be > 0")
    if not definitions:
        return RiskCompatibility(
            compatible=False,
            same_risk_definition=False,
            reference_risk_fraction=reference_risk_fraction,
            mismatches=("missing_risk_definition",),
        )

    mismatches: list[str] = []
    first = definitions[0]
    for definition in definitions[1:]:
        for field_name in ("unit", "normalization_version", "cost_basis"):
            if getattr(first, field_name) != getattr(definition, field_name):
                mismatches.append(field_name)
        if first.method != definition.method:
            mismatches.append("method")
        if not isclose(
            first.risk_unit_fraction,
            definition.risk_unit_fraction,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            mismatches.append("risk_unit_fraction")

    compatible = (
        all(definition.unit == "R" for definition in definitions)
        and all(definition.normalization_version == RISK_NORMALIZATION_VERSION for definition in definitions)
        and all(definition.cost_basis == "gross_r" for definition in definitions)
        and all(definition.method in SUPPORTED_RISK_METHODS for definition in definitions)
        and all(definition.risk_unit_fraction > 0.0 for definition in definitions)
    )
    return RiskCompatibility(
        compatible=compatible,
        same_risk_definition=not mismatches,
        reference_risk_fraction=reference_risk_fraction,
        mismatches=tuple(sorted(set(mismatches))),
    )


def _delta(first: ExpectancyEstimate | None, second: ExpectancyEstimate | None) -> float | None:
    if first is None or second is None:
        return None
    if first.canonical_value is None or second.canonical_value is None:
        return None
    return first.canonical_value - second.canonical_value


def compare_train_test_expectancy(
    train: ExpectancyEstimate,
    test: ExpectancyEstimate,
    reference_risk_fraction: float = CANONICAL_RISK_FRACTION,
) -> OutOfSampleComparisonResult:
    """Compare two historical-backtest expectancy estimates from disjoint time
    windows of the same strategy/spec (Фаза 20).

    The Out-of-Sample analogue of `compare_expectancy`: same risk-compatibility
    check and canonicalization, generalized from фиксированных "theoretical/
    sample vs historical" source roles to two arbitrary same-kind estimates.
    """
    compatibility = _risk_compatibility(
        [train.risk_definition, test.risk_definition], reference_risk_fraction
    )
    if not compatibility.compatible:
        return OutOfSampleComparisonResult(
            train=train,
            test=test,
            risk_compatibility=compatibility,
            delta_train_test=None,
            warnings=("risk_definitions_incompatible",),
        )

    train_canonical = canonicalize_estimate(train, reference_risk_fraction)
    test_canonical = canonicalize_estimate(test, reference_risk_fraction)
    warnings = () if compatibility.same_risk_definition else ("risk_definitions_converted",)
    return OutOfSampleComparisonResult(
        train=train_canonical,
        test=test_canonical,
        risk_compatibility=compatibility,
        delta_train_test=_delta(train_canonical, test_canonical),
        warnings=warnings,
    )
