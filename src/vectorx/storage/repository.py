"""ExperimentRepository: the storage-agnostic contract the runner's output
persists through. This module must never import SQLAlchemy — concrete
backends (Postgres) live in `vectorx.storage.postgres` behind the `[postgres]`
extra, so unit tests of the rest of the library never need a database.
"""

from typing import Protocol, runtime_checkable

from vectorx.experiments.runner import ExperimentResult


@runtime_checkable
class ExperimentRepository(Protocol):
    """Persists and reconstructs `ExperimentResult`s."""

    def save_experiment(self, result: ExperimentResult) -> int:
        """Persist a completed experiment result, returning its assigned id."""
        ...

    def get_experiment(self, experiment_id: int) -> ExperimentResult | None:
        """Reconstruct a previously saved experiment result, or None if absent."""
        ...

    def list_experiment_ids(self) -> tuple[int, ...]:
        """Return all stored experiment ids, in insertion order."""
        ...

