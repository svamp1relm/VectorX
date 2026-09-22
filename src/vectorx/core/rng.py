"""Reproducible, run-scoped random number generation.

Each run gets its own `numpy.random.Generator`, derived from the experiment
seed and the run index via `SeedSequence` (not a naive `seed + run_index`
sum, which risks correlated streams). Same (experiment_seed, run_index)
always reproduces the same stream; different run_index or experiment_seed
diverges.
"""

import numpy as np


def derived_rng(experiment_seed: int, run_index: int) -> np.random.Generator:
    """Build the RNG for one run of an experiment."""
    seed_sequence = np.random.SeedSequence([experiment_seed, run_index])
    return np.random.default_rng(seed_sequence)


def derived_seed_value(experiment_seed: int, run_index: int) -> int:
    """A single reproducible integer identifying this run's seed, for metadata.

    Built from a fresh `SeedSequence` with the same entropy as `derived_rng`,
    so it never advances the state of the actual per-run generator.
    """
    seed_sequence = np.random.SeedSequence([experiment_seed, run_index])
    return int(seed_sequence.generate_state(1)[0])
