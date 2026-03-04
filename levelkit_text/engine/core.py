"""Tkinter-powered classroom adventure engine."""

from __future__ import annotations

from collections import Counter
import random
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import tkinter as tk
from tkinter import messagebox

from . import audio
from .models import BattleAction, BattleSpec, OptionSpec, RoomSpec, Stats

# Fallback definitions for engine-created items. Leave empty in the template.
DEFAULT_ITEM_DEFINITIONS: Dict[str, Dict[str, object]] = {}

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = PACKAGE_ROOT / "assets" / "images"
SOUNDS_DIR = PACKAGE_ROOT / "assets" / "sounds"


# ------------------------------------------------------------------
# Colour helpers
# ------------------------------------------------------------------

def _tk_color(color: str, default: str = "#ffffff") -> str:
    """Convert a theme colour (possibly with alpha) to a tkinter #RRGGBB string."""
    if isinstance(color, str) and color.startswith("#"):
        if len(color) == 9:
            return color[:7]
        if len(color) == 7:
            return color
    return default


def _tk_font(spec) -> Tuple[str, int, str]:
    """Convert a theme font spec (family, size, weight) to a tkinter font tuple."""
    if not isinstance(spec, (tuple, list)) or len(spec) < 2:
        return ("TkDefaultFont", 12, "normal")
    family = spec[0]
    size = int(spec[1])
    weight = spec[2] if len(spec) > 2 else ""
    parts: List[str] = []
    if "bold" in weight.lower():
        parts.append("bold")
    if "italic" in weight.lower():
        parts.append("italic")
    style = " ".join(parts) if parts else "normal"
    return (family, size, style)


# ------------------------------------------------------------------
# OptionButton wrapper
# ------------------------------------------------------------------

class OptionButton:
    """Wrapper around tk.Button with hover states."""

    def __init__(
        self,
        parent: tk.Widget,
        index: int,
        trigger: Callable[[int], None],
        *,
        fg: str,
        bg: str,
        hover_bg: str,
        active_bg: str,
        disabled_bg: str,
        disabled_fg: str,
        font: Tuple[str, int, str],
    ) -> None:
        self._index = index
        self._trigger = trigger
        self._bg = bg
        self._hover_bg = hover_bg
        self._disabled_bg = disabled_bg

        self._btn = tk.Button(
            parent,
            text="",
            command=self._handle_click,
            relief="flat",
            bd=0,
            fg=fg,
            bg=bg,
            activebackground=active_bg,
            activeforeground=fg,
            disabledforeground=disabled_fg,
            highlightbackground=bg,
            highlightthickness=0,
            font=font,
            cursor="hand2",
            anchor="center",
            padx=18,
            pady=12,
        )
        self._btn.bind("<Enter>", self._on_enter)
        self._btn.bind("<Leave>", self._on_leave)
        self._row = index // 2
        self._col = index % 2
        self._visible = False

    def grid(self, **kwargs: Any) -> None:
        self._btn.grid(row=self._row, column=self._col, sticky="nsew", padx=6, pady=6, **kwargs)
        self._visible = True

    def grid_remove(self) -> None:
        self._btn.grid_remove()
        self._visible = False

    def show(self) -> None:
        if not self._visible:
            self.grid()

    def hide(self) -> None:
        if self._visible:
            self.grid_remove()

    def set_text(self, text: str) -> None:
        self._btn.config(text=text)

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self._btn.config(state="normal", bg=self._bg, highlightbackground=self._bg)
        else:
            self._btn.config(state="disabled", bg=self._disabled_bg, highlightbackground=self._disabled_bg)

    def _on_enter(self, _event: Any) -> None:
        if str(self._btn["state"]) != "disabled":
            self._btn.config(bg=self._hover_bg, highlightbackground=self._hover_bg)

    def _on_leave(self, _event: Any) -> None:
        if str(self._btn["state"]) != "disabled":
            self._btn.config(bg=self._bg, highlightbackground=self._bg)

    def _handle_click(self) -> None:
        if self._trigger:
            self._trigger(self._index)


# ------------------------------------------------------------------
# Inventory listbox wrapper
# ------------------------------------------------------------------

class _InventoryList:
    """Wrapper around tk.Listbox that stores item IDs alongside display text."""

    def __init__(self, parent: tk.Widget, height: int = 4, **kwargs: Any) -> None:
        self._listbox = tk.Listbox(
            parent,
            height=height,
            relief="flat",
            bd=0,
            highlightthickness=0,
            exportselection=False,
            activestyle="none",
            **kwargs,
        )
        self._item_ids: List[Optional[str]] = []

    @property
    def widget(self) -> tk.Listbox:
        return self._listbox

    def clear(self) -> None:
        self._listbox.delete(0, "end")
        self._item_ids.clear()

    def add_item(self, display_text: str, item_id: Optional[str] = None) -> None:
        self._listbox.insert("end", display_text)
        self._item_ids.append(item_id)

    def count(self) -> int:
        return self._listbox.size()

    def select(self, index: int) -> None:
        self._listbox.selection_clear(0, "end")
        if 0 <= index < self._listbox.size():
            self._listbox.selection_set(index)
            self._listbox.see(index)
            self._listbox.event_generate("<<ListboxSelect>>")

    def selected_item_id(self) -> Optional[str]:
        sel = self._listbox.curselection()
        if sel:
            idx = sel[0]
            if idx < len(self._item_ids):
                return self._item_ids[idx]
        return None

    def bind_select(self, callback: Callable[[], None]) -> None:
        self._listbox.bind("<<ListboxSelect>>", lambda _e: callback())

    def bind_activate(self, callback: Callable[[], None]) -> None:
        self._listbox.bind("<Double-Button-1>", lambda _e: callback())
        self._listbox.bind("<Return>", lambda _e: callback())


# ------------------------------------------------------------------
# GameApp
# ------------------------------------------------------------------

class GameApp:
    """Top-level tkinter application managing rooms, battles, and UI."""

    def __init__(
        self,
        rooms: Dict[str, RoomSpec],
        battles: Dict[str, BattleSpec],
        images: Dict[str, str],
        sounds: Dict[str, str],
        defaults_module: Any,
        root: tk.Tk,
    ) -> None:
        self.root = root

        self.rooms = rooms
        self.battles = battles
        self.images = images
        self.sounds = sounds
        self.defaults = defaults_module

        self.stats = self._build_stats(self.defaults.STARTING_STATS)
        self.inventory: Dict[str, int] = {}
        self.flags: Dict[str, int] = {}
        self.timed_flags: Dict[str, int] = {}
        self.alert_level: int = 0
        self.current_room_id: Optional[str] = None
        self.current_music_key: Optional[str] = None
        self.current_battle: Optional[Dict[str, Any]] = None
        self.option_handlers: List[Callable[[], None]] = []
        self._pending_room_transition: Optional[str] = None
        self._unique_loot_awards: Set[str] = set()
        self.equipment: Dict[str, Optional[str]] = {"melee": None, "ranged": None}
        self.battle_repeat_tracker: Dict[str, int] = {}
        self._mana_regen_reserve: float = 0.0

        self.theme: Dict[str, Any] = getattr(self.defaults, "UI_THEME", {})

        self._bg_photo: Optional[tk.PhotoImage] = None

        self._build_ui()
        start_room = self.defaults.START_ROOM_ID
        self.go_to(start_room, initial=True)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.root.title(getattr(self.defaults, "GAME_TITLE", "LevelKit-Text"))
        self.root.geometry(f"{self.defaults.WINDOW_WIDTH}x{self.defaults.WINDOW_HEIGHT}")
        self.root.minsize(800, 500)

        window_bg = _tk_color(self._theme("window", "background", default="#101010"), "#101010")
        self._window_bg = window_bg
        self.root.configure(bg=window_bg)

        # Canvas for background image
        self._canvas = tk.Canvas(self.root, highlightthickness=0, bg=window_bg)
        self._canvas.pack(fill="both", expand=True)
        self._bg_image_id = self._canvas.create_image(0, 0, anchor="center")

        # --- Header ---
        # Placed directly on the canvas so the background image shows through
        # the gap between header and bottom HUD panel.
        header_bg = _tk_color(self._theme("header", "panel_background", default="#202020cc"), "#202020")
        header_padding = self._int(self._theme("header", "padding", default=16), 16) + 8
        header_frame = tk.Frame(self._canvas, bg=header_bg, padx=header_padding, pady=header_padding)
        self._header_window = self._canvas.create_window(20, 20, anchor="nw", window=header_frame)

        # Title column
        title_frame = tk.Frame(header_frame, bg=header_bg)
        title_frame.pack(side="left", fill="both", expand=True)

        title_fg = _tk_color(self._theme("header", "title_foreground", default="#f0f0f0"), "#f0f0f0")
        title_font = _tk_font(self._theme("header", "title_font", default=("Segoe UI", 20, "bold")))
        game_title = getattr(self.defaults, "GAME_TITLE", "LevelKit-Text")
        self.title_label = tk.Label(
            title_frame, text=game_title, fg=title_fg, bg=header_bg,
            font=title_font, anchor="w",
        )
        self.title_label.pack(anchor="w")

        byline = getattr(self.defaults, "GAME_BYLINE", "")
        byline_fg = _tk_color(self._theme("header", "byline_foreground", default="#cccccc"), "#cccccc")
        byline_font = _tk_font(self._theme("header", "byline_font", default=("Segoe UI", 12, "")))
        self.byline_label = tk.Label(
            title_frame, text=byline, fg=byline_fg, bg=header_bg,
            font=byline_font, anchor="w",
        )
        if byline:
            self.byline_label.pack(anchor="w")

        # Stats column
        stats_fg = _tk_color(self._theme("header", "stats_foreground", default="#dedede"), "#dedede")
        stats_font_setting = self._theme("header", "stats_font", default=("Segoe UI", 14, ""))
        if isinstance(stats_font_setting, (tuple, list)) and len(stats_font_setting) >= 2:
            stats_family = stats_font_setting[0]
            stats_size = self._int(stats_font_setting[1], 14) + 4
            stats_weight = stats_font_setting[2] if len(stats_font_setting) > 2 else ""
            stats_font = _tk_font((stats_family, stats_size, stats_weight))
        else:
            stats_font = _tk_font(("Segoe UI", 18, ""))

        stats_frame = tk.Frame(header_frame, bg=header_bg)
        stats_frame.pack(side="right", padx=10)

        stat_order = [
            ("HP", "hp"),
            ("ATK", "attack"),
            ("LVL", "level"),
            ("MP", "mana"),
            ("DEF", "defence"),
            ("XP", "xp"),
        ]
        self._stat_labels: Dict[str, tk.Label] = {}
        for index, (_label_text, key) in enumerate(stat_order):
            row = index // 3
            col = index % 3
            label = tk.Label(
                stats_frame, text="", fg=stats_fg, bg=header_bg,
                font=stats_font, anchor="e",
            )
            label.grid(row=row, column=col, padx=12, pady=2, sticky="e")
            self._stat_labels[key] = label

        # --- Bottom HUD panel (dialogue + options + inventory) ---
        # Anchored to the canvas bottom so the background image shows in the
        # space between header and this panel.
        self._bottom_frame = tk.Frame(self._canvas, bg=window_bg)
        self._bottom_window = self._canvas.create_window(20, 0, anchor="sw", window=self._bottom_frame)
        bottom_frame = self._bottom_frame

        # Main column (dialogue + options)
        self._main_column = tk.Frame(bottom_frame, bg=window_bg)
        self._main_column.pack(side="left", fill="both", expand=True)
        main_column = self._main_column

        # Options panel (packed to bottom first so dialogue sits above)
        options_bg = _tk_color(self._theme("options", "panel_background", default="#1c1c1ccc"), "#1c1c1c")
        options_padding = self._int(self._theme("options", "padding", default=18), 18)
        options_frame = tk.Frame(main_column, bg=options_bg, padx=options_padding, pady=options_padding)
        options_frame.pack(side="bottom", fill="x", pady=(12, 0))

        button_fg = _tk_color(self._theme("options", "button_foreground", default="#f5f5f5"), "#f5f5f5")
        button_bg = _tk_color(self._theme("options", "button_background", default="#252525"), "#252525")
        button_hover = _tk_color(self._theme("options", "button_hover_background", default="#343434"), "#343434")
        button_active = _tk_color(self._theme("options", "button_active_background", default="#454545"), "#454545")
        button_disabled = _tk_color(self._theme("options", "button_disabled_background", default="#151515"), "#151515")
        button_disabled_fg = _tk_color(self._theme("options", "button_disabled_foreground", default="#7a7a7a"), "#7a7a7a")
        button_font = _tk_font(self._theme("options", "button_font", default=("Segoe UI", 12, "")))

        button_grid = tk.Frame(options_frame, bg=options_bg)
        button_grid.pack(fill="both", expand=True)
        button_grid.columnconfigure(0, weight=1)
        button_grid.columnconfigure(1, weight=1)
        button_grid.rowconfigure(0, weight=1)
        button_grid.rowconfigure(1, weight=1)

        self.option_buttons: List[OptionButton] = []
        for idx in range(4):
            button = OptionButton(
                button_grid, idx, self._on_option,
                fg=button_fg, bg=button_bg, hover_bg=button_hover,
                active_bg=button_active, disabled_bg=button_disabled,
                disabled_fg=button_disabled_fg, font=button_font,
            )
            button.hide()
            self.option_buttons.append(button)

        # Dialogue panel (above options)
        dialogue_bg = _tk_color(self._theme("dialogue", "panel_background", default="#1c1c1ccc"), "#1c1c1c")
        dialogue_padding = self._int(self._theme("dialogue", "padding", default=28), 28)
        dialogue_fg = _tk_color(self._theme("dialogue", "foreground", default="#f8f8f2"), "#f8f8f2")
        dialogue_font = _tk_font(self._theme("dialogue", "font", default=("Segoe UI", 14, "")))

        dialogue_frame = tk.Frame(main_column, bg=dialogue_bg, padx=dialogue_padding, pady=dialogue_padding)
        dialogue_frame.pack(side="bottom", fill="x")

        self.dialogue_label = tk.Label(
            dialogue_frame, text="", fg=dialogue_fg, bg=dialogue_bg,
            font=dialogue_font, wraplength=600, justify="center", anchor="center",
        )
        self.dialogue_label.pack(fill="both", expand=True)

        # --- Inventory sidebar ---
        inventory_bg = _tk_color(self._theme("inventory", "panel_background", default="#1c1c1ccc"), "#1c1c1c")
        inventory_padding = self._int(self._theme("inventory", "padding", default=18), 18)
        inventory_title_fg = _tk_color(self._theme("inventory", "title_foreground", default="#f0f0f0"), "#f0f0f0")
        inventory_title_font = _tk_font(self._theme("inventory", "title_font", default=("Segoe UI", 16, "bold")))
        list_fg = _tk_color(self._theme("inventory", "list_foreground", default="#f5f5f5"), "#f5f5f5")
        list_font = _tk_font(self._theme("inventory", "list_font", default=("Segoe UI", 12, "")))
        button_hover_color = _tk_color(self._theme("options", "button_hover_background", default="#343434"), "#343434")

        # Inventory is a separate canvas window on the right side so it stretches
        # the full height and the background image shows behind both HUD panels.
        self._inventory_frame = tk.Frame(
            self._canvas, bg=inventory_bg, padx=inventory_padding, pady=inventory_padding,
        )
        self._inventory_frame.pack_propagate(False)
        inv_width = max(180, int(self.defaults.WINDOW_WIDTH * 0.14))
        self._inventory_frame.config(width=inv_width)
        self._inventory_window = self._canvas.create_window(
            0, 20, anchor="ne", window=self._inventory_frame
        )

        # Inventory title
        self.inventory_title = tk.Label(
            self._inventory_frame, text="Inventory", fg=inventory_title_fg,
            bg=inventory_bg, font=inventory_title_font, anchor="w",
        )
        self.inventory_title.pack(anchor="w", pady=(0, 8))

        # Equipped section
        equipped_font = _tk_font(self._theme("inventory", "section_font", default=("Segoe UI", 12, "bold")))

        self.inventory_equipped_label = tk.Label(
            self._inventory_frame, text="Equipped", fg=inventory_title_fg,
            bg=inventory_bg, font=equipped_font, anchor="w",
        )
        # Initially hidden
        self._equipped_label_visible = False

        self.inventory_equipped_container = tk.Frame(self._inventory_frame, bg=inventory_bg)
        self._equipped_container_visible = False

        self.inventory_equipped_sections: Dict[str, Dict[str, Any]] = {}
        for slot in ("melee", "ranged", "magic"):
            section_widget = tk.Frame(self.inventory_equipped_container, bg=inventory_bg)

            slot_label = tk.Label(
                section_widget, text=slot.capitalize(), fg=inventory_title_fg,
                bg=inventory_bg, font=equipped_font, anchor="w",
            )
            slot_label.pack(anchor="w")

            inv_list = _InventoryList(
                section_widget, height=2,
                bg=inventory_bg, fg=list_fg, font=list_font,
                selectbackground=button_hover_color,
            )
            inv_list.widget.pack(fill="x")
            inv_list.bind_activate(lambda lst=inv_list: self._inventory_activate_from_list(lst))
            inv_list.bind_select(lambda lst=inv_list: self._on_inventory_selection_changed_from_list(lst))

            self.inventory_equipped_sections[slot] = {
                "widget": section_widget,
                "list": inv_list,
                "_visible": False,
            }

        # Backpack section
        self.inventory_backpack_label = tk.Label(
            self._inventory_frame, text="Backpack", fg=inventory_title_fg,
            bg=inventory_bg, font=equipped_font, anchor="w",
        )
        self.inventory_backpack_label.pack(anchor="w", pady=(8, 0))

        self.inventory_backpack_list = _InventoryList(
            self._inventory_frame, height=8,
            bg=inventory_bg, fg=list_fg, font=list_font,
            selectbackground=button_hover_color,
        )
        self.inventory_backpack_list.widget.pack(fill="both", expand=True)
        self.inventory_backpack_list.bind_activate(
            lambda: self._inventory_activate_from_list(self.inventory_backpack_list)
        )
        self.inventory_backpack_list.bind_select(
            lambda: self._on_inventory_selection_changed_from_list(self.inventory_backpack_list)
        )

        # Detail label
        detail_fg = _tk_color(self._theme("inventory", "detail_foreground", default="#dcdcdc"), "#dcdcdc")
        detail_font = _tk_font(self._theme("inventory", "detail_font", default=("Segoe UI", 11, "")))
        self.inventory_detail_label = tk.Label(
            self._inventory_frame, text="", fg=detail_fg, bg=inventory_bg,
            font=detail_font, wraplength=160, justify="left", anchor="nw",
        )
        self.inventory_detail_label.pack(anchor="w", pady=(4, 0))

        # Hint label
        hint_fg = _tk_color(self._theme("inventory", "hint_foreground", default="#bbbbbb"), "#bbbbbb")
        hint_font = _tk_font(self._theme("inventory", "hint_font", default=("Segoe UI", 10, "")))
        self.inventory_hint_label = tk.Label(
            self._inventory_frame, text="Double-click or press Enter to use/equip",
            fg=hint_fg, bg=inventory_bg, font=hint_font, wraplength=160,
            justify="left", anchor="w",
        )
        self.inventory_hint_label.pack(anchor="w", pady=(4, 0))

        # --- Resize + keyboard + close ---
        self._canvas.bind("<Configure>", self._on_resize)
        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _theme(self, *keys: str, default: Any = None) -> Any:
        value: Any = self.theme
        for key in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(key, default)
        return value

    @staticmethod
    def _int(value: Any, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _ratio(value: Any, fallback: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = fallback
        return max(0.0, min(1.0, numeric))

    @staticmethod
    def _solid_color(color: str, fallback: str) -> str:
        if isinstance(color, str) and color.startswith("#") and len(color) == 9:
            return color[:7]
        return color if isinstance(color, str) else fallback

    @staticmethod
    def _build_stats(starting: Dict[str, int]) -> Stats:
        return Stats(**starting)

    # ------------------------------------------------------------------
    # Background handling
    # ------------------------------------------------------------------
    def _apply_room_bg(self, color: str) -> None:
        """Set the canvas background colour for edges not covered by the image."""
        self._canvas.configure(bg=color)

    def _set_background(self, key: Optional[str]) -> None:
        self._bg_photo = None

        if not key:
            self._apply_room_bg(self._window_bg)
            self._canvas.itemconfig(self._bg_image_id, image="")
            return
        filename = self.images.get(key)
        if not filename:
            self._apply_room_bg(self._window_bg)
            self._canvas.itemconfig(self._bg_image_id, image="")
            return
        path = IMAGES_DIR / filename
        if not path.exists():
            self._apply_room_bg(self._window_bg)
            self._canvas.itemconfig(self._bg_image_id, image="")
            return
        try:
            photo = tk.PhotoImage(file=str(path))
        except tk.TclError:
            self._apply_room_bg(self._window_bg)
            self._canvas.itemconfig(self._bg_image_id, image="")
            return

        # Extract the dominant colour from pixel (0,0) of the image so every
        # layout frame matches the room backdrop on macOS where tk.Frame has
        # no true transparency.
        try:
            pix = photo.get(0, 0)
            room_bg = f"#{int(pix[0]):02x}{int(pix[1]):02x}{int(pix[2]):02x}"
        except Exception:
            room_bg = self._window_bg

        self._apply_room_bg(room_bg)
        self._bg_photo = photo
        self._canvas.itemconfig(self._bg_image_id, image=self._bg_photo)
        self._center_background()

    def _center_background(self) -> None:
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w > 1 and h > 1:
            self._canvas.coords(self._bg_image_id, w // 2, h // 2)

    def _on_resize(self, event: Any) -> None:
        inv_width = max(180, int(event.width * 0.14))

        # Inventory: right-side panel, full available height
        inv_h = max(100, event.height - 40)
        self._canvas.itemconfig(self._inventory_window, width=inv_width, height=inv_h)
        self._canvas.coords(self._inventory_window, event.width - 20, 20)
        self._inventory_frame.config(width=inv_width)

        # Header and bottom panel sit to the left of the inventory
        content_width = max(200, event.width - inv_width - 60)
        self._canvas.itemconfig(self._header_window, width=content_width)
        self._canvas.itemconfig(self._bottom_window, width=content_width)
        self._canvas.coords(self._bottom_window, 20, event.height - 20)

        self._center_background()

        # Dialogue wraplength based on content column width
        self.dialogue_label.config(wraplength=max(200, int(content_width * 0.9)))

        # Inventory detail wraplength
        detail_wrap = max(100, inv_width - 30)
        self.inventory_detail_label.config(wraplength=detail_wrap)
        self.inventory_hint_label.config(wraplength=detail_wrap)

    # ------------------------------------------------------------------
    # Dialogue and options
    # ------------------------------------------------------------------
    def set_dialogue(self, text: str) -> None:
        self.dialogue_label.config(text=text)

    def _append_dialogue(self, text: str) -> None:
        current = self.dialogue_label.cget("text")
        combined = f"{current}\n{text}" if current else text
        self.dialogue_label.config(text=combined)

    def set_options(self, options: List[Tuple[Any, ...]]) -> None:
        limited = options[: len(self.option_buttons)]
        self.option_handlers = []
        for idx, button in enumerate(self.option_buttons):
            if idx < len(limited):
                option = limited[idx]
                label: str
                handler: Callable[[], None]
                enabled = True
                if len(option) >= 3:
                    label, handler, enabled = option[0], option[1], bool(option[2])
                else:
                    label, handler = option[0], option[1]
                self.option_handlers.append(handler)
                button.set_text(f"{idx + 1}. {label}")
                button.show()
                button.set_enabled(enabled)
            else:
                button.hide()
        if len(self.option_handlers) < len(limited):
            self.option_handlers.extend([lambda: None] * (len(limited) - len(self.option_handlers)))

    def _on_option(self, index: int) -> None:
        if index >= len(self.option_handlers):
            return
        handler = self.option_handlers[index]
        handler()

    def update_stats_display(self) -> None:
        level, xp_progress, xp_target = self._calculate_level_progress()
        values = {
            "hp": f"HP {self.stats.hp}/{self.stats.max_hp}",
            "mana": f"MP {self.stats.mana}/{self.stats.max_mana}",
            "attack": f"ATK {self.stats.attack}",
            "defence": f"DEF {self.stats.defence}",
            "level": f"LVL {level}",
            "xp": f"XP {xp_progress}/{xp_target}",
        }
        for key, label in self._stat_labels.items():
            label.config(text=values.get(key, ""))

    def _calculate_level_progress(self) -> Tuple[int, int, int]:
        total_xp = max(0, int(self.stats.xp))
        curve = getattr(self.defaults, "XP_CURVE", None)
        if callable(curve):
            level, progress, target = curve(total_xp)
            level = max(1, int(level))
            progress = max(0, int(progress))
            target = max(1, int(target))
            return level, progress, target
        xp_per_level = max(1, int(getattr(self.defaults, "XP_PER_LEVEL", 100)))
        level = 1 + total_xp // xp_per_level
        progress = total_xp % xp_per_level
        return level, progress, xp_per_level

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------
    def _inventory_activate_from_list(self, inv_list: _InventoryList) -> None:
        item_id = inv_list.selected_item_id()
        if not item_id:
            return
        if self._use_item(item_id):
            if self.inventory.get(item_id, 0) <= 0:
                self.inventory.pop(item_id, None)
            self._refresh_inventory_panel()

    def _on_inventory_selection_changed_from_list(self, inv_list: _InventoryList) -> None:
        item_id = inv_list.selected_item_id()
        if not item_id:
            self.inventory_detail_label.config(text="")
            return
        definition = self._item_definition(item_id)
        description = definition.get("description", "")
        extra_lines: List[str] = []
        slot = self._equipped_slot(item_id)
        if slot:
            extra_lines.append(f"Currently equipped in {slot} slot.")
        category = definition.get("category", "")
        if category == "weapon" or definition.get("weapon_type"):
            weapon_type = self._weapon_slot(definition)
            extra_lines.append(f"Weapon type: {weapon_type.capitalize()}")
            ammo_item = definition.get("ammo_item")
            if ammo_item:
                ammo_name = self._item_name(ammo_item)
                ammo_per_use = max(1, int(definition.get("ammo_per_use", 1)))
                extra_lines.append(f"Consumes {ammo_per_use} {ammo_name} per attack.")
        elif category == "ammo":
            extra_lines.append("Ammo is spent automatically by ranged weapons.")
        detail_text = description
        if extra_lines:
            detail_text = f"{description}\n" + "\n".join(extra_lines) if description else "\n".join(extra_lines)
        self.inventory_detail_label.config(text=detail_text)

    def _refresh_inventory_panel(self) -> None:
        all_lists = [section["list"] for section in self.inventory_equipped_sections.values()]
        all_lists.append(self.inventory_backpack_list)
        for inv_list in all_lists:
            inv_list.clear()

        has_equipped = False
        first_equipped_list: Optional[_InventoryList] = None
        for slot, section in self.inventory_equipped_sections.items():
            inv_list: _InventoryList = section["list"]
            item_id = self.equipment.get(slot)
            if item_id:
                name = self._item_name(item_id)
                inv_list.add_item(name, item_id)
                if not section["_visible"]:
                    section["widget"].pack(anchor="w", fill="x")
                    section["_visible"] = True
                if not has_equipped:
                    first_equipped_list = inv_list
                has_equipped = True
            else:
                if section["_visible"]:
                    section["widget"].pack_forget()
                    section["_visible"] = False

        if has_equipped:
            if not self._equipped_label_visible:
                self.inventory_equipped_label.pack(anchor="w", before=self.inventory_backpack_label)
                self._equipped_label_visible = True
            if not self._equipped_container_visible:
                self.inventory_equipped_container.pack(anchor="w", fill="x", before=self.inventory_backpack_label)
                self._equipped_container_visible = True
        else:
            if self._equipped_label_visible:
                self.inventory_equipped_label.pack_forget()
                self._equipped_label_visible = False
            if self._equipped_container_visible:
                self.inventory_equipped_container.pack_forget()
                self._equipped_container_visible = False

        backpack_counts: Dict[str, int] = {k: int(v) for k, v in self.inventory.items()}
        for item_id in self.equipment.values():
            if not item_id:
                continue
            if item_id in backpack_counts:
                backpack_counts[item_id] -= 1
                if backpack_counts[item_id] <= 0:
                    backpack_counts.pop(item_id, None)

        if backpack_counts:
            for item_id, count in backpack_counts.items():
                name = self._item_name(item_id)
                suffix = f" x{count}" if count > 1 else ""
                self.inventory_backpack_list.add_item(f"{name}{suffix}", item_id)
        else:
            self.inventory_backpack_list.add_item("Empty", None)

        if has_equipped and first_equipped_list and first_equipped_list.count() > 0:
            first_equipped_list.select(0)
        else:
            first_selectable = -1
            for i in range(self.inventory_backpack_list.count()):
                if self.inventory_backpack_list._item_ids[i] is not None:
                    first_selectable = i
                    break
            if first_selectable >= 0:
                self.inventory_backpack_list.select(first_selectable)
            else:
                self.inventory_detail_label.config(text="")

    def open_inventory(self, _event: Any = None) -> None:
        if not self.inventory:
            messagebox.showinfo("Inventory", "Your inventory is empty.")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Inventory")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("350x400")

        inv_bg = _tk_color(self._theme("inventory", "panel_background", default="#1c1c1ccc"), "#1c1c1c")
        list_fg = _tk_color(self._theme("inventory", "list_foreground", default="#f5f5f5"), "#f5f5f5")
        list_font = _tk_font(self._theme("inventory", "list_font", default=("Segoe UI", 12, "")))

        dialog.configure(bg=inv_bg)

        inv_list = _InventoryList(
            dialog, height=15, bg=inv_bg, fg=list_fg, font=list_font,
            selectbackground=_tk_color(self._theme("options", "button_hover_background", default="#343434"), "#343434"),
        )
        for item_id, count in self.inventory.items():
            name = self._item_name(item_id)
            suffix = f" x{count}" if count > 1 else ""
            slot = self._equipped_slot(item_id)
            equipped_tag = f" [Equipped: {slot.capitalize()}]" if slot else ""
            inv_list.add_item(f"{name}{suffix}{equipped_tag}", item_id)
        inv_list.widget.pack(fill="both", expand=True, padx=10, pady=10)
        inv_list.bind_activate(lambda: self._dialog_use_item(inv_list, dialog))

        use_btn = tk.Button(
            dialog, text="Use", command=lambda: self._dialog_use_item(inv_list, dialog),
            relief="flat", bd=0, bg="#252525", fg="#f5f5f5", activebackground="#454545",
            font=list_font, padx=12, pady=6,
        )
        use_btn.pack(pady=10)

        self.root.wait_window(dialog)

    def _dialog_use_item(self, inv_list: _InventoryList, dialog: tk.Toplevel) -> None:
        item_id = inv_list.selected_item_id()
        if not item_id:
            return
        definition = self._item_definition(item_id)
        if self._use_item(item_id):
            if definition.get("category") == "weapon" or definition.get("weapon_type"):
                self._refresh_inventory_panel()
                return
            if self.inventory.get(item_id, 0) <= 0:
                self.inventory.pop(item_id, None)
            self._refresh_inventory_panel()
            dialog.destroy()

    # ------------------------------------------------------------------
    # Item helpers
    # ------------------------------------------------------------------
    def _item_definition(self, item_id: str) -> Dict[str, Any]:
        if item_id in self.defaults.ITEM_DEFINITIONS:
            return self.defaults.ITEM_DEFINITIONS[item_id]
        if item_id in DEFAULT_ITEM_DEFINITIONS:
            return DEFAULT_ITEM_DEFINITIONS[item_id]
        return {"name": item_id, "description": "", "effects": {}}

    def _item_name(self, item_id: str) -> str:
        definition = self._item_definition(item_id)
        return str(definition.get("name", item_id))

    def _use_item(self, item_id: str) -> bool:
        if item_id not in self.inventory:
            return False
        definition = self._item_definition(item_id)
        category = definition.get("category", "")
        if category == "weapon" or definition.get("weapon_type"):
            equipped = self._equip_weapon(item_id, definition)
            if equipped and self.current_battle:
                self._refresh_battle_actions(self.current_battle["spec"])
            return equipped
        if category == "ammo":
            messagebox.showinfo(
                "Inventory",
                "Ammo is used automatically by ranged weapons during combat.",
            )
            return False
        effects = definition.get("effects", {})
        for stat_name, delta in effects.items():
            if hasattr(self.stats, stat_name):
                value = getattr(self.stats, stat_name) + int(delta)
                if stat_name == "hp":
                    value = min(self.stats.max_hp, max(0, value))
                setattr(self.stats, stat_name, value)
        if definition.get("category") == "consumable":
            self.inventory[item_id] -= 1
            if self.inventory[item_id] <= 0:
                self.inventory.pop(item_id, None)
        self.update_stats_display()
        messagebox.showinfo("Inventory", f"Used {definition.get('name', item_id)}.")
        return True

    def _equip_weapon(self, item_id: str, definition: Dict[str, Any], *, notify: bool = True) -> bool:
        slot = self._weapon_slot(definition)
        current = self.equipment.get(slot)
        if current == item_id:
            if notify:
                messagebox.showinfo(
                    "Inventory",
                    f"{self._item_name(item_id)} is already equipped.",
                )
            return False
        if current:
            self._unequip_weapon(slot)
        self.equipment[slot] = item_id
        self._apply_weapon_effects(definition, remove=False)
        self.update_stats_display()
        self._refresh_inventory_panel()
        if notify:
            messagebox.showinfo(
                "Inventory",
                f"Equipped {self._item_name(item_id)} to your {slot} slot.",
            )
        return True

    def _unequip_weapon(self, slot: str) -> None:
        weapon_id = self.equipment.get(slot)
        if not weapon_id:
            return
        definition = self._item_definition(weapon_id)
        self._apply_weapon_effects(definition, remove=True)
        self.equipment[slot] = None
        self._refresh_inventory_panel()

    def _apply_weapon_effects(self, definition: Dict[str, Any], *, remove: bool) -> None:
        effects = definition.get("effects", {})
        for stat_name, delta in effects.items():
            if hasattr(self.stats, stat_name):
                change = int(delta)
                if remove:
                    change = -change
                setattr(self.stats, stat_name, getattr(self.stats, stat_name) + change)

    def _weapon_slot(self, definition: Dict[str, Any]) -> str:
        weapon_type = str(definition.get("weapon_type", "melee")).lower()
        return "ranged" if weapon_type == "ranged" else "melee"

    def _equipped_slot(self, item_id: str) -> Optional[str]:
        for slot, equipped in self.equipment.items():
            if equipped == item_id:
                return slot
        return None

    def _consume_inventory(self, item_id: str, amount: int) -> None:
        if amount <= 0:
            return
        current = self.inventory.get(item_id, 0)
        remaining = current - amount
        if remaining <= 0:
            self.inventory.pop(item_id, None)
        else:
            self.inventory[item_id] = remaining
        self._refresh_inventory_panel()

    # ------------------------------------------------------------------
    # Room & battle handling
    # ------------------------------------------------------------------
    def go_to(self, room_id: str, initial: bool = False) -> None:
        room = self.rooms.get(room_id)
        if not room:
            self.set_dialogue(f"Room '{room_id}' is missing.")
            return
        expired_messages: List[str] = []
        if not initial:
            expired_messages = self._tick_timed_flags()
            self._regen_mana()
        self.current_room_id = room_id
        self.current_battle = None
        game_title = getattr(self.defaults, "GAME_TITLE", "LevelKit-Text")
        room_title = room.title
        display_title = f"{game_title} - {room_title}" if room_title else game_title
        self.title_label.config(text=display_title)
        self._set_background(room.background_key)
        self._set_music(room.music_key)
        if getattr(room, "enter_sound_key", None):
            audio.play_effect(room.enter_sound_key, self.sounds, SOUNDS_DIR)
        self.set_dialogue(room.body)
        options = self._build_room_options(room)
        if not options:
            options.append(("Catch your breath.", lambda: None))
        self.set_options(options)
        for message in expired_messages:
            self._append_dialogue(message)
        self.update_stats_display()

    def _build_room_options(self, room: RoomSpec) -> List[Tuple[str, Callable[[], None]]]:
        options: List[Tuple[str, Callable[[], None]]] = []
        for option in room.options:
            if not self._option_available(option):
                continue
            label = option.label
            hint = getattr(option, "hint", None)
            if hint:
                label = f"{label} ({hint})"
            options.append((label, lambda opt=option: self._handle_room_option(opt)))
        return options

    def _option_available(self, option: Any) -> bool:
        required_flag = getattr(option, "requires_flag", None)
        if required_flag and self._flag_value(required_flag) <= 0:
            return False
        forbidden_flag = getattr(option, "requires_not_flag", None)
        if forbidden_flag and self._flag_value(forbidden_flag) > 0:
            return False
        require_expr = getattr(option, "require_expr", None)
        if isinstance(require_expr, dict) and not self._evaluate_requirement(require_expr):
            return False
        return True

    def _flag_value(self, flag: str) -> int:
        return int(self.flags.get(flag, 0))

    def _set_flag(self, flag: str, value: int) -> bool:
        current = self.flags.get(flag)
        normalized = int(value)
        if current == normalized:
            return False
        self.flags[flag] = normalized
        return True

    def _clear_flag(self, flag: str) -> bool:
        removed = self.flags.pop(flag, None) is not None
        self.timed_flags.pop(flag, None)
        return removed

    def _evaluate_requirement(self, expr: Dict[str, Any]) -> bool:
        if not isinstance(expr, dict):
            return False
        if "flag" in expr:
            return self._flag_value(str(expr["flag"])) > 0
        if "not_flag" in expr:
            return self._flag_value(str(expr["not_flag"])) == 0
        if "min" in expr:
            requirements = expr.get("min", {})
            if not isinstance(requirements, dict):
                return False
            for key, value in requirements.items():
                if self._flag_value(str(key)) < int(value):
                    return False
            return True
        if "alert_below" in expr:
            return self.alert_level < int(expr["alert_below"])
        if "all" in expr:
            conditions = expr.get("all", [])
            return all(self._evaluate_requirement(cond) for cond in conditions if isinstance(cond, dict))
        if "any" in expr:
            conditions = expr.get("any", [])
            return any(self._evaluate_requirement(cond) for cond in conditions if isinstance(cond, dict))
        return True

    def _tick_timed_flags(self) -> List[str]:
        expired_messages: List[str] = []
        for flag in list(self.timed_flags):
            remaining = self.timed_flags[flag] - 1
            if remaining <= 0:
                self.timed_flags.pop(flag, None)
                if self.flags.pop(flag, None) is not None:
                    human_name = flag.replace("_", " ").capitalize()
                    expired_messages.append(f"{human_name} fades.")
            else:
                self.timed_flags[flag] = remaining
        return expired_messages

    def _battle_repeat_key(self, option: OptionSpec) -> str:
        if option.battle_repeat_key:
            return option.battle_repeat_key
        label = getattr(option, "label", "option").strip().lower().replace(" ", "_")
        room_id = self.current_room_id or "room"
        return f"{room_id}:{label}"

    def _handle_room_option(self, option: Any) -> None:
        message, needs_refresh = self._apply_option_effects(option)

        if option.battle_id:
            repeat_key: Optional[str] = None
            limit = getattr(option, "battle_repeat_limit", None)
            if limit is not None and limit > 0:
                repeat_key = self._battle_repeat_key(option)
                if self.battle_repeat_tracker.get(repeat_key, 0) >= limit:
                    repeat_message = option.battle_repeat_message or "The encounter no longer responds."
                    self._append_dialogue(repeat_message)
                    return
            battle = self.battles.get(option.battle_id)
            if not battle:
                self.set_dialogue(f"Battle '{option.battle_id}' not found.")
                return
            self.start_battle(battle, option.to, repeat_key=repeat_key)
            return
        if option.to:
            self.go_to(option.to)
            return
        if message:
            self._append_dialogue(message)
        else:
            self._append_dialogue("You wait, but nothing happens.")
        if needs_refresh:
            self._refresh_current_room_options()

    def start_battle(
        self,
        battle: BattleSpec,
        option_default_to: Optional[str],
        repeat_key: Optional[str] = None,
    ) -> None:
        stunned_turns = max(0, int(self.flags.pop("enemy_stunned", 0)))
        self.current_battle = {
            "spec": battle,
            "option_to": option_default_to,
            "enemy_hp": battle.enemy.hp,
            "repeat_key": repeat_key,
        }
        if stunned_turns:
            reduction = min(self.current_battle["enemy_hp"], stunned_turns * 4)
            self.current_battle["enemy_hp"] -= reduction
            opening = (
                f"{battle.title}\n"
                f"{battle.enemy.name} reels from your setup, losing {reduction} HP before the fight truly begins!"
            )
        else:
            opening = f"{battle.title}\n{battle.enemy.name} prepares to strike!"
        self.set_dialogue(opening)
        self._refresh_battle_actions(battle)

    def _battle_action_available(self, action: BattleAction) -> Tuple[bool, Optional[str]]:
        required_weapon_type = getattr(action, "requires_weapon_type", None)
        required_weapon_id = getattr(action, "requires_weapon_id", None)
        if required_weapon_type:
            equipped = self.equipment.get(required_weapon_type)
            if not equipped:
                return False, f"Requires {required_weapon_type} weapon"
            if required_weapon_id and equipped != required_weapon_id:
                item_name = self._item_name(required_weapon_id)
                return False, f"Requires {item_name}"
        elif required_weapon_id:
            if required_weapon_id not in self.equipment.values():
                item_name = self._item_name(required_weapon_id)
                return False, f"Requires {item_name}"
        ammo_item = getattr(action, "ammo_item", None)
        if ammo_item:
            ammo_cost = max(0, int(getattr(action, "ammo_cost", 1)))
            if self.inventory.get(ammo_item, 0) < ammo_cost:
                return False, "Out of ammo"
        return True, None

    def _refresh_battle_actions(self, battle: Optional[BattleSpec] = None) -> None:
        if not self.current_battle:
            return
        if battle is None:
            battle = self.current_battle["spec"]
        options: List[Tuple[str, Callable[[], None], bool]] = []
        for action in battle.actions:
            available, reason = self._battle_action_available(action)
            if not available and not getattr(action, "show_if_unavailable", False):
                continue
            label = action.label
            if not available and reason:
                label = f"{label} ({reason})"
            options.append((label, lambda act=action: self._resolve_battle_action(act), available))
        if not options:
            options.append(("Endure", self._pass_turn, True))
        self.set_options(options)

    def _pass_turn(self) -> None:
        if not self.current_battle:
            return
        battle: BattleSpec = self.current_battle["spec"]  # type: ignore[assignment]
        log_lines: List[str] = [battle.title, "You take a defensive stance."]
        log_lines.extend(self._enemy_attack(battle))
        self.update_stats_display()
        if self.stats.hp <= 0:
            self._handle_defeat()
            return
        self.set_dialogue("\n".join(log_lines))
        self._refresh_battle_actions(battle)

    def _resolve_battle_action(self, action: BattleAction) -> None:
        if not self.current_battle:
            return
        battle: BattleSpec = self.current_battle["spec"]  # type: ignore[assignment]
        log_lines: List[str] = [battle.title]

        available, reason = self._battle_action_available(action)
        if not available:
            log_lines.append(reason or "You cannot take that action right now.")
            log_lines.extend(self._enemy_attack(battle))
            self.update_stats_display()
            if self.stats.hp <= 0:
                self._handle_defeat()
                return
            self.set_dialogue("\n".join(log_lines))
            self._refresh_battle_actions(battle)
            return

        ammo_item = getattr(action, "ammo_item", None)
        ammo_cost = max(0, int(getattr(action, "ammo_cost", 1)))
        if ammo_item and ammo_cost:
            if self.inventory.get(ammo_item, 0) < ammo_cost:
                log_lines.append("Out of ammo!")
                log_lines.extend(self._enemy_attack(battle))
                self.update_stats_display()
                if self.stats.hp <= 0:
                    self._handle_defeat()
                    return
                self.set_dialogue("\n".join(log_lines))
                self._refresh_battle_actions(battle)
                return
            self._consume_inventory(ammo_item, ammo_cost)

        if action.kind in ("attack", "cast"):
            chance = float(getattr(action, "hit_chance", 1.0))
            chance = max(0.0, min(1.0, chance))
            if chance < 1.0 and random.random() > chance:
                log_lines.append(f"{action.label} misses.")
                log_lines.extend(self._enemy_attack(battle))
                self.update_stats_display()
                if self.stats.hp <= 0:
                    self._handle_defeat()
                    return
                self.set_dialogue("\n".join(log_lines))
                self._refresh_battle_actions(battle)
                return

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
        if self.current_battle:
            self._refresh_battle_actions(battle)

    def _calculate_player_damage(self, bonus: int, variance: int) -> int:
        total_variance = max(0, variance + getattr(self.defaults, "DAMAGE_VARIANCE", 0))
        roll = random.randint(0, total_variance)
        damage = max(0, (self.stats.attack + bonus + roll))
        if self.current_battle:
            damage -= self.current_battle["spec"].enemy.defence
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
        self.stats.xp += getattr(self.defaults, "XP_PER_VICTORY", 0)
        self._collect_loot(battle.enemy.loot)
        table_loot = self._roll_loot_table(battle.loot_table, battle.loot_rolls)
        if table_loot:
            self._collect_loot(table_loot)
        next_room = battle.victory_to or self.current_battle.get("option_to") or self.current_room_id
        repeat_key = self.current_battle.get("repeat_key")
        if repeat_key:
            self.battle_repeat_tracker[repeat_key] = self.battle_repeat_tracker.get(repeat_key, 0) + 1
        self.current_battle = None
        self.update_stats_display()
        self._prepare_room_transition(next_room)

    def _handle_defeat(self) -> None:
        if not self.current_battle:
            return
        battle: BattleSpec = self.current_battle["spec"]
        self.set_dialogue(battle.defeat_text)
        self.stats.hp = self.stats.max_hp
        defeat_room = battle.defeat_to or getattr(self.defaults, "DEFEAT_ROOM_ID", self.defaults.START_ROOM_ID)
        self.current_battle = None
        self.update_stats_display()
        self._prepare_room_transition(defeat_room, label="Continue")

    def _collect_loot(self, items: List[str]) -> None:
        if not items:
            return
        counts = Counter(items)
        display: List[str] = []
        for item_id, count in counts.items():
            self.inventory[item_id] = self.inventory.get(item_id, 0) + count
            name = self._item_name(item_id)
            suffix = f" x{count}" if count > 1 else ""
            display.append(f"{name}{suffix}")
        loot_text = ", ".join(display)
        self._append_dialogue(f"Loot acquired: {loot_text}.")
        self._refresh_inventory_panel()

    # ------------------------------------------------------------------
    # Mana regeneration and music
    # ------------------------------------------------------------------
    def _regen_mana(self) -> None:
        regen_value = float(getattr(self.defaults, "MANA_PER_ROOM", 0.0))
        if regen_value <= 0.0:
            return
        self._mana_regen_reserve += regen_value
        points = int(self._mana_regen_reserve)
        if points <= 0:
            return
        self._mana_regen_reserve -= points
        self.stats.mana = min(self.stats.max_mana, self.stats.mana + points)

    def _set_music(self, key: Optional[str]) -> None:
        if key == self.current_music_key:
            return
        self.current_music_key = key
        audio.play_music(key, self.sounds, SOUNDS_DIR)

    def on_close(self) -> None:
        audio.stop_music()
        self.root.destroy()

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------
    def _bind_shortcuts(self) -> None:
        self.root.bind_all("<Key-1>", lambda _e: self._on_option(0))
        self.root.bind_all("<Key-2>", lambda _e: self._on_option(1))
        self.root.bind_all("<Key-3>", lambda _e: self._on_option(2))
        self.root.bind_all("<Key-4>", lambda _e: self._on_option(3))
        self.root.bind_all("<Key-i>", self.open_inventory)

    def _apply_option_effects(self, option: OptionSpec) -> Tuple[str, bool]:
        messages: List[str] = []
        requires_refresh = False
        stats_changed = False
        fail_triggered = False
        if option.sound_key:
            audio.play_effect(option.sound_key, self.sounds, SOUNDS_DIR)
        gained_items: List[str] = list(option.gain_items or [])
        rolled_loot = self._roll_loot_table(option.loot_table, option.loot_rolls)
        if rolled_loot:
            gained_items.extend(rolled_loot)
        if gained_items:
            counts = Counter(gained_items)
            display = []
            for item_id, count in counts.items():
                self.inventory[item_id] = self.inventory.get(item_id, 0) + count
                name = self._item_name(item_id)
                suffix = f" x{count}" if count > 1 else ""
                display.append(f"{name}{suffix}")
            self._refresh_inventory_panel()
            messages.append(f"You obtain: {', '.join(display)}.")
            requires_refresh = True
        if option.set_flag and self._set_flag(option.set_flag, 1):
            requires_refresh = True
        effects = getattr(option, "effects", {}) or {}
        if not isinstance(effects, dict):
            effects = {}
        equip_targets = effects.get("equip_item")
        if equip_targets:
            if isinstance(equip_targets, str):
                equip_ids = [equip_targets]
            elif isinstance(equip_targets, (list, tuple, set)):
                equip_ids = [str(item) for item in equip_targets if isinstance(item, str)]
            else:
                equip_ids = []
            for item_id in equip_ids:
                if self.inventory.get(item_id, 0) <= 0:
                    continue
                definition = self._item_definition(item_id)
                if definition.get("category") != "weapon" and not definition.get("weapon_type"):
                    continue
                equipped = self._equip_weapon(item_id, definition, notify=False)
                if equipped:
                    messages.append(f"{self._item_name(item_id)} equipped.")
                    requires_refresh = True
        timer_rooms_value: Optional[int] = None
        raw_timer = effects.get("timer_rooms")
        if isinstance(raw_timer, (int, float)):
            timer_rooms_value = max(0, int(raw_timer))
        hp_fail_effect = 0
        set_map = effects.get("set", {})
        if isinstance(set_map, dict):
            for flag, value in set_map.items():
                if self._set_flag(str(flag), int(value)):
                    requires_refresh = True
                if timer_rooms_value and timer_rooms_value > 0:
                    self.timed_flags[str(flag)] = timer_rooms_value
        inc_map = effects.get("inc", {})
        if isinstance(inc_map, dict):
            for flag, amount in inc_map.items():
                new_value = self.flags.get(flag, 0) + int(amount)
                if self._set_flag(str(flag), new_value):
                    requires_refresh = True
        energy_cost = effects.get("energy_cost")
        if isinstance(energy_cost, (int, float)):
            cost = max(0, int(energy_cost))
            if cost:
                self.stats.stamina = max(0, self.stats.stamina - cost)
                stats_changed = True
                messages.append(f"You expend {cost} stamina.")
        alert_delta = effects.get("alert")
        if isinstance(alert_delta, (int, float)):
            change = int(alert_delta)
            if change:
                self.alert_level = max(0, self.alert_level + change)
                messages.append("Facility alert increases.")
        enemy_stunned = effects.get("enemy_stunned")
        if isinstance(enemy_stunned, (int, float)):
            if self._set_flag("enemy_stunned", int(enemy_stunned)):
                requires_refresh = True
        roll_check = effects.get("roll_check")
        if isinstance(roll_check, dict):
            chance = float(roll_check.get("pass", 1.0))
            chance = max(0.0, min(1.0, chance))
            if random.random() > chance:
                fail_triggered = True
                fail_text = roll_check.get("fail_text")
                if fail_text:
                    messages.append(str(fail_text))
                else:
                    messages.append("The attempt draws suspicion.")
                fail_alert = roll_check.get("on_fail_alert")
                if isinstance(fail_alert, (int, float)):
                    self.alert_level = max(0, self.alert_level + int(fail_alert))
                    messages.append("Security tightens.")
                hp_on_fail = roll_check.get("hp_delta_on_fail")
                if isinstance(hp_on_fail, (int, float)):
                    hp_fail_effect += int(hp_on_fail)
            else:
                success_text = roll_check.get("success_text")
                if success_text:
                    messages.append(str(success_text))
        hp_fail_effect += int(effects.get("hp_delta_on_fail", 0)) if isinstance(
            effects.get("hp_delta_on_fail"), (int, float)
        ) else 0
        if option.clear_flag:
            if self._clear_flag(option.clear_flag):
                requires_refresh = True
        if timer_rooms_value and option.set_flag:
            self.timed_flags[option.set_flag] = timer_rooms_value
        if fail_triggered:
            alert_on_fail = effects.get("alert_on_fail") or effects.get("on_fail_alert")
            if isinstance(alert_on_fail, (int, float)):
                self.alert_level = max(0, self.alert_level + int(alert_on_fail))
            if hp_fail_effect:
                self.stats.hp = max(0, min(self.stats.max_hp, self.stats.hp + hp_fail_effect))
                stats_changed = True
                if hp_fail_effect < 0:
                    messages.append(f"You lose {-hp_fail_effect} HP.")
                elif hp_fail_effect > 0:
                    messages.append(f"You recover {hp_fail_effect} HP.")
        if stats_changed:
            self.update_stats_display()
        return ("\n".join(messages), requires_refresh)

    def _refresh_current_room_options(self) -> None:
        if not self.current_room_id:
            return
        room = self.rooms.get(self.current_room_id)
        if not room:
            return
        options = self._build_room_options(room)
        if not options:
            options.append(("Catch your breath.", lambda: None))
        self.set_options(options)

    def _prepare_room_transition(self, next_room: Optional[str], label: str = "Continue") -> None:
        self._pending_room_transition = next_room
        self.set_options([(label, self._execute_pending_transition)])

    def _execute_pending_transition(self) -> None:
        next_room = self._pending_room_transition
        self._pending_room_transition = None
        if next_room:
            self.go_to(next_room)
            return
        if not self.current_room_id:
            return
        room = self.rooms.get(self.current_room_id)
        if not room:
            return
        options = self._build_room_options(room)
        if not options:
            options.append(("Catch your breath.", lambda: None))
        self.set_options(options)

    def _roll_loot_table(self, table: List[Dict[str, Any]], rolls: int) -> List[str]:
        if not table:
            return []
        awards: List[str] = []
        attempts = max(1, int(rolls or 1))
        for _ in range(attempts):
            for entry in table:
                item = entry.get("item")
                if not item:
                    continue
                chance = float(entry.get("chance", 1.0))
                chance = max(0.0, min(1.0, chance))
                if chance < 1.0 and random.random() > chance:
                    continue
                if entry.get("unique"):
                    unique_key = entry.get("unique_key") or item
                    if unique_key in self._unique_loot_awards:
                        continue
                    self._unique_loot_awards.add(unique_key)
                awards.append(item)
                break
        return awards

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def run(self) -> None:
        self.root.mainloop()


def create_app(
    rooms: Dict[str, RoomSpec],
    battles: Dict[str, BattleSpec],
    images: Dict[str, str],
    sounds: Dict[str, str],
    defaults_module: Any,
) -> GameApp:
    root = tk.Tk()
    return GameApp(rooms, battles, images, sounds, defaults_module, root)
