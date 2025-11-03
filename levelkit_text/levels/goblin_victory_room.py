"""Room visited when the player defeats the goblin."""

from engine.models import OptionSpec, RoomSpec

ROOM = RoomSpec(
    id="goblin_victory",
    title="Cleared Corridor",
    body=(
        "The goblin crumples, leaving the passage quiet and washed in gentle green light. "
        "Beyond, fresh possibilities await."
    ),
    background_key="victory_green",
    options=[
        OptionSpec(label="Return to the entrance", to="start"),
    ],
)

