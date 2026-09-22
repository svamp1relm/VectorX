"""`vectorx run <config.yaml>` — the MVP CLI.

Runs an experiment without any API/UI and always persists it to PostgreSQL:
there is no in-memory/dry-run mode in the MVP, so a missing
`VECTORX_DATABASE_URL` or a missing `[postgres]` extra are both hard errors,
not silent fallbacks.
"""

import argparse
import os
import sys
from pathlib import Path

from vectorx.experiments.runner import run_experiment
from vectorx.experiments.spec import load_experiment_spec


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vectorx")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run an experiment from a YAML spec")
    run_parser.add_argument("config", type=Path, help="Path to the experiment YAML file")

    return parser


def _require_database_url() -> str:
    db_url = os.environ.get("VECTORX_DATABASE_URL")
    if not db_url:
        raise SystemExit(
            "VECTORX_DATABASE_URL is not set. The MVP CLI always persists to "
            "PostgreSQL — set VECTORX_DATABASE_URL "
            "(e.g. postgresql+psycopg://user@host/db) and try again."
        )
    return db_url


def _run_command(config_path: Path) -> int:
    db_url = _require_database_url()

    try:
        from sqlalchemy import create_engine

        from vectorx.storage.postgres.repository import PostgresExperimentRepository
    except ImportError as exc:
        print(
            "PostgreSQL support is not installed. Install it with: "
            "pip install -e '.[postgres]'",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    spec = load_experiment_spec(config_path)
    result = run_experiment(spec)

    engine = create_engine(db_url)
    try:
        experiment_id = PostgresExperimentRepository(engine).save_experiment(result)
    finally:
        engine.dispose()

    summary = result.summary
    print(f"experiment_id: {experiment_id}")
    print(f"name: {result.name}")
    print(f"seed: {result.seed}")
    print(f"runs: {result.runs}")
    print(f"status: {result.status}")
    print(f"duration: {result.duration:.3f}s")
    print(f"mean_total_return: {summary.mean_total_return:.6f}")
    print(f"median_total_return: {summary.median_total_return:.6f}")
    print(f"stdev_total_return: {summary.stdev_total_return:.6f}")
    print(f"p_negative: {summary.p_negative:.4f}")
    print(f"p_ruined: {summary.p_ruined:.4f}")

    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "run":
        return _run_command(args.config)

    raise SystemExit(f"unknown command: {args.command}")
