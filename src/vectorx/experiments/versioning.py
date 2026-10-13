"""Experiment/code version metadata for reproducibility.

`EXPERIMENT_VERSION` gates the spec schema and the statistics algorithms it
implies (see `vectorx.statistics.histogram`'s locked bin algorithm); bump it
whenever either changes. `get_code_version` is best-effort: it reads the git
working tree's current commit by walking the filesystem (no `git` binary
invocation, no subprocess), falling back to `"unknown"` when no repository
or commit is found.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

EXPERIMENT_VERSION = 1


def get_code_version(start: Path | None = None) -> str:
    """Return the current commit SHA of the repo containing `start`, or "unknown"."""
    git_dir = _find_git_dir(start or Path.cwd())
    if git_dir is None:
        return "unknown"

    head = _read_text_best_effort(git_dir / "HEAD")
    if head is None:
        return "unknown"

    if not head.startswith("ref:"):
        return head or "unknown"

    ref_path = git_dir / head.removeprefix("ref:").strip()
    return _read_text_best_effort(ref_path) or "unknown"


def _read_text_best_effort(path: Path) -> str | None:
    """Read `path`, logging (not swallowing) anything other than "doesn't exist"."""
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        logger.warning("could not read %s for code_version: %s", path, exc)
        return None


def _find_git_dir(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        git_dir = candidate / ".git"
        if git_dir.is_dir():
            return git_dir
    return None
