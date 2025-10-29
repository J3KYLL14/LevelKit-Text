from dataclasses import dataclass, field
from typing import List, Optional, Dict, Literal


@dataclass
class Stats:
    hp: int
    max_hp: int
    mana: int
    stamina: int
    attack: int
    defence: int
    xp: int


@dataclass
class Item:
    id: str
    name: str
    description: str
    kind: Literal["consumable","weapon","armour","quest"]
    effects: Dict[str, int] = field(default_factory=dict)
    stackable: bool = True


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


@dataclass
class RoomSpec:
    id: str
    title: str
    body: str
    background_key: Optional[str] = None
    music_key: Optional[str] = None
    options: List[OptionSpec] = field(default_factory=list)


@dataclass
class BattleAction:
    kind: Literal["attack","skill_check","cast"]
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


@dataclass
class BattleOutcome:
    victory: bool
    next_room_id: Optional[str] = None
    loot: List[str] = field(default_factory=list)
    xp_gain: int = 0
