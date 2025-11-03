"""Training alcove where the player can collect a weapon."""

from engine.models import OptionSpec, RoomSpec

ROOM = RoomSpec(
    id="armory",
    title="Practice Alcove",
    body=(
        "A single training blade rests on a rack, its edge polished from countless drills. "
        "Dust motes drift through the blue light as if waiting for your decision."
    ),
    background_key="armory_blue",
    options=[
        OptionSpec(
            label="Take the training blade",
            gain_items=["Wooden Bow"],
            set_flag="weapon_taken",
            requires_not_flag="weapon_taken",
            hint="Equips automatically",
            effects={"equip_item": "wooden_bow"},
        ),
        OptionSpec(label="Return to the entrance", to="start"),
    ],
)

