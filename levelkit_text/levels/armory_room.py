"""Training alcove where the player can collect a weapon."""

from engine.models import Button, RoomSpec

ROOM = RoomSpec(
    id="armory",
    title="Practice Alcove",
    body=(
        "A training blade and padded vest rest on a rack beside a crate with a bent key. "
        "Dust motes drift through the blue light as if waiting for your decision."
    ),
    background_key="armory_blue",
    options=[
        Button(
            label="Take the training blade",
            gain_items=["training_sword"],
            set_flag="weapon_taken",
            requires_not_flag="weapon_taken",
            hint="Equips automatically",
            effects={"equip_item": "training_sword"},
        ),
        Button(
            label="Take the training vest",
            gain_items=["training_vest"],
            set_flag="armour_taken",
            requires_not_flag="armour_taken",
            hint="Equips automatically",
            effects={"equip_item": "training_vest"},
        ),
        Button(
            label="Pocket the rusty key",
            gain_items=["rusty_key"],
            set_flag="key_taken",
            requires_not_flag="key_taken",
        ),
        Button(label="Return to the entrance", to="start"),
    ],
)
