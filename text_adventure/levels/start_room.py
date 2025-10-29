from engine.models import RoomSpec, OptionSpec

ROOM = RoomSpec(
    id="start",
    title="Crumbling Gate",
    body=(
        "Moonlight over a shattered arch. A sign says, \"Speak true\".\n"
        "A lit archway to the left. A shadowed stairwell to the right."
    ),
    background_key="gate",
    music_key="ambient_silence",
    options=[
        OptionSpec(label="Take the archway", to="hall"),
        OptionSpec(label="Descend the stairwell", to="crypt"),
        OptionSpec(label="Shout a challenge at the darkness", battle_id="simple_goblin", to="hall"),
    ],
)
