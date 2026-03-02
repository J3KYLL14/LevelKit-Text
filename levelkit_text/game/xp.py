"""XP progression utilities for the classroom adventure.

Student developers can tweak the XP requirements here to craft their own
progression curve. Edit ``XP_LEVEL_REQUIREMENTS`` for the early levels and
adjust ``XP_GROWTH_FACTOR`` to control how sharply the curve scales for
higher levels.
"""

from __future__ import annotations

import math
from typing import Tuple

# XP required to go from level N to level N+1 for the first few levels.
# Extend or adjust this list to fine-tune the early-game progression.
XP_LEVEL_REQUIREMENTS = [50, 90, 140, 200, 270]

# Multiplier that controls how XP requirements grow once the explicit list
# above runs out. Higher values make late levels slower to reach.
XP_GROWTH_FACTOR = 1.25


def _xp_requirement_for_index(index: int) -> int:
    if index < len(XP_LEVEL_REQUIREMENTS):
        return max(1, int(XP_LEVEL_REQUIREMENTS[index]))
    if not XP_LEVEL_REQUIREMENTS:
        return 100
    # Scale the final explicit requirement by the growth factor for each
    # additional level beyond the table.
    steps = index - len(XP_LEVEL_REQUIREMENTS) + 1
    base = XP_LEVEL_REQUIREMENTS[-1]
    requirement = base * (XP_GROWTH_FACTOR ** steps)
    return max(1, int(math.ceil(requirement)))


def xp_curve(total_xp: int) -> Tuple[int, int, int]:
    """Return (level, progress, target) for the given total XP."""
    xp_remaining = max(0, int(total_xp))
    level = 1
    index = 0
    while True:
        requirement = _xp_requirement_for_index(index)
        if xp_remaining < requirement:
            return level, xp_remaining, requirement
        xp_remaining -= requirement
        level += 1
        index += 1


XP_CURVE = xp_curve
