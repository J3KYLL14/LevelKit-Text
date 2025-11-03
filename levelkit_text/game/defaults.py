"""Default configuration for the text adventure template."""

from __future__ import annotations

from .items import ITEM_DEFINITIONS as BASE_ITEM_DEFINITIONS
from .theme import UI_THEME
from .weapons import WEAPON_DEFINITIONS
from .xp import XP_CURVE, XP_GROWTH_FACTOR, XP_LEVEL_REQUIREMENTS

# Merge custom item definitions provided in ``items.py`` and ``weapons.py``.
ITEM_DEFINITIONS = {**BASE_ITEM_DEFINITIONS, **WEAPON_DEFINITIONS}

# Game flow -----------------------------------------------------------------

# Update this once you add your first room (see ``levels`` package).
START_ROOM_ID = "start"

# Where the player is sent after losing a battle. Override as needed.
DEFEAT_ROOM_ID = START_ROOM_ID

# Presentation --------------------------------------------------------------
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Text shown in the title bar and header area.
GAME_TITLE = "Text Adventure"
GAME_BYLINE = ""

# Save behaviour ------------------------------------------------------------
LOAD_SAVE_ON_START = False

# Player stats --------------------------------------------------------------
STARTING_STATS = {
    "hp": 10,
    "max_hp": 10,
    "mana": 5,
    "max_mana": 5,
    "stamina": 5,
    "attack": 1,
    "defence": 0,
    "xp": 0,
}

# Combat tuning -------------------------------------------------------------
DAMAGE_VARIANCE = 2
CRIT_CHANCE = 0.0
CRIT_MULTIPLIER = 1.5

# XP & recovery -------------------------------------------------------------
XP_PER_VICTORY = 5
MANA_PER_ROOM = 0.25

