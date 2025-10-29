from engine.models import RoomSpec, OptionSpec

ROOM = RoomSpec(
    id="crypt",
    title="Quiet Crypt",
    body=(
        "Chill air drifts through rows of stone sarcophagi. A faint glow pulses beneath the floor.\n"
        "A ladder leads back up to the gate hall."
    ),
    background_key="crypt",
    music_key="ambient_silence",
    options=[
        OptionSpec(label="Climb the ladder back up", to="start"),
    ],
)
