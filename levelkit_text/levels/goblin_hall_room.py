"""Hallway leading to the goblin encounter."""

from engine.models import Button, RoomSpec

ROOM = RoomSpec(
    id="goblin_hall",
    title="Right Passage",
    body=(
        "A goblin skulker plants itself in the middle of the yellow-lit hallway, "
        "brandishing a crude spear and daring you to pass."
    ),
    background_key="goblin_yellow",
    options=[
        Button(label="Face the goblin", battle_id="goblin_trial"),
        Button(label="Retreat to the entrance", to="start"),
    ],
)
