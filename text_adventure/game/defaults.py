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

# Visual theme defaults
UI_THEME = {
    "window": {
        "background": "#101010",
        "fallback_text": "#ffffff",
    },
    "layout": {
        "header_width": 0.8,
        "header_top_margin": 0.04,
        "content_width": 0.68,
        "options_bottom_margin": 0.05,
        "option_spacing": 0.02,
        "dialogue_options_gap": 0.02,
    },
    "header": {
        "panel_background": "#202020cc",
        "panel_outline": "",
        "corner_radius": 26,
        "padding": 24,
        "title_font": ("Segoe UI", 20, "bold"),
        "title_foreground": "#f0f0f0",
        "stats_font": ("Segoe UI", 14, ""),
        "stats_foreground": "#dedede",
    },
    "dialogue": {
        "panel_background": "#1c1c1ccc",
        "panel_outline": "",
        "corner_radius": 28,
        "padding": 28,
        "font": ("Segoe UI", 14, ""),
        "foreground": "#f8f8f2",
    },
    "options": {
        "panel_background": "#1c1c1ccc",
        "panel_outline": "",
        "corner_radius": 24,
        "padding": 18,
        "button_corner_radius": 18,
        "button_font": ("Segoe UI", 12, ""),
        "button_height": 56,
        "button_padding": 22,
        "button_foreground": "#f5f5f5",
        "button_background": "#252525",
        "button_hover_background": "#343434",
        "button_active_background": "#454545",
        "button_disabled_background": "#151515",
        "button_disabled_foreground": "#7a7a7a",
        "button_horizontal_padding": 20,
    },
}
