"""Derived per-run RNG: reproducible within a run, independent across runs."""

import numpy as np

from vectorx.core.rng import derived_rng, derived_seed_value


def test_same_seed_and_run_index_reproduce_identical_sequence():
    rng_a = derived_rng(experiment_seed=42, run_index=0)
    rng_b = derived_rng(experiment_seed=42, run_index=0)

    assert np.array_equal(rng_a.random(50), rng_b.random(50))


def test_different_run_index_diverges():
    rng_a = derived_rng(experiment_seed=42, run_index=0)
    rng_b = derived_rng(experiment_seed=42, run_index=1)

    assert not np.array_equal(rng_a.random(50), rng_b.random(50))


def test_different_experiment_seed_diverges():
    rng_a = derived_rng(experiment_seed=42, run_index=0)
    rng_b = derived_rng(experiment_seed=43, run_index=0)

    assert not np.array_equal(rng_a.random(50), rng_b.random(50))


def test_derived_rng_returns_numpy_generator():
    rng = derived_rng(experiment_seed=1, run_index=0)

    assert isinstance(rng, np.random.Generator)


def test_derived_seed_value_is_deterministic():
    assert derived_seed_value(42, 0) == derived_seed_value(42, 0)


def test_derived_seed_value_differs_by_run_index():
    assert derived_seed_value(42, 0) != derived_seed_value(42, 1)


def test_derived_seed_value_is_plain_int():
    assert isinstance(derived_seed_value(42, 0), int)
