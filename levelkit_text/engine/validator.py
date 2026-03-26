"""Validation utilities for teacher sanity checks."""

from typing import Dict, Set, Tuple

from .models import BattleSpec, RoomSpec


def _validate_assets(rooms: Dict[str, RoomSpec], images: Dict[str, str], sounds: Dict[str, str]) -> Tuple[bool, str]:
    for room in rooms.values():
        if room.background_key and room.background_key not in images:
            return False, f"Room '{room.id}' asks for a background called '{room.background_key}', but that image is not in the image registry."
        if room.music_key and room.music_key not in sounds:
            return False, f"Room '{room.id}' asks for music called '{room.music_key}', but that sound is not in the sound registry."
    return True, "ok"


def _validate_graph(
    rooms: Dict[str, RoomSpec],
    start_room_id: str,
    battles: Dict[str, BattleSpec],
    defeat_fallback: str,
) -> Tuple[bool, str]:
    if start_room_id not in rooms:
        return False, f"The game starts in room '{start_room_id}', but no room with that id exists."

    adjacency: Dict[str, Set[str]] = {room_id: set() for room_id in rooms}

    for room in rooms.values():
        for option in room.options:
            if option.to and option.to not in rooms:
                return False, f"In room '{room.id}', the button '{option.label}' points to room '{option.to}', but that room does not exist."
            if option.to:
                adjacency[room.id].add(option.to)
            if option.battle_id:
                if option.battle_id not in battles:
                    return False, f"In room '{room.id}', the button '{option.label}' starts battle '{option.battle_id}', but that battle does not exist."
                battle = battles[option.battle_id]
                if battle.victory_to and battle.victory_to not in rooms:
                    return False, f"Battle '{battle.id}' sends the player to room '{battle.victory_to}' after a win, but that room does not exist."
                if battle.defeat_to and battle.defeat_to not in rooms:
                    return False, f"Battle '{battle.id}' sends the player to room '{battle.defeat_to}' after a loss, but that room does not exist."
                if battle.victory_to:
                    adjacency[room.id].add(battle.victory_to)
                elif option.to:
                    adjacency[room.id].add(option.to)
                defeat_target = battle.defeat_to or defeat_fallback
                if defeat_target:
                    if defeat_target not in rooms:
                        return False, f"Battle '{battle.id}' needs a defeat room called '{defeat_target}', but that room does not exist."
                    adjacency[room.id].add(defeat_target)

    visited: Set[str] = set()
    stack = [start_room_id]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        stack.extend(adjacency.get(current, ()))

    unreachable = set(rooms.keys()) - visited
    if unreachable:
        return False, f"These rooms can never be reached from the start of the game: {', '.join(sorted(unreachable))}."

    return True, "ok"


def validate(
    rooms: Dict[str, RoomSpec],
    images: Dict[str, str],
    sounds: Dict[str, str],
    battles: Dict[str, BattleSpec],
    defaults_module,
) -> Tuple[bool, str]:
    assets_ok, assets_msg = _validate_assets(rooms, images, sounds)
    if not assets_ok:
        return False, assets_msg

    graph_ok, graph_msg = _validate_graph(
        rooms,
        getattr(defaults_module, "START_ROOM_ID"),
        battles,
        getattr(defaults_module, "DEFEAT_ROOM_ID", ""),
    )
    if not graph_ok:
        return False, graph_msg

    return True, "Validation passed."
