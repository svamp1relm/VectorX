"""Thin FastAPI layer: create/list/detail/results/run-detail/equity, all
backed by the same run_experiment + PostgresExperimentRepository as CLI.
No auth, no websocket, no job queue. Operations-limit violations -> 400.
"""

import pytest
from api.dependencies import get_engine
from api.main import app
from fastapi.testclient import TestClient

VALID_SPEC = {
    "name": "expectancy_test",
    "seed": 42,
    "runs": 5,
    "model": {"p_win": 0.55, "win_r": 2.0, "loss_r": -1.0, "n_trades": 20},
    "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
}


@pytest.fixture
def client(clean_postgres_engine):
    app.dependency_overrides[get_engine] = lambda: clean_postgres_engine
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_experiment_returns_201_with_id(client):
    response = client.post("/experiments", json=VALID_SPEC)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "expectancy_test"
    assert body["runs"] == 5
    assert "summary" in body
    assert "spec" in body


def test_get_experiment_returns_created_one(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    response = client.get(f"/experiments/{created['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "expectancy_test"


def test_get_unknown_experiment_returns_404(client):
    response = client.get("/experiments/999999")

    assert response.status_code == 404


def test_list_experiments_includes_created_one(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    response = client.get("/experiments")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert created["id"] in ids


def test_results_endpoint_has_metrics_but_not_equity(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    response = client.get(f"/experiments/{created['id']}/results")

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 5
    assert "metrics" in results[0]
    assert "equity_curve" not in results[0]


def test_run_detail_endpoint_has_equity_curve(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    response = client.get(f"/experiments/{created['id']}/runs/0")

    assert response.status_code == 200
    body = response.json()
    assert body["run_index"] == 0
    assert len(body["equity_curve"]) > 0


def test_run_detail_unknown_run_id_returns_404(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    response = client.get(f"/experiments/{created['id']}/runs/999")

    assert response.status_code == 404


def test_equity_endpoint_defaults_to_run_zero(client):
    created = client.post("/experiments", json=VALID_SPEC).json()
    run_detail = client.get(f"/experiments/{created['id']}/runs/0").json()

    response = client.get(f"/experiments/{created['id']}/equity")

    assert response.status_code == 200
    assert response.json() == run_detail["equity_curve"]


def test_equity_endpoint_accepts_run_id_query_param(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    response = client.get(f"/experiments/{created['id']}/equity", params={"run_id": 1})

    assert response.status_code == 200
    assert len(response.json()) > 0


def test_rerun_endpoint_creates_new_experiment_reproducibly(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    rerun = client.post(f"/experiments/{created['id']}/run")

    assert rerun.status_code == 201
    rerun_body = rerun.json()
    assert rerun_body["id"] != created["id"]
    assert rerun_body["summary"] == created["summary"]


def test_rerun_unknown_experiment_returns_404(client):
    response = client.post("/experiments/999999/run")

    assert response.status_code == 404


def test_operations_limit_returns_400(client):
    oversized_spec = {
        **VALID_SPEC,
        "runs": 3,
        "model": {**VALID_SPEC["model"], "n_trades": 1_000_000},
    }

    response = client.post("/experiments", json=oversized_spec)

    assert response.status_code == 400


def test_infinite_profit_factor_is_json_safe(client):
    all_wins_spec = {
        **VALID_SPEC,
        "runs": 1,
        "model": {"p_win": 1.0, "win_r": 2.0, "loss_r": -1.0, "n_trades": 10},
    }

    created = client.post("/experiments", json=all_wins_spec).json()
    response = client.get(f"/experiments/{created['id']}/results")

    assert response.status_code == 200
    assert response.json()[0]["metrics"]["profit_factor"] == "Infinity"


def test_cors_allows_the_vite_dev_server_origin(client):
    response = client.get("/experiments", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def _write_csv(tmp_path, closes):
    from datetime import UTC, datetime, timedelta

    start = datetime(2024, 1, 1, tzinfo=UTC)
    path = tmp_path / "candles.csv"
    lines = ["timestamp,open,high,low,close,volume"]
    for i, close in enumerate(closes):
        ts = (start + timedelta(hours=i)).isoformat()
        lines.append(f"{ts},{close},{close},{close},{close},1000.0")
    path.write_text("\n".join(lines) + "\n")
    return path


def test_create_historical_backtest_experiment_via_same_endpoint(client, tmp_path):
    # The same /experiments endpoint handles both spec types (Фаза 16a decision):
    # no dedicated historical-only route exists.
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    csv_path = _write_csv(tmp_path, closes)
    historical_spec = {
        "type": "historical_backtest",
        "name": "ma_crossover_api_test",
        "data": {"path": str(csv_path), "symbol": "BTCUSDT", "timeframe": "1h"},
        "strategy": {"fast_period": 2, "slow_period": 4, "stop_loss_pct": 0.01},
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
    }

    response = client.post("/experiments", json=historical_spec)

    assert response.status_code == 201
    body = response.json()
    assert body["runs"] == 1
    assert body["spec"]["type"] == "historical_backtest"

    results = client.get(f"/experiments/{body['id']}/results").json()
    assert results[0]["metrics"]["expectancy_theoretical"] is None


def test_compare_expectancy_endpoint_converts_risk_units(client, tmp_path):
    monte_carlo_spec = {
        **VALID_SPEC,
        "name": "mc_comparison",
        "runs": 1,
        "model": {
            **VALID_SPEC["model"],
            "n_trades": 10,
            "risk_unit_fraction": 0.01,
        },
    }
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    historical_spec = {
        "type": "historical_backtest",
        "name": "historical_comparison",
        "data": {
            "path": str(_write_csv(tmp_path, closes)),
            "symbol": "BTCUSDT",
            "timeframe": "1h",
        },
        "strategy": {"fast_period": 2, "slow_period": 4, "stop_loss_pct": 0.02},
        "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.01},
    }
    monte_carlo = client.post("/experiments", json=monte_carlo_spec).json()
    historical = client.post("/experiments", json=historical_spec).json()

    response = client.post(
        "/comparisons/expectancy",
        json={
            "monte_carlo_experiment_id": monte_carlo["id"],
            "historical_experiment_id": historical["id"],
            "reference_risk_fraction": 0.01,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["risk_compatibility"]["compatible"] is True
    assert body["risk_compatibility"]["same_risk_definition"] is False
    assert body["estimates"]["historical"]["canonical_value"] is not None
    assert body["deltas"]["delta_sample_historical"] is not None
    assert "risk_definitions_converted" in body["warnings"]


def test_create_batch_generates_and_saves_every_sweep_experiment(client):
    sweep = {
        "hypothesis": "p_win sensitivity",
        "notes": "first sweep",
        "base": VALID_SPEC,
        "grid": {"model.p_win": [0.5, 0.55, 0.6]},
    }

    response = client.post("/batches", json=sweep)

    assert response.status_code == 201
    body = response.json()
    assert body["hypothesis"] == "p_win sensitivity"
    assert body["notes"] == "first sweep"
    assert len(body["experiments"]) == 3
    for experiment in body["experiments"]:
        assert experiment["status"] == "completed"


def test_get_batch_returns_created_one(client):
    sweep = {"hypothesis": "h", "base": VALID_SPEC, "grid": {"model.p_win": [0.5, 0.6]}}
    created = client.post("/batches", json=sweep).json()

    response = client.get(f"/batches/{created['id']}")

    assert response.status_code == 200
    assert response.json()["hypothesis"] == "h"
    assert len(response.json()["experiments"]) == 2


def test_get_unknown_batch_returns_404(client):
    response = client.get("/batches/999999")

    assert response.status_code == 404


def test_list_batches_includes_created_one(client):
    sweep = {"hypothesis": "h", "base": VALID_SPEC, "grid": {}}
    created = client.post("/batches", json=sweep).json()

    response = client.get("/batches")

    assert response.status_code == 200
    ids = [batch["id"] for batch in response.json()]
    assert created["id"] in ids
    listed = next(batch for batch in response.json() if batch["id"] == created["id"])
    assert listed["experiment_count"] == 1


def test_create_batch_over_resource_guard_returns_400(client):
    from vectorx.experiments.sweep import MAX_BATCH_EXPERIMENTS

    sweep = {
        "hypothesis": "too big",
        "base": VALID_SPEC,
        "grid": {"seed": list(range(MAX_BATCH_EXPERIMENTS + 1))},
    }

    response = client.post("/batches", json=sweep)

    assert response.status_code == 400


def test_analysis_endpoint_returns_ci_and_risk_adjusted_metrics(client):
    spec = {**VALID_SPEC, "storage": {"store_trades": True}}
    created = client.post("/experiments", json=spec).json()

    response = client.get(f"/experiments/{created['id']}/analysis")

    assert response.status_code == 200
    body = response.json()
    assert "analysis_version" in body
    assert body["confidence_interval"]["lower"] <= body["confidence_interval"]["point_estimate"]
    assert body["confidence_interval"]["point_estimate"] <= body["confidence_interval"]["upper"]
    assert "sharpe" in body["risk_adjusted"]
    assert "significant" in body["significance_vs_zero"]


def test_analysis_endpoint_is_deterministic_for_same_seed_query_param(client):
    spec = {**VALID_SPEC, "storage": {"store_trades": True}}
    created = client.post("/experiments", json=spec).json()

    response_a = client.get(f"/experiments/{created['id']}/analysis?seed=7")
    response_b = client.get(f"/experiments/{created['id']}/analysis?seed=7")

    assert response_a.json() == response_b.json()


def test_analysis_endpoint_returns_400_when_trades_were_not_stored(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    response = client.get(f"/experiments/{created['id']}/analysis")

    assert response.status_code == 400


def test_analysis_endpoint_returns_404_for_unknown_experiment(client):
    response = client.get("/experiments/999999/analysis")

    assert response.status_code == 404


def test_out_of_sample_endpoint_returns_train_test_and_comparison(client, tmp_path):
    closes = [100.0 + i * 5.0 for i in range(10)] + [150.0 - i * 5.0 for i in range(1, 11)]
    csv_path = _write_csv(tmp_path, closes)
    payload = {
        "base": {
            "type": "historical_backtest",
            "name": "oos_api_test",
            "data": {"path": str(csv_path), "symbol": "BTCUSDT", "timeframe": "1h"},
            "strategy": {"type": "buy_and_hold", "stop_loss_pct": 1.0},
            "portfolio": {"initial_capital": 10_000.0, "risk_per_trade": 0.1},
        },
        "train_start": "2024-01-01T00:00:00+00:00",
        "train_end": "2024-01-01T09:00:00+00:00",
        "test_start": "2024-01-01T10:00:00+00:00",
        "test_end": "2024-01-01T19:00:00+00:00",
    }

    response = client.post("/out-of-sample", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["train"]["spec"]["type"] == "historical_backtest"
    assert body["test"]["spec"]["type"] == "historical_backtest"
    assert "delta_train_test" in body["comparison"]


def test_export_endpoint_returns_byte_identical_json_across_two_calls(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    response_a = client.get(f"/experiments/{created['id']}/export")
    response_b = client.get(f"/experiments/{created['id']}/export")

    assert response_a.status_code == 200
    assert response_a.content == response_b.content
    body = response_a.json()
    assert body["seed"] == VALID_SPEC["seed"]
    assert body["hypothesis"] is None


def test_export_endpoint_markdown_format_includes_name_and_provenance(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    response = client.get(f"/experiments/{created['id']}/export?format=markdown")

    assert response.status_code == 200
    assert "expectancy_test" in response.text
    assert "code_version" in response.text


def test_export_endpoint_includes_hypothesis_when_experiment_is_in_a_batch(client):
    sweep = {"hypothesis": "export sensitivity", "base": VALID_SPEC, "grid": {}}
    batch = client.post("/batches", json=sweep).json()
    experiment_id = batch["experiments"][0]["id"]

    response = client.get(f"/experiments/{experiment_id}/export")

    assert response.json()["hypothesis"] == "export sensitivity"


def test_export_endpoint_rejects_unsupported_format(client):
    created = client.post("/experiments", json=VALID_SPEC).json()

    response = client.get(f"/experiments/{created['id']}/export?format=xml")

    assert response.status_code == 400


def test_export_endpoint_returns_404_for_unknown_experiment(client):
    response = client.get("/experiments/999999/export")

    assert response.status_code == 404
