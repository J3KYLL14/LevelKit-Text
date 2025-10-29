# Classroom Text Adventure Engine

Welcome to the Baldur's Gate III inspired text adventure starter kit. This repository ships a plug-and-play engine plus a tiny adventure so students can focus on writing narrative content.

## What students may edit

Students have access to the following folders:

- `levels/` – one Python file per room exporting `ROOM`.
- `battle_loops/` – one Python file per battle exporting `BATTLE`.
- `assets/images/registry.py` and `assets/sounds/registry.py` – register background images and looping audio.
- `game/defaults.py` – adjust starting stats, XP rewards, mana regeneration, and defeat routing.

Everything in `engine/` is read-only for students. Only instructors should modify the engine.

## Running the game

- Windows: double-click `run.bat` or open a terminal and run `python main.py`.
- macOS/Linux: double-click `run.command` (ensure it is executable) or run `python main.py`.

The entry point automatically loads the current save from `saves/slot1.json` if present.

## Adding a new room in three steps

1. Copy an existing file in `levels/` (e.g., `start_room.py`) and rename it to `<your_room_id>_room.py`.
2. Edit the new file so it exports a `RoomSpec` instance named `ROOM`. Give it a unique `id`, descriptive `title`, `body` text, and a list of `OptionSpec` entries.
3. Reference the new room from an existing room's options (or another new room) using the `to="your_room_id"` field.

## Adding a new battle in three steps

1. Create a new file in `battle_loops/` with a descriptive name, such as `spider_ambush.py`.
2. Define a `BattleSpec` instance named `BATTLE`, filling out the enemy stats, action list, and optional routing fields.
3. In any room option, set `battle_id` to the new battle's id. Optionally set `to` for the post-victory route.

## Registering art or audio

1. Drop PNG files into `assets/images/` and WAV files into `assets/sounds/`.
2. Add entries to `assets/images/registry.py` (`IMAGES`) or `assets/sounds/registry.py` (`SOUNDS`) mapping a unique key to the filename.
3. Reference the keys from rooms (`background_key`, `music_key`) or via the audio API.

## Tweaking gameplay defaults

Edit `game/defaults.py` to configure:

- Window dimensions
- Starting stats (`STARTING_STATS`)
- Damage variance, crit chance, XP rewards, mana regeneration
- Defeat routing (`DEFEAT_ROOM_ID`)

This file is the only place stats and global tuning should be changed.

## Keyboard shortcuts

- `1`–`9`: Activate the matching choice button.
- `I`: Open the inventory modal.
- `Esc`/window close: Saves to `saves/slot1.json` before quitting.

## Troubleshooting (school lab edition)

- **No sound?** Ensure the lab image has `afplay`, `paplay`, or `aplay` installed. The engine fails silently if none are available.
- **Tkinter errors on launch?** Install a Python build with Tk support (Windows Store and macOS official installers include it). On Linux, install `python3-tk` via the system package manager.
- **Graphics missing?** Confirm the PNG is in `assets/images/` and registered in `assets/images/registry.py`.
- **Validator failures?** Run `python main.py --validate` to see which room, battle, or asset is misconfigured.
- **Save corruption?** Delete `saves/slot1.json` and restart the game.
