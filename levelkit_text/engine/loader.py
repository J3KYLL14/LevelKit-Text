"""Content discovery utilities for the LevelKit-Text engine."""

import traceback
from importlib import import_module
from pathlib import Path
from typing import Dict, Tuple

from .models import BattleSpec, RoomSpec

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
LEVELS_DIR = PACKAGE_ROOT / "levels"
BATTLES_DIR = PACKAGE_ROOT / "battle_loops"
IMAGES_MODULE = "levelkit_text.assets.images.registry"
SOUNDS_MODULE = "levelkit_text.assets.sounds.registry"


class LoaderError(RuntimeError):
    """Raised when the loader encounters invalid content."""


def _load_registry(module_path: str, attr_name: str) -> Dict[str, str]:
    module = import_module(module_path)
    mapping = getattr(module, attr_name, None)
    if not isinstance(mapping, dict):
        raise LoaderError(f"Registry {module_path}.{attr_name} must be a dict.")
    return dict(mapping)


def load_registries() -> Tuple[Dict[str, str], Dict[str, str]]:
    """Return copies of the image and sound registries."""
    images = _load_registry(IMAGES_MODULE, "IMAGES")
    sounds = _load_registry(SOUNDS_MODULE, "SOUNDS")
    return images, sounds


def _module_name_from_path(base_package: str, path: Path) -> str:
    stem = path.with_suffix("").name
    return f"{base_package}.{stem}"


def _import_content_module(module_name: str, file_path: Path):
    try:
        return import_module(module_name)
    except SyntaxError as exc:
        line_number = getattr(exc, "lineno", "?")
        raise LoaderError(
            f"Could not load {file_path.name} because Python found a syntax problem on line "
            f"{line_number}: {exc.msg}."
        ) from exc
    except Exception as exc:
        brief = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        raise LoaderError(
            f"Could not run {file_path.name}. Check that file first. Problem: {brief}."
        ) from exc


def load_rooms() -> Dict[str, RoomSpec]:
    rooms: Dict[str, RoomSpec] = {}
    for file_path in sorted(LEVELS_DIR.glob("*.py")):
        if file_path.name.startswith("__"):
            continue
        module_name = _module_name_from_path("levelkit_text.levels", file_path)
        module = _import_content_module(module_name, file_path)
        room = getattr(module, "ROOM", None)
        if not isinstance(room, RoomSpec):
            raise LoaderError(
                f"{file_path.name} must define a room called ROOM using RoomSpec(...)."
            )
        if room.id in rooms:
            raise LoaderError(f"Two room files are using the same room id: '{room.id}'.")
        rooms[room.id] = room
    return rooms


def load_battles() -> Dict[str, BattleSpec]:
    battles: Dict[str, BattleSpec] = {}
    for file_path in sorted(BATTLES_DIR.glob("*.py")):
        if file_path.name.startswith("__"):
            continue
        module_name = _module_name_from_path("levelkit_text.battle_loops", file_path)
        module = _import_content_module(module_name, file_path)
        battle = getattr(module, "BATTLE", None)
        if not isinstance(battle, BattleSpec):
            raise LoaderError(
                f"{file_path.name} must define a battle called BATTLE using BattleSpec(...)."
            )
        if battle.id in battles:
            raise LoaderError(f"Two battle files are using the same battle id: '{battle.id}'.")
        battles[battle.id] = battle
    return battles


def load_all() -> Tuple[Dict[str, str], Dict[str, str], Dict[str, RoomSpec], Dict[str, BattleSpec]]:
    images, sounds = load_registries()
    rooms = load_rooms()
    battles = load_battles()
    return images, sounds, rooms, battles
