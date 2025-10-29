from engine.models import RoomSpec, OptionSpec

ROOM = RoomSpec(
    id="hall",
    title="Echoing Hall",
    body=(
        "The hall is long and lined with warrior statues. Dust dances in torchlight.\n"
        "To the north, a reinforced door hums with magic. Back south lies the gate."
    ),
    background_key="hall",
    music_key="ambient_silence",
    options=[
        OptionSpec(label="Inspect the statues", to="hall"),
        OptionSpec(label="Return to the gate", to="start"),
    ],
)
