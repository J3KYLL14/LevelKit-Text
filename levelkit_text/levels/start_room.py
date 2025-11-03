"""Starting room for the template adventure."""

from engine.models import OptionSpec, RoomSpec

ROOM = RoomSpec(
    id="start",
    title="Entrance Hall",
    body=(
        "You stand at a junction of the old training complex. "
        "A dim corridor stretches left toward a practice alcove, while a harsh light flickers to the right."
    ),
    background_key="start_black",
    options=[
        OptionSpec(label="Go left toward the practice alcove", to="armory"),
        OptionSpec(label="Go right toward the flickering light", to="goblin_hall"),
    ],
)

