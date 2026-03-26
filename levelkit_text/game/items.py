"""Item definitions for the template build."""

# Extend this mapping with your own item definitions. Keys should be unique
# identifiers and values should describe the item (name, description, effects, etc.).
ITEM_DEFINITIONS: dict[str, dict[str, object]] = {
    "training_vest": {
        "name": "Training Vest",
        "description": "Padded armour that softens incoming blows during drills.",
        "category": "armour",
        "equip_slot": "armour",
        "effects": {"defence": 2, "max_hp": 2},
    },
    "rusty_key": {
        "name": "Rusty Key",
        "description": "An old key that looks like it might snap after a few uses.",
        "category": "quest",
        "stackable": False,
        "uses": 2,
    },
}
