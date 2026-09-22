"""Experiment/code version metadata for reproducibility.

`EXPERIMENT_VERSION` gates the spec schema and the statistics algorithms it
implies (see `vectorx.statistics.histogram`'s locked bin algorithm); bump it
whenever either changes. `get_code_version` is best-effort: it reads the git
working tree's current commit by walking the filesystem (no `git` binary
invocation, no subprocess), falling back to `"unknown"` when no repository
or commit is found.
"""

from pathlib import Path

EXPERIMENT_VERSION = 1


def get_code_version(start: Path | None = None) -> str:
    """Return the current commit SHA of the repo containing `start`, or "unknown"."""
    git_dir = _find_git_dir(start or Path.cwd())
    if git_dir is None:
        return "unknown"

    try:
        head = (git_dir / "HEAD").read_text().strip()
    except OSError:
        return "unknown"

    if not head.startswith("ref:"):
        return head or "unknown"

    ref_path = git_dir / head.removeprefix("ref:").strip()
    try:
        return ref_path.read_text().strip() or "unknown"
    except OSError:
        return "unknown"


def _find_git_dir(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        git_dir = candidate / ".git"
        if git_dir.is_dir():
            return git_dir
    return None
