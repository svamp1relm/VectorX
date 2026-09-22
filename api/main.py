"""FastAPI routes. Handlers stay thin: validation is `ExperimentSpec`
(pydantic, reused as-is from `vectorx.experiments.spec`), execution is
`run_experiment`, persistence is `PostgresExperimentRepository` — no
business logic lives here. No auth, no websocket, no job queue.
"""

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.dependencies import get_repository
from api.serialization import (
    equity_curve_to_dicts,
    experiment_detail_to_dict,
    experiment_summary_to_dict,
    run_result_to_dict,
)
from vectorx.core.errors import VectorXError
from vectorx.experiments.runner import run_experiment
from vectorx.experiments.spec import ExperimentSpec
from vectorx.storage.postgres.repository import PostgresExperimentRepository

app = FastAPI(title="VectorX API")

# The Vue dashboard (web/) is served from Vite's dev server on a different
# origin/port than the API, so the browser needs CORS to allow it through.
# No auth exists yet (plan: no auth in MVP), so a permissive origin list
# doesn't weaken anything that isn't already unauthenticated.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(VectorXError)
async def domain_error_handler(_request: Request, exc: VectorXError) -> JSONResponse:
    # Covers ExperimentTooLargeError (plan: over the operations limit -> 400)
    # and any other domain validation failure: all are the client's fault.
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def _get_experiment_or_404(
    experiment_id: int, repo: PostgresExperimentRepository
):
    result = repo.get_experiment(experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    return result


@app.post("/experiments", status_code=201)
def create_experiment(
    spec: ExperimentSpec, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    result = run_experiment(spec)
    experiment_id = repo.save_experiment(result)
    stored = _get_experiment_or_404(experiment_id, repo)
    return experiment_detail_to_dict(experiment_id, stored)


@app.post("/experiments/{experiment_id}/run", status_code=201)
def rerun_experiment(
    experiment_id: int, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    existing = _get_experiment_or_404(experiment_id, repo)
    result = run_experiment(existing.spec)
    new_id = repo.save_experiment(result)
    stored = _get_experiment_or_404(new_id, repo)
    return experiment_detail_to_dict(new_id, stored)


@app.get("/experiments")
def list_experiments(
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> list[dict]:
    return [
        experiment_summary_to_dict(experiment_id, repo.get_experiment(experiment_id))
        for experiment_id in repo.list_experiment_ids()
    ]


@app.get("/experiments/{experiment_id}")
def get_experiment(
    experiment_id: int, repo: PostgresExperimentRepository = Depends(get_repository)
) -> dict:
    result = _get_experiment_or_404(experiment_id, repo)
    return experiment_detail_to_dict(experiment_id, result)


@app.get("/experiments/{experiment_id}/results")
def get_experiment_results(
    experiment_id: int, repo: PostgresExperimentRepository = Depends(get_repository)
) -> list[dict]:
    result = _get_experiment_or_404(experiment_id, repo)
    return [run_result_to_dict(run, include_equity=False) for run in result.run_results]


def _find_run_or_404(result, run_id: int):
    for run in result.run_results:
        if run.run_index == run_id:
            return run
    raise HTTPException(status_code=404, detail="run not found")


@app.get("/experiments/{experiment_id}/runs/{run_id}")
def get_run(
    experiment_id: int,
    run_id: int,
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> dict:
    result = _get_experiment_or_404(experiment_id, repo)
    run = _find_run_or_404(result, run_id)
    return run_result_to_dict(run, include_equity=True)


@app.get("/experiments/{experiment_id}/equity")
def get_equity(
    experiment_id: int,
    run_id: int = 0,
    repo: PostgresExperimentRepository = Depends(get_repository),
) -> list[dict]:
    result = _get_experiment_or_404(experiment_id, repo)
    run = _find_run_or_404(result, run_id)
    return equity_curve_to_dicts(run.equity_curve)
