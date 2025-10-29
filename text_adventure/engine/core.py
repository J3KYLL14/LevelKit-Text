"""Tkinter-powered classroom adventure engine."""

import random
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Callable, Dict, List, Optional, Tuple

from . import audio, save
from .models import BattleAction, BattleSpec, RoomSpec, Stats

DEFAULT_ITEM_EFFECTS: Dict[str, Dict[str, object]] = {
    "potion_small": {
        "name": "Small Potion",
        "description": "Restores a small amount of health.",
        "effects": {"hp": 5},
    }
}

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = PACKAGE_ROOT / "assets" / "images"
SOUNDS_DIR = PACKAGE_ROOT / "assets" / "sounds"


class GameApp:
    """Top-level Tkinter application managing rooms and battles."""

    def __init__(
        self,
        rooms: Dict[str, RoomSpec],
        battles: Dict[str, BattleSpec],
        images: Dict[str, str],
        sounds: Dict[str, str],
        defaults_module,
    ) -> None:
        self.rooms = rooms
        self.battles = battles
        self.images = images
        self.sounds = sounds
        self.defaults = defaults_module
        self.stats = self._build_stats(self.defaults.STARTING_STATS)
        self.inventory: Dict[str, int] = {}
        self.flags: Dict[str, bool] = {}
        self.current_room_id: Optional[str] = None
        self.current_music_key: Optional[str] = None
        self.current_battle: Optional[Dict[str, object]] = None
        self.option_handlers: List[Callable[[], None]] = []
        self.save_path = save.DEFAULT_SAVE_PATH

        self.root = tk.Tk()
        self.root.title("Text Adventure")
        self.root.geometry(f"{self.defaults.WINDOW_WIDTH}x{self.defaults.WINDOW_HEIGHT}")
        self.root.configure(bg="#101010")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.background_label = tk.Label(self.root, bg="#000000", fg="#ffffff")
        self.background_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.top_frame = tk.Frame(self.root, bg="#1b1b1b", bd=0, highlightthickness=0)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)

        self.title_var = tk.StringVar(value="")
        self.title_label = tk.Label(
            self.top_frame,
            textvariable=self.title_var,
            anchor="w",
            bg="#1b1b1b",
            fg="#f0f0f0",
            font=("Segoe UI", 20, "bold"),
            padx=16,
            pady=8,
        )
        self.title_label.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.stats_var = tk.StringVar()
        self.stats_label = tk.Label(
            self.top_frame,
            textvariable=self.stats_var,
            anchor="e",
            bg="#1b1b1b",
            fg="#dddddd",
            font=("Segoe UI", 14),
            padx=16,
            pady=8,
        )
        self.stats_label.pack(side=tk.RIGHT)

        self.dialogue_frame = tk.Frame(self.root, bg="#141414")
        self.dialogue_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.dialogue_var = tk.StringVar(value="")
        self.dialogue_label = tk.Label(
            self.dialogue_frame,
            textvariable=self.dialogue_var,
            justify="left",
            anchor="nw",
            wraplength=self.defaults.WINDOW_WIDTH - 40,
            bg="#141414",
            fg="#f8f8f2",
            font=("Segoe UI", 14),
            padx=20,
            pady=16,
        )
        self.dialogue_label.pack(side=tk.TOP, fill=tk.X)

        self.options_frame = tk.Frame(self.dialogue_frame, bg="#111111", pady=12)
        self.options_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.option_buttons: List[tk.Button] = []
        for index in range(9):
            btn = tk.Button(
                self.options_frame,
                text="",
                anchor="w",
                justify="left",
                bg="#2b2b2b",
                fg="#f0f0f0",
                activebackground="#3b3b3b",
                activeforeground="#ffffff",
                font=("Segoe UI", 12),
                command=lambda idx=index: self._on_option(idx),
            )
            btn.pack(side=tk.TOP, fill=tk.X, padx=20, pady=3)
            self.option_buttons.append(btn)

        for number in range(1, 10):
            self.root.bind(str(number), lambda event, idx=number - 1: self._on_option(idx))
        self.root.bind("i", self.open_inventory)
        self.root.bind("I", self.open_inventory)

        self._load_save()
        start_room = self.current_room_id or self.defaults.START_ROOM_ID
        self.go_to(start_room, initial=True)

    @staticmethod
    def _build_stats(starting: Dict[str, int]) -> Stats:
        return Stats(**starting)

    def _load_save(self) -> None:
        data = save.load_game(self.save_path)
        if not data:
            return
        try:
            stats_data = data.get("stats", {})
            self.stats = Stats(**{k: int(v) for k, v in stats_data.items()})
            self.inventory = {k: int(v) for k, v in data.get("inventory", {}).items()}
            self.flags = {k: bool(v) for k, v in data.get("flags", {}).items()}
            self.current_room_id = str(data.get("room_id")) if data.get("room_id") else None
        except Exception:
            self.stats = self._build_stats(self.defaults.STARTING_STATS)
            self.inventory = {}
            self.flags = {}
            self.current_room_id = None

    def on_close(self) -> None:
        if self.current_room_id:
            self.save_game()
        audio.stop_music()
        self.root.destroy()

    def save_game(self) -> None:
        if not self.current_room_id:
            return
        save.save_game(self.current_room_id, self.stats, self.inventory, self.flags, self.save_path)

    def run(self) -> None:
        self.root.mainloop()

    def set_dialogue(self, text: str) -> None:
        self.dialogue_var.set(text)

    def set_options(self, options: List[Tuple[str, Callable[[], None]]]) -> None:
        self.option_handlers = [handler for _, handler in options]
        for index, button in enumerate(self.option_buttons):
            if index < len(options):
                label, _ = options[index]
                button.configure(text=f"{index + 1}. {label}", state=tk.NORMAL)
            else:
                button.configure(text="", state=tk.DISABLED)

    def _on_option(self, index: int) -> None:
        if index >= len(self.option_handlers):
            return
        handler = self.option_handlers[index]
        handler()

    def update_stats_display(self) -> None:
        self.stats_var.set(
            f"HP {self.stats.hp}/{self.stats.max_hp}  ATK {self.stats.attack}  DEF {self.stats.defence}  MANA {self.stats.mana}  XP {self.stats.xp}"
        )

    def _set_background(self, key: Optional[str]) -> None:
        if not key:
            self.background_label.configure(image="", text="No background image", font=("Segoe UI", 24, "bold"))
            self.background_label.image = None
            return
        filename = self.images.get(key)
        if not filename:
            self.background_label.configure(image="", text="Missing background", font=("Segoe UI", 24, "bold"))
            self.background_label.image = None
            return
        path = IMAGES_DIR / filename
        if not path.exists():
            self.background_label.configure(image="", text="Background file not found", font=("Segoe UI", 24, "bold"))
            self.background_label.image = None
            return
        try:
            image = tk.PhotoImage(file=str(path))
        except Exception:
            self.background_label.configure(image="", text="Failed to load image", font=("Segoe UI", 24, "bold"))
            self.background_label.image = None
            return
        self.background_label.configure(image=image, text="")
        self.background_label.image = image

    def _set_music(self, key: Optional[str]) -> None:
        if key == self.current_music_key:
            return
        self.current_music_key = key
        audio.play_music(key, self.sounds, SOUNDS_DIR)

    def _regen_mana(self) -> None:
        if self.defaults.MANA_PER_ROOM <= 0:
            return
        self.stats.mana += self.defaults.MANA_PER_ROOM

    def go_to(self, room_id: str, initial: bool = False) -> None:
        room = self.rooms.get(room_id)
        if not room:
            self.set_dialogue(f"Room '{room_id}' is missing.")
            return
        if not initial:
            self._regen_mana()
        self.current_room_id = room_id
        self.current_battle = None
        self.title_var.set(room.title)
        self.set_dialogue(room.body)
        self._set_background(room.background_key)
        self._set_music(room.music_key)
        self.update_stats_display()

        options: List[Tuple[str, Callable[[], None]]] = []
        for option in room.options:
            options.append((option.label, lambda opt=option: self._handle_room_option(opt)))
        if not options:
            options.append(("Catch your breath.", lambda: None))
        self.set_options(options)
        self.save_game()

    def _handle_room_option(self, option) -> None:
        if option.battle_id:
            battle = self.battles.get(option.battle_id)
            if not battle:
                self.set_dialogue(f"Battle '{option.battle_id}' not found.")
                return
            self.start_battle(battle, option.to)
            return
        if option.to:
            self.go_to(option.to)
            return
        self.set_dialogue("You wait, but nothing happens.")

    def start_battle(self, battle: BattleSpec, option_default_to: Optional[str]) -> None:
        self.current_battle = {
            "spec": battle,
            "option_to": option_default_to,
            "enemy_hp": battle.enemy.hp,
        }
        self.set_dialogue(f"{battle.title}\n{battle.enemy.name} prepares to strike!")
        options = [(action.label, lambda act=action: self._resolve_battle_action(act)) for action in battle.actions]
        self.set_options(options)

    def _resolve_battle_action(self, action: BattleAction) -> None:
        if not self.current_battle:
            return
        battle: BattleSpec = self.current_battle["spec"]  # type: ignore[assignment]
        log_lines: List[str] = [battle.title]

        if action.kind == "attack":
            damage = self._calculate_player_damage(action.bonus, action.variance)
            self.current_battle["enemy_hp"] = max(0, self.current_battle["enemy_hp"] - damage)
            log_lines.append(f"You use {action.label} for {damage} damage.")
        elif action.kind == "skill_check":
            stat_name = action.stat or ""
            stat_value = getattr(self.stats, stat_name, 0)
            threshold = action.gte or 0
            if stat_value >= threshold:
                if action.success_damage:
                    self.current_battle["enemy_hp"] = max(0, self.current_battle["enemy_hp"] - action.success_damage)
                if action.success_heal:
                    self._heal_player(action.success_heal)
                log_lines.append(f"Success! {action.label} lands.")
            else:
                if action.fail_damage:
                    self._take_damage(action.fail_damage)
                if action.fail_heal:
                    self._heal_player(action.fail_heal)
                log_lines.append(f"Failed check. {action.label} falters.")
        elif action.kind == "cast":
            if self.stats.mana < action.mana_cost:
                log_lines.append("Not enough mana.")
                self.set_dialogue("\n".join(log_lines))
                self.update_stats_display()
                return
            self.stats.mana -= action.mana_cost
            damage = self._calculate_player_damage(action.bonus, action.variance)
            self.current_battle["enemy_hp"] = max(0, self.current_battle["enemy_hp"] - damage)
            log_lines.append(f"You channel energy! {damage} damage dealt.")
        else:
            log_lines.append("You hesitate.")

        enemy_hp = self.current_battle["enemy_hp"]
        if enemy_hp <= 0:
            self._handle_victory()
            return

        log_lines.extend(self._enemy_attack(battle))
        self.update_stats_display()
        if self.stats.hp <= 0:
            self._handle_defeat()
            return

        self.set_dialogue("\n".join(log_lines))

    def _calculate_player_damage(self, bonus: int, variance: int) -> int:
        total_variance = max(0, variance + getattr(self.defaults, "DAMAGE_VARIANCE", 0))
        roll = random.randint(0, total_variance)
        damage = max(0, (self.stats.attack + bonus + roll))
        damage -= self.current_battle["spec"].enemy.defence if self.current_battle else 0
        damage = max(0, damage)
        crit_chance = getattr(self.defaults, "CRIT_CHANCE", 0.0)
        if crit_chance > 0.0 and random.random() < crit_chance:
            multiplier = getattr(self.defaults, "CRIT_MULTIPLIER", 1.5)
            damage = int(damage * multiplier)
        return damage

    def _enemy_attack(self, battle: BattleSpec) -> List[str]:
        variance = getattr(self.defaults, "DAMAGE_VARIANCE", 2)
        roll = random.randint(0, max(0, variance))
        damage = max(0, battle.enemy.attack + roll - self.stats.defence)
        if damage > 0:
            self._take_damage(damage)
            return [f"{battle.enemy.name} strikes for {damage} damage!"]
        return [f"{battle.enemy.name}'s attack glances off your armour."]

    def _take_damage(self, amount: int) -> None:
        self.stats.hp = max(0, self.stats.hp - amount)

    def _heal_player(self, amount: int) -> None:
        self.stats.hp = min(self.stats.max_hp, self.stats.hp + amount)

    def _handle_victory(self) -> None:
        if not self.current_battle:
            return
        battle: BattleSpec = self.current_battle["spec"]
        self.set_dialogue(battle.victory_text)
        xp_gain = getattr(self.defaults, "XP_PER_VICTORY", 0)
        self.stats.xp += xp_gain
        loot_items = battle.enemy.loot
        self._collect_loot(loot_items)
        next_room = battle.victory_to or self.current_battle.get("option_to") or self.current_room_id
        self.current_battle = None
        self.update_stats_display()
        self.save_game()
        if next_room:
            self.root.after(500, lambda rid=next_room: self.go_to(rid))

    def _handle_defeat(self) -> None:
        if not self.current_battle:
            return
        battle: BattleSpec = self.current_battle["spec"]
        self.set_dialogue(battle.defeat_text)
        self.stats.hp = self.stats.max_hp
        defeat_room = battle.defeat_to or getattr(self.defaults, "DEFEAT_ROOM_ID", self.defaults.START_ROOM_ID)
        self.current_battle = None
        self.update_stats_display()
        self.save_game()
        self.root.after(700, lambda rid=defeat_room: self.go_to(rid))

    def _collect_loot(self, items: List[str]) -> None:
        if not items:
            return
        for item in items:
            self.inventory[item] = self.inventory.get(item, 0) + 1
        loot_text = ", ".join(items)
        self.set_dialogue(self.dialogue_var.get() + f"\nLoot acquired: {loot_text}.")

    def open_inventory(self, event=None) -> None:
        if not self.inventory:
            self.set_dialogue("Your inventory is empty.")
            return
        window = tk.Toplevel(self.root)
        window.title("Inventory")
        listbox = tk.Listbox(window, width=40)
        for item_id, count in self.inventory.items():
            definition = DEFAULT_ITEM_EFFECTS.get(item_id, {})
            name = definition.get("name", item_id)
            listbox.insert(tk.END, f"{name} x{count}")
        listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=12)

        def use_selected() -> None:
            selection = listbox.curselection()
            if not selection:
                return
            item_id = list(self.inventory.keys())[selection[0]]
            if self._use_item(item_id):
                if self.inventory[item_id] <= 0:
                    del self.inventory[item_id]
                window.destroy()
                self.save_game()

        use_button = tk.Button(window, text="Use", command=use_selected)
        use_button.pack(side=tk.BOTTOM, pady=8)

    def _use_item(self, item_id: str) -> bool:
        if item_id not in self.inventory:
            return False
        definition = DEFAULT_ITEM_EFFECTS.get(item_id)
        if not definition:
            messagebox.showinfo("Inventory", "Nothing happens.")
            return False
        effects = definition.get("effects", {})
        for stat_name, delta in effects.items():
            if hasattr(self.stats, stat_name):
                value = getattr(self.stats, stat_name) + int(delta)
                if stat_name == "hp":
                    value = min(self.stats.max_hp, max(0, value))
                setattr(self.stats, stat_name, value)
        self.inventory[item_id] -= 1
        self.update_stats_display()
        messagebox.showinfo("Inventory", f"Used {definition.get('name', item_id)}.")
        return True


def create_app(rooms: Dict[str, RoomSpec], battles: Dict[str, BattleSpec], images: Dict[str, str], sounds: Dict[str, str], defaults_module) -> GameApp:
    return GameApp(rooms, battles, images, sounds, defaults_module)
