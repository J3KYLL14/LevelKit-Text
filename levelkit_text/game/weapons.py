"""Weapon definitions for the template build."""

# Add any equippable weapon-style items here. These definitions merge into the
# base item list exposed to the engine.
WEAPON_DEFINITIONS: dict[str, dict[str, object]] = {
    "training_sword": {
        "name": "Training Blade",
        "description": "A balanced practice sword that sharpens your stance.",
        "category": "weapon",
        "weapon_type": "melee",
        "effects": {"attack": 10},
    },
    "wooden_bow": {
        "name": "Wooden Bow",
        "description": "A simple bow made from sturdy oak, suitable for beginners.",
        "category": "weapon",
        "weapon_type": "ranged",
        "effects": {"attack": 8, "range": 15},
    },
}

