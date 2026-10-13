"""render_json_report/render_markdown_report: deterministic reproducibility
export (Фаза 24).

"Two independent runs of the export on the same saved experiment produce a
byte-identical report" is the phase's own acceptance criterion — so nothing
here may depend on wall-clock time or Python's dict/set iteration order.
`json.dumps(..., sort_keys=True)` makes key order deterministic regardless
of how `build_experiment_report`'s dict was constructed.

No storage import here on purpose: this module stays as storage-agnostic as
`vectorx.experiments.runner` itself, so it duplicates the small, JSON-safe
`ExperimentSummary` serializer rather than reaching into
`vectorx.storage.postgres.serializers` (a different package's internal
JSONB-shape helper, not a general-purpose export format).
"""

import json

from vectorx.core.types import ExpectancyComparison, ExpectancyEstimate, ExperimentSummary
from vectorx.experiments.batch import ExperimentBatch
from vectorx.experiments.runner import ExperimentResult
from vectorx.statistics.versioning import ANALYSIS_VERSION


def _expectancy_estimate_to_dict(value: ExpectancyEstimate) -> dict:
    return {
        "value": value.value,
        "canonical_value": value.canonical_value,
        "source": value.source,
        "unit": value.unit,
        "sample_size": value.sample_size,
        "planned_sample_size": value.planned_sample_size,
        "risk_definition": {
            "unit": value.risk_definition.unit,
            "normalization_version": value.risk_definition.normalization_version,
            "method": value.risk_definition.method,
            "risk_unit_fraction": value.risk_definition.risk_unit_fraction,
            "cost_basis": value.risk_definition.cost_basis,
        },
    }


def _expectancy_comparison_to_dict(value: ExpectancyComparison | None) -> dict | None:
    if value is None:
        return None
    return {
        "theoretical": (
            _expectancy_estimate_to_dict(value.theoretical) if value.theoretical else None
        ),
        "sample": _expectancy_estimate_to_dict(value.sample) if value.sample else None,
        "historical": (
            _expectancy_estimate_to_dict(value.historical) if value.historical else None
        ),
    }


def _summary_to_dict(summary: ExperimentSummary) -> dict:
    return {
        "runs": summary.runs,
        "mean_total_return": summary.mean_total_return,
        "median_total_return": summary.median_total_return,
        "stdev_total_return": summary.stdev_total_return,
        "p_negative": summary.p_negative,
        "p_ruined": summary.p_ruined,
        "total_return_histogram": {
            "edges": list(summary.total_return_histogram.edges),
            "counts": list(summary.total_return_histogram.counts),
        },
        "r_multiple_histogram": {
            "edges": list(summary.r_multiple_histogram.edges),
            "counts": list(summary.r_multiple_histogram.counts),
        },
        "expectancy": _expectancy_comparison_to_dict(summary.expectancy),
    }


def build_experiment_report(
    result: ExperimentResult, *, batch: ExperimentBatch | None = None
) -> dict:
    """Assemble the full reproducibility report as a plain, JSON-safe dict."""
    return {
        "name": result.name,
        "seed": result.seed,
        "runs": result.runs,
        "status": result.status,
        "created_at": result.created_at.isoformat(),
        "duration": result.duration,
        "code_version": result.code_version,
        "data_version": result.data_version,
        "experiment_version": result.experiment_version,
        "analysis_version": ANALYSIS_VERSION,
        "spec": result.spec.model_dump(mode="json"),
        "summary": _summary_to_dict(result.summary),
        "hypothesis": batch.hypothesis if batch is not None else None,
        "notes": batch.notes if batch is not None else None,
    }


def render_json_report(
    result: ExperimentResult, *, batch: ExperimentBatch | None = None
) -> str:
    """A deterministic JSON report: same input always gives byte-identical output."""
    report = build_experiment_report(result, batch=batch)
    return json.dumps(report, sort_keys=True, indent=2) + "\n"


def render_markdown_report(
    result: ExperimentResult, *, batch: ExperimentBatch | None = None
) -> str:
    """A deterministic Markdown report covering the same fields as the JSON report."""
    report = build_experiment_report(result, batch=batch)
    lines = [
        f"# Experiment report: {report['name']}",
        "",
        "## Provenance",
        f"- seed: {report['seed']}",
        f"- code_version: {report['code_version']}",
        f"- data_version: {report['data_version']}",
        f"- experiment_version: {report['experiment_version']}",
        f"- analysis_version: {report['analysis_version']}",
        f"- created_at: {report['created_at']}",
        f"- duration: {report['duration']}",
        f"- status: {report['status']}",
        f"- runs: {report['runs']}",
    ]
    if report["hypothesis"] is not None:
        lines += ["", "## Hypothesis", report["hypothesis"]]
    if report["notes"] is not None:
        lines += ["", "## Notes", report["notes"]]
    lines += [
        "",
        "## Spec",
        "```json",
        json.dumps(report["spec"], sort_keys=True, indent=2),
        "```",
        "",
        "## Summary",
        "```json",
        json.dumps(report["summary"], sort_keys=True, indent=2),
        "```",
        "",
    ]
    return "\n".join(lines)
