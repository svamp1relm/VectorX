"""Experiment and source-code version metadata for reproducibility."""

import hashlib
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

EXPERIMENT_VERSION = 2
_SOURCE_SUFFIXES = {".py", ".ts", ".vue", ".toml", ".yaml", ".yml"}
_EXCLUDED_DIRS = {".git", ".venv", "node_modules", "dist", "__pycache__"}


def get_code_version(start: Path | None = None) -> str:
    """Return HEAD plus a hash of the actual source inputs, including dirty changes."""
    start = start or Path.cwd()
    git_dir = _find_git_dir(start)
    if git_dir is None:
        return "unknown"

    head = _read_text_best_effort(git_dir / "HEAD")
    if head is None:
        return "unknown"
    if head.startswith("ref:"):
        ref_path = git_dir / head.removeprefix("ref:").strip()
        commit = _read_text_best_effort(ref_path)
    else:
        commit = head
    if not commit:
        return "unknown"

    source_hash = _source_digest(git_dir.parent)
    return f"{commit}+source-{source_hash}"


def _source_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in _EXCLUDED_DIRS)
        for filename in sorted(filenames):
            path = Path(directory) / filename
            if path.suffix not in _SOURCE_SUFFIXES:
                continue
            try:
                relative = path.relative_to(root).as_posix().encode()
                content = path.read_bytes()
            except OSError as exc:
                logger.warning("could not hash source file %s: %s", path, exc)
                continue
            digest.update(relative)
            digest.update(b"\0")
            digest.update(content)
            digest.update(b"\0")
    return digest.hexdigest()[:16]


def _read_text_best_effort(path: Path) -> str | None:
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
