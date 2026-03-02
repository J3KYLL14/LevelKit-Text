"""Room visited when the player loses to the goblin."""

from engine.models import OptionSpec, RoomSpec

ROOM = RoomSpec(
    id="goblin_defeat",
    title="Recovery Chamber",
    body=(
        "You come to amid urgent red light, the sting of the goblin's strike still fresh. "
        "Someone dragged you back to safety—time to regroup."
    ),
    background_key="defeat_red",
    options=[
        OptionSpec(label="Gather yourself and try again", to="start"),
    ],
)

