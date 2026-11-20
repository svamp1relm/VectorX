"""FastAPI application assembly, middleware, and domain error handling."""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import batches, experiments, robustness
from vectorx.core.errors import VectorXError

app = FastAPI(title="VectorX API")

_default_cors_origins = "http://localhost:5173,http://127.0.0.1:5173"
_cors_origins = [
    origin.strip()
    for origin in os.environ.get("VECTORX_CORS_ORIGINS", _default_cors_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(VectorXError)
async def domain_error_handler(_request: Request, exc: VectorXError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(experiments.router)
app.include_router(batches.router)
app.include_router(robustness.router)
