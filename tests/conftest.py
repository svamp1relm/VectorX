"""Session-scoped ephemeral PostgreSQL cluster for integration tests.

Shared across `tests/storage/` and `tests/` (CLI) — both need a real,
disposable Postgres. Spins up a local `initdb`/`pg_ctl` cluster (no Docker,
no root), applies the real Alembic migrations against it, and tears it down
at the end of the session. If `initdb`/`pg_ctl` aren't on PATH, integration
tests are skipped rather than failing the whole suite.
"""

import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def postgres_url(tmp_path_factory: pytest.TempPathFactory):
    initdb = shutil.which("initdb")
    pg_ctl = shutil.which("pg_ctl")
    if not initdb or not pg_ctl:
        pytest.skip("initdb/pg_ctl not on PATH: skipping Postgres integration tests")

    data_dir = tmp_path_factory.mktemp("vectorx_pg")
    port = _free_tcp_port()

    subprocess.run(
        [initdb, "-D", str(data_dir), "-U", "vectorx", "--auth=trust", "-E", "UTF8"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            pg_ctl,
            "-D",
            str(data_dir),
            "-o",
            f"-p {port} -k {data_dir}",
            "-l",
            str(data_dir / "server.log"),
            "-w",
            "start",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    db_url = f"postgresql+psycopg://vectorx@localhost:{port}/postgres"
    os.environ["VECTORX_DATABASE_URL"] = db_url
    try:
        alembic_cfg = Config(str(_REPO_ROOT / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(_REPO_ROOT / "alembic"))
        command.upgrade(alembic_cfg, "head")
        yield db_url
    finally:
        os.environ.pop("VECTORX_DATABASE_URL", None)
        subprocess.run(
            [pg_ctl, "-D", str(data_dir), "stop", "-m", "fast"],
            check=False,
            capture_output=True,
        )


@pytest.fixture(scope="session")
def postgres_engine(postgres_url: str) -> Engine:
    engine = create_engine(postgres_url)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_postgres_engine(postgres_engine: Engine) -> Engine:
    """Truncate all tables before each test so tests don't see each other's rows."""
    with postgres_engine.begin() as conn:
        conn.exec_driver_sql(
            "TRUNCATE TABLE runs, experiments, experiment_batches RESTART IDENTITY CASCADE"
        )
    return postgres_engine
