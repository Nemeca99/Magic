from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class PowerMode:
    power: int
    label: str
    description: str
    pool_fn: Callable[[], List[int]]


def _n1_pool() -> List[int]:
    # Fixed calibration set used by run_foundation_calibration (1..9).
    return list(range(1, 10))


def _n2_pool() -> List[int]:
    # Squares (30^2 to 80^2).
    return [i**2 for i in range(30, 81)]


def _n3_pool() -> List[int]:
    # Cubes (30^3 to 80^3).
    return [i**3 for i in range(30, 81)]


POWER_MODES: Dict[int, PowerMode] = {
    1: PowerMode(
        power=1,
        label="n=1",
        description="Baseline integers (1..9) — Foundation calibration set",
        pool_fn=_n1_pool,
    ),
    2: PowerMode(
        power=2,
        label="n=2",
        description="Squares (30^2 to 80^2)",
        pool_fn=_n2_pool,
    ),
    3: PowerMode(
        power=3,
        label="n=3",
        description="Cubes (30^3 to 80^3)",
        pool_fn=_n3_pool,
    ),
}


DEFAULT_POWER: int = 3


def get_power_mode(power: Optional[int] = None) -> PowerMode:
    """
    Resolve a PowerMode from the registry.

    Falls back to DEFAULT_POWER if an unknown or None power is requested.
    """
    if power is None:
        power = DEFAULT_POWER
    return POWER_MODES.get(power, POWER_MODES[DEFAULT_POWER])

