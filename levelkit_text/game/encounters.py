"""Random encounter helpers for advanced scenarios."""

from __future__ import annotations

import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..engine.models import BattleSpec


def pick_random_battle(
    battles: Dict[str, BattleSpec],
    pool: Optional[Sequence[str]] = None,
    weights: Optional[Sequence[float]] = None,
) -> BattleSpec:
    """Return a random battle from ``battles``.

    Parameters
    ----------
    battles:
        Mapping of battle id -> ``BattleSpec`` (as returned by the loader).
    pool:
        Optional subset of battle ids to select from. Defaults to all battles.
    weights:
        Optional weights aligned with ``pool`` to bias the roll.
    """
    choices = list(pool) if pool else list(battles.keys())
    if not choices:
        raise ValueError("Battle pool is empty.")
    if weights and len(weights) != len(choices):
        raise ValueError("weights must match the length of pool.")
    battle_id = random.choices(choices, weights=weights, k=1)[0]
    return battles[battle_id]


def pick_random_group(
    battles: Dict[str, BattleSpec],
    groups: Iterable[Tuple[Sequence[str], float]],
) -> List[BattleSpec]:
    """Return a list of battles representing a grouped encounter.

    Each entry in ``groups`` should be ``(battle_ids, weight)`` where
    ``battle_ids`` is a sequence of ids to include when the group is chosen.
    """
    weighted_groups = list(groups)
    if not weighted_groups:
        raise ValueError("No groups provided.")
    ids, weights = zip(*weighted_groups)
    index = random.choices(range(len(weighted_groups)), weights=weights, k=1)[0]
    selected_ids = ids[index]
    return [battles[battle_id] for battle_id in selected_ids if battle_id in battles]
