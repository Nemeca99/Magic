"""
number_pool.py — Modular Pool Configuration
"The Ghost of the Center" modding layer.

Edit this file to change the search space (Squares, Cubes, Primes, etc.)

This module is now backed by power_modes.py so that the active
search power (n) can be selected in a single place.
"""

from __future__ import annotations

import os
from typing import List, Optional

from power_modes import DEFAULT_POWER, PowerMode, get_power_mode


def _resolve_power_from_env() -> int:
    """
    Resolve the active power (n) from the MAGIC_POWER environment variable.

    Falls back to DEFAULT_POWER if unset or invalid.
    """
    raw = os.environ.get("MAGIC_POWER")
    if not raw:
        return DEFAULT_POWER
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_POWER
    return value


_ACTIVE_POWER: int = _resolve_power_from_env()
_ACTIVE_MODE: PowerMode = get_power_mode(_ACTIVE_POWER)


def get_number_pool(power: Optional[int] = None) -> List[int]:
    """
    Returns the list of integers to be used for the magic square search.

    MOD SECTIONS (see power_modes.py for definitions):
    - n=1: Baseline integers (1..9) — foundation calibration set
    - n=2: Squares (30^2 to 80^2)
    - n=3: Cubes (30^3 to 80^3)

    If no power is provided, the current process-wide ACTIVE_POWER is used,
    which is derived from the MAGIC_POWER environment variable and defaults
    to n=3 (cubes) for the siege.
    """
    mode = get_power_mode(power if power is not None else _ACTIVE_POWER)
    return mode.pool_fn()


# Metadata for UI / logging
POOL_DESCRIPTION: str = _ACTIVE_MODE.description
ACTIVE_POWER: int = _ACTIVE_MODE.power

