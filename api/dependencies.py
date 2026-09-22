"""FastAPI dependency wiring: DB engine + repository.

`get_engine` is overridden wholesale in tests via
`app.dependency_overrides[get_engine]`, so the cache here only matters for
the real running process (one engine per process, not per request).
"""

import os
from functools import lru_cache

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from vectorx.storage.postgres.repository import PostgresExperimentRepository


@lru_cache
def get_engine() -> Engine:
    db_url = os.environ.get("VECTORX_DATABASE_URL")
    if not db_url:
        raise RuntimeError("VECTORX_DATABASE_URL is not set; the API requires PostgreSQL.")
    return create_engine(db_url)


def get_repository(engine: Engine = Depends(get_engine)) -> PostgresExperimentRepository:
    return PostgresExperimentRepository(engine)
