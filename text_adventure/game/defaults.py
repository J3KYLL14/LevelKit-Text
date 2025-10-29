START_ROOM_ID = "start"

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Starting stats
STARTING_STATS = {
    "hp": 20,
    "max_hp": 20,
    "mana": 10,
    "stamina": 10,
    "attack": 3,
    "defence": 1,
    "xp": 0,
}

# Global combat tuning
DAMAGE_VARIANCE = 2      # random 0..VAR added to base attack
CRIT_CHANCE = 0.0        # 0.0..1.0, set >0 if you want
CRIT_MULTIPLIER = 1.5

# XP & recovery
XP_PER_VICTORY = 5
MANA_PER_ROOM = 1        # passive regen on room change

# Routing
DEFEAT_ROOM_ID = "start" # where to send player on defeat (fallback)
