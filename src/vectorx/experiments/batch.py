"""ExperimentBatch: groups many ExperimentSpec runs under one research
hypothesis (Фаза 18c). A pure data container — `vectorx.storage` fills it
in, `vectorx.experiments` does not depend on storage.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ExperimentBatch:
    """One saved batch: its hypothesis/notes plus the experiment ids it contains."""

    id: int
    hypothesis: str
    notes: str | None
    created_at: datetime
    experiment_ids: tuple[int, ...]
