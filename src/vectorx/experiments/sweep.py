"""SweepSpec/generate_sweep_specs: one research hypothesis x parameter grid
-> N concrete `ExperimentSpec` (Фаза 18c).

A pure function: no execution (`run_experiment` is reused unchanged for
each generated spec) and no storage. Every generated spec forces
`storage.store_trades=true` — batch experiments always keep raw trades,
since the statistical toolkit (Фаза 19) and robustness/OOS (Фазы 20-21)
cannot work on a batch without them.
"""

from itertools import product
from typing import Any

from pydantic import BaseModel, ConfigDict

from vectorx.core.errors import ExperimentTooLargeError
from vectorx.experiments.spec import ExperimentSpec, parse_experiment_spec

MAX_BATCH_EXPERIMENTS = 100
"""Resource guard on the number of ExperimentSpec one sweep may generate."""


class SweepSpec(BaseModel):
    """One research hypothesis: a base spec payload plus a parameter grid.

    `base` is a raw dict in the same shape as an `ExperimentSpec` YAML/JSON
    payload; `grid` maps dotted field paths (e.g. `"strategy.fast_period"`)
    to the list of values to sweep over. The cartesian product of `grid`'s
    values, applied on top of `base`, is what `generate_sweep_specs` expands.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    hypothesis: str
    notes: str | None = None
    base: dict[str, Any]
    grid: dict[str, list[Any]] = {}


def _set_dotted(payload: dict[str, Any], dotted_key: str, value: Any) -> dict[str, Any]:
    """Return a copy of `payload` with `dotted_key` (e.g. "a.b.c") overridden."""
    result = dict(payload)
    *parents, leaf = dotted_key.split(".")
    cursor = result
    for part in parents:
        cursor[part] = dict(cursor.get(part, {}))
        cursor = cursor[part]
    cursor[leaf] = value
    return result


def generate_sweep_specs(sweep: SweepSpec) -> tuple[ExperimentSpec, ...]:
    """Expand `sweep.grid`'s cartesian product over `sweep.base` into concrete specs."""
    keys = list(sweep.grid.keys())
    value_lists = [sweep.grid[key] for key in keys]
    combinations = list(product(*value_lists)) if keys else [()]

    if len(combinations) > MAX_BATCH_EXPERIMENTS:
        raise ExperimentTooLargeError(
            f"sweep would generate {len(combinations)} experiments, exceeding the "
            f"limit of {MAX_BATCH_EXPERIMENTS}"
        )

    base_name = sweep.base.get("name", sweep.hypothesis)
    specs = []
    for index, combo in enumerate(combinations):
        payload = dict(sweep.base)
        for key, value in zip(keys, combo, strict=True):
            payload = _set_dotted(payload, key, value)
        payload = _set_dotted(payload, "name", f"{base_name}_{index}")
        payload = _set_dotted(payload, "storage.store_trades", True)
        specs.append(parse_experiment_spec(payload))

    return tuple(specs)
