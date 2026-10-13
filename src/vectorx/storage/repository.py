"""ExperimentRepository: the storage-agnostic contract the runner's output
persists through. This module must never import SQLAlchemy — concrete
backends (Postgres) live in `vectorx.storage.postgres` behind the `[postgres]`
extra, so unit tests of the rest of the library never need a database.
"""

from typing import Protocol, runtime_checkable

from vectorx.experiments.batch import ExperimentBatch
from vectorx.experiments.runner import ExperimentResult


@runtime_checkable
class ExperimentRepository(Protocol):
    """Persists and reconstructs `ExperimentResult`s (and `ExperimentBatch`es)."""

    def save_experiment(self, result: ExperimentResult, batch_id: int | None = None) -> int:
        """Persist a completed experiment result, returning its assigned id."""
        ...

    def get_experiment(self, experiment_id: int) -> ExperimentResult | None:
        """Reconstruct a previously saved experiment result, or None if absent."""
        ...

    def list_experiment_ids(self) -> tuple[int, ...]:
        """Return all stored experiment ids, in insertion order."""
        ...

    def save_batch(self, hypothesis: str, notes: str | None = None) -> int:
        """Persist a new experiment batch, returning its assigned id."""
        ...

    def get_batch(self, batch_id: int) -> ExperimentBatch | None:
        """Reconstruct a previously saved batch (with its experiment ids), or None."""
        ...

    def list_batch_ids(self) -> tuple[int, ...]:
        """Return all stored batch ids, in insertion order."""
        ...

    def get_batch_id_for_experiment(self, experiment_id: int) -> int | None:
        """The batch an experiment belongs to, or `None` if it isn't in one."""
        ...

