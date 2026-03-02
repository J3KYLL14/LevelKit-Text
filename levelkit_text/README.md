# LevelKit-Text Template

This package contains the base engine used for classroom text adventures. It
ships with a tiny example scenario—an entrance room that branches left to a
practice alcove (where a training blade can be collected) and right to a goblin
test battle. The sample demonstrates how room routing, inventory, and battles
fit together, and can be used as a starting point or cleared away for your own
story.

## What to edit first

- `levels/` – add files ending with `_room.py` that export a `RoomSpec` named `ROOM`.
- `battle_loops/` – add battle modules that export a `BattleSpec` named `BATTLE`.
- `assets/images/registry.py` & `assets/sounds/registry.py` – register PNG or WAV assets.
- `game/defaults.py` – tweak starting stats, routing, and presentation constants.
- `game/items.py` & `game/weapons.py` – describe inventory items and equipment.
- `game/theme.py` – customise UI colours, fonts, and layout spacing.
- `game/xp.py` – adjust the XP curve to match your lesson goals.

Everything inside `engine/` powers the UI and core systems. Students normally
leave it untouched.

## Running the template

- Windows: double-click `run.bat` or run `python main.py`.
- macOS/Linux: double-click `run.command` (ensure it is executable) or run `python main.py`.

## Creating your first room

1. Create a new file in `levels/` such as `start_room.py`.
2. Import `RoomSpec` and `OptionSpec` from `engine.models`, then define a `ROOM`
   instance with a unique `id`, `title`, `body`, and list of options.
3. Update `START_ROOM_ID` in `game/defaults.py` to match the new room id.

Run `python main.py --validate` any time to check for missing rooms, battles, or
assets before class. Once students are comfortable with the included example,
they can replace the rooms, battle, and assets with their own creations.
