"""render_json_report/render_markdown_report: reproducible export (Фаза 24).

"Byte-identical across two independent runs" is the phase's own acceptance
criterion — these tests assert exact string equality, not just structural
equality, to actually prove that.
"""

import json
from datetime import UTC, datetime

from vectorx.experiments.batch import ExperimentBatch
from vectorx.experiments.export import render_json_report, render_markdown_report
from vectorx.experiments.runner import run_experiment
from vectorx.experiments.spec import parse_experiment_spec
from vectorx.statistics.versioning import ANALYSIS_VERSION


def _spec(**overrides):
    payload = {
        "name": "export_test",
        "seed": 42,
        "runs": 3,
        "model": {"p_win": 0.55, "win_r": 2.0, "loss_r": -1.0, "n_trades": 10},
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
    }
    payload.update(overrides)
    return parse_experiment_spec(payload)


def _batch() -> ExperimentBatch:
    return ExperimentBatch(
        id=1,
        hypothesis="p_win sensitivity",
        notes="first sweep",
        created_at=datetime(2026, 10, 2, tzinfo=UTC),
        experiment_ids=(1,),
    )


def test_json_report_is_byte_identical_across_two_independent_calls():
    result = run_experiment(_spec())

    report_a = render_json_report(result)
    report_b = render_json_report(result)

    assert report_a == report_b


def test_markdown_report_is_byte_identical_across_two_independent_calls():
    result = run_experiment(_spec())

    report_a = render_markdown_report(result)
    report_b = render_markdown_report(result)

    assert report_a == report_b


def test_json_report_includes_all_required_provenance_fields():
    result = run_experiment(_spec())

    report = json.loads(render_json_report(result))

    assert report["seed"] == result.seed
    assert report["code_version"] == result.code_version
    assert report["data_version"] == result.data_version
    assert report["experiment_version"] == result.experiment_version
    assert report["analysis_version"] == ANALYSIS_VERSION
    assert report["spec"] == result.spec.model_dump(mode="json")
    assert report["hypothesis"] is None
    assert report["notes"] is None


def test_json_report_includes_hypothesis_and_notes_when_batch_given():
    result = run_experiment(_spec())

    report = json.loads(render_json_report(result, batch=_batch()))

    assert report["hypothesis"] == "p_win sensitivity"
    assert report["notes"] == "first sweep"


def test_markdown_report_includes_spec_and_hypothesis():
    result = run_experiment(_spec())

    report = render_markdown_report(result, batch=_batch())

    assert "export_test" in report
    assert "p_win sensitivity" in report
    assert "first sweep" in report
    assert str(ANALYSIS_VERSION) in report
