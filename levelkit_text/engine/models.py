from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal


@dataclass
class Stats:
    hp: int
    max_hp: int
    mana: int
    max_mana: int
    stamina: int
    attack: int
    defence: int
    xp: int


@dataclass
class Item:
    id: str
    name: str
    description: str
    kind: Literal["consumable", "weapon", "armour", "quest", "ammo"]
    effects: Dict[str, int] = field(default_factory=dict)
    stackable: bool = True
    weapon_type: Optional[Literal["melee", "ranged"]] = None
    ammo_item: Optional[str] = None
    ammo_per_use: int = 1


@dataclass
class Weapon:
    id: str
    name: str
    description: str
    weapon_type: Literal["melee", "ranged"]
    effects: Dict[str, int] = field(default_factory=dict)
    ammo_item: Optional[str] = None
    ammo_per_use: int = 1
    stackable: bool = False


@dataclass
class Enemy:
    id: str
    name: str
    hp: int
    attack: int
    defence: int
    loot: List[str] = field(default_factory=list)


@dataclass
class OptionSpec:
    label: str
    to: Optional[str] = None
    battle_id: Optional[str] = None
    hint: Optional[str] = None
    require_expr: Optional[Dict[str, Any]] = None
    gain_items: List[str] = field(default_factory=list)
    requires_flag: Optional[str] = None
    requires_not_flag: Optional[str] = None
    set_flag: Optional[str] = None
    clear_flag: Optional[str] = None
    effects: Dict[str, Any] = field(default_factory=dict)
    loot_table: List[Dict[str, Any]] = field(default_factory=list)
    loot_rolls: int = 1
    battle_repeat_limit: Optional[int] = None
    battle_repeat_message: Optional[str] = None
    battle_repeat_key: Optional[str] = None
    sound_key: Optional[str] = None


@dataclass
class RoomSpec:
    id: str
    title: str
    body: str
    background_key: Optional[str] = None
    music_key: Optional[str] = None
    enter_sound_key: Optional[str] = None
    puzzle: Optional[Dict[str, Any]] = None
    options: List[OptionSpec] = field(default_factory=list)


@dataclass
class BattleAction:
    kind: Literal["attack", "skill_check", "cast"]
    label: str
    bonus: int = 0
    variance: int = 2
    stat: Optional[str] = None
    gte: Optional[int] = None
    success_damage: int = 0
    fail_damage: int = 0
    success_heal: int = 0
    fail_heal: int = 0
    mana_cost: int = 0
    sound_key: Optional[str] = None
    requires_weapon_type: Optional[Literal["melee", "ranged"]] = None
    requires_weapon_id: Optional[str] = None
    ammo_item: Optional[str] = None
    ammo_cost: int = 1
    hit_chance: float = 1.0
    show_if_unavailable: bool = False


@dataclass
class BattleSpec:
    id: str
    title: str
    enemy: Enemy
    actions: List[BattleAction]
    victory_to: Optional[str] = None
    defeat_to: Optional[str] = None
    victory_text: str = "Victory."
    defeat_text: str = "Defeat."
    loot_table: List[Dict[str, Any]] = field(default_factory=list)
    loot_rolls: int = 1


@dataclass
class BattleOutcome:
    victory: bool
    next_room_id: Optional[str] = None
    loot: List[str] = field(default_factory=list)
    xp_gain: int = 0
