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
