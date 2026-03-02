"""Simple JSON save/load helpers."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional, List

from .models import Stats

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAVE_PATH = PACKAGE_ROOT / "saves" / "slot1.json"


def save_game(
    room_id: str,
    stats: Stats,
    inventory: Dict[str, int],
    flags: Dict[str, bool],
    path: Path = DEFAULT_SAVE_PATH,
    counters: Optional[Dict[str, int]] = None,
    story_items_used: Optional[List[str]] = None,
    unique_loot: Optional[List[str]] = None,
) -> None:
    data = {
        "room_id": room_id,
        "stats": asdict(stats),
        "inventory": inventory,
        "flags": flags,
    }
    if counters:
        data["counters"] = counters
    if story_items_used:
        data["story_items_used"] = story_items_used
    if unique_loot:
        data["unique_loot"] = unique_loot
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_game(path: Path = DEFAULT_SAVE_PATH) -> Optional[Dict[str, object]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    return data


def delete_save(path: Path = DEFAULT_SAVE_PATH) -> None:
    if path.exists():
        path.unlink()
