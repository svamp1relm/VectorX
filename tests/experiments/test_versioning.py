"""Experiment/code version metadata: locked histogram schema + best-effort git SHA."""

import re

from vectorx.experiments.versioning import EXPERIMENT_VERSION, get_code_version

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def test_experiment_version_is_locked_to_one():
    assert EXPERIMENT_VERSION == 1


def test_get_code_version_returns_sha_or_unknown():
    result = get_code_version()

    assert result == "unknown" or _SHA_RE.fullmatch(result)


def test_get_code_version_falls_back_to_unknown_outside_a_repo(tmp_path):
    assert get_code_version(start=tmp_path) == "unknown"
