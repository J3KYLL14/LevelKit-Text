"""Tkinter-powered classroom adventure engine."""

import random
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageTk

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


class RoundedPanel(tk.Frame):
    """Canvas-backed frame with rounded corners."""

    def __init__(
        self,
        master,
        *,
        corner_radius: int = 24,
        background: str = "#181818",
        outline: str = "",
        padding: int = 20,
    ) -> None:
        super().__init__(master, bg="", highlightthickness=0, bd=0)
        self._corner_radius = corner_radius
        self._panel_color = background
        self._outline = outline
        self._padding = padding
        self._inner_color = self._strip_alpha(background)

        self._canvas = tk.Canvas(self, bg="", highlightthickness=0, bd=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self.inner = tk.Frame(
            self._canvas,
            bg=self._inner_color,
            highlightthickness=0,
            bd=0,
        )
        self._window_id = self._canvas.create_window(
            (self._padding, self._padding),
            window=self.inner,
            anchor="nw",
        )

        self._canvas.bind("<Configure>", self._redraw)

    def _redraw(self, event) -> None:
        width = max(2, event.width)
        height = max(2, event.height)
        radius = min(self._corner_radius, width // 2, height // 2)
        self._canvas.delete("panel")
        points = self._rounded_points(0, 0, width, height, radius)
        try:
            self._canvas.create_polygon(
                points,
                fill=self._panel_color,
                outline=self._outline,
                smooth=True,
                tags="panel",
            )
        except tk.TclError:
            self._canvas.create_polygon(
                points,
                fill=self._inner_color,
                outline=self._outline,
                smooth=True,
                tags="panel",
            )
        inner_width = max(0, width - 2 * self._padding)
        inner_height = max(0, height - 2 * self._padding)
        self._canvas.coords(self._window_id, self._padding, self._padding)
        self._canvas.itemconfigure(self._window_id, width=inner_width, height=inner_height)

    @staticmethod
    def _strip_alpha(color: str) -> str:
        if isinstance(color, str) and color.startswith("#") and len(color) == 9:
            return color[:7]
        return color

    @staticmethod
    def _rounded_points(x1: int, y1: int, x2: int, y2: int, radius: int) -> List[int]:
        if radius <= 0:
            return [x1, y1, x2, y1, x2, y2, x1, y2]
        return [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]


class RoundedButton(tk.Canvas):
    """Canvas-based button with rounded corners and left-aligned text."""

    def __init__(
        self,
        master,
        *,
        text: str = "",
        command: Optional[Callable[[], None]] = None,
        corner_radius: int = 18,
        font: Tuple[str, int, str] = ("Segoe UI", 12, ""),
        foreground: str = "#f0f0f0",
        background: str = "#2b2b2b",
        hover_background: str = "#3a3a3a",
        active_background: str = "#4a4a4a",
        disabled_background: str = "#1e1e1e",
        disabled_foreground: Optional[str] = None,
        padding: int = 18,
        height: int = 54,
    ) -> None:
        super().__init__(master, highlightthickness=0, bd=0, bg="", height=height)
        self._corner_radius = corner_radius
        self._font = font
        self._fg_color = foreground
        self._bg_normal = background
        self._bg_hover = hover_background
        self._bg_active = active_background
        self._bg_disabled = disabled_background
        self._fg_disabled = disabled_foreground or "#7a7a7a"
        self._padding = padding
        self._height = height
        self._command = command
        self._enabled = True
        self._state = "normal"

        self._text_id = self.create_text(
            self._padding,
            self._height // 2,
            anchor="w",
            text=text,
            font=self._font,
            fill=self._fg_color,
            tags="text",
            justify="left",
            width=1,
        )

        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def set_text(self, text: str) -> None:
        self.itemconfigure(self._text_id, text=text)
        self._update_text_width()

    def set_command(self, command: Callable[[], None]) -> None:
        self._command = command

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self._state = "disabled" if not enabled else "normal"
        self._apply_state_colors()

    def apply_colors(
        self,
        *,
        foreground: Optional[str] = None,
        background: Optional[str] = None,
        hover: Optional[str] = None,
        active: Optional[str] = None,
        disabled: Optional[str] = None,
        disabled_foreground: Optional[str] = None,
    ) -> None:
        if foreground is not None:
            self._fg_color = foreground
        if background is not None:
            self._bg_normal = background
        if hover is not None:
            self._bg_hover = hover
        if active is not None:
            self._bg_active = active
        if disabled is not None:
            self._bg_disabled = disabled
        if disabled_foreground is not None:
            self._fg_disabled = disabled_foreground
        self._apply_state_colors()

    def _on_enter(self, _event) -> None:
        if not self._enabled:
            return
        self._state = "hover"
        self._apply_state_colors()

    def _on_leave(self, _event) -> None:
        if not self._enabled:
            return
        self._state = "normal"
        self._apply_state_colors()

    def _on_press(self, _event) -> None:
        if not self._enabled:
            return
        self._state = "active"
        self._apply_state_colors()

    def _on_release(self, event) -> None:
        if not self._enabled:
            return
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self._state = "hover" if inside else "normal"
        self._apply_state_colors()
        if inside and self._command:
            self._command()

    def _apply_state_colors(self) -> None:
        if self._state == "disabled":
            color = self._bg_disabled
            text_color = self._fg_disabled
        elif self._state == "active":
            color = self._bg_active
            text_color = self._fg_color
        elif self._state == "hover":
            color = self._bg_hover
            text_color = self._fg_color
        else:
            color = self._bg_normal
            text_color = self._fg_color
        self._draw_background(color)
        self.itemconfigure(self._text_id, fill=text_color)

    def _redraw(self, _event) -> None:
        self._update_text_width()
        self._apply_state_colors()

    def _update_text_width(self) -> None:
        width = max(0, self.winfo_width() - 2 * self._padding)
        self.itemconfigure(self._text_id, width=width)
        self.coords(self._text_id, self._padding, self.winfo_height() / 2)

    def _draw_background(self, fill_color: str) -> None:
        width = max(2, self.winfo_width())
        height = max(2, self.winfo_height())
        radius = min(self._corner_radius, width // 2, height // 2)
        self.delete("background")
        points = RoundedPanel._rounded_points(0, 0, width, height, radius)
        self.create_polygon(points, fill=fill_color, outline="", smooth=True, tags="background")
        self.tag_lower("background")
        self.tag_raise(self._text_id)


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

        self.theme: Dict[str, object] = getattr(self.defaults, "UI_THEME", {})
        self._content_width_ratio = self._ratio(self._theme("layout", "content_width", default=0.68), 0.68)
        self._header_width_ratio = self._ratio(self._theme("layout", "header_width", default=0.8), 0.8)
        self._header_top_margin_ratio = self._ratio(
            self._theme("layout", "header_top_margin", default=0.04), 0.04
        )
        self._options_bottom_margin_ratio = self._ratio(
            self._theme("layout", "options_bottom_margin", default=0.05), 0.05
        )
        self._option_spacing_ratio = self._ratio(
            self._theme("layout", "option_spacing", default=0.02), 0.02
        )
        self._dialogue_options_gap_ratio = self._ratio(
            self._theme("layout", "dialogue_options_gap", default=0.02), 0.02
        )

        self.root = tk.Tk()
        self.root.title("Text Adventure")
        self.root.geometry(f"{self.defaults.WINDOW_WIDTH}x{self.defaults.WINDOW_HEIGHT}")
        window_bg = self._solid_color(self._theme("window", "background", default="#101010"), "#101010")
        self._window_bg = window_bg
        self.root.configure(bg=window_bg)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        fallback_text = self._theme("window", "fallback_text", default="#ffffff") or "#ffffff"
        self._fallback_text_color = fallback_text
        self._fallback_font = ("Segoe UI", 24, "bold")
        self._background_original: Optional[Image.Image] = None
        self._background_photo: Optional[ImageTk.PhotoImage] = None
        self._last_size: Tuple[int, int] = (0, 0)

        self.background_label = tk.Label(self.root, bg=window_bg, fg=fallback_text, anchor="center")
        self.background_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.overlay = tk.Frame(self.root, bg="", highlightthickness=0, bd=0)
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        header_bg = self._theme("header", "panel_background", default="#202020cc")
        header_inner_bg = self._solid_color(header_bg, "#202020")
        header_outline = self._theme("header", "panel_outline", default="")
        header_padding = self._int(self._theme("header", "padding", default=24), 24)
        header_corner = self._int(self._theme("header", "corner_radius", default=26), 26)

        self.header_panel = RoundedPanel(
            self.overlay,
            corner_radius=header_corner,
            background=header_bg,
            outline=header_outline or "",
            padding=header_padding,
        )
        self.header_panel.inner.configure(bg=header_inner_bg)
        self.header_panel.place(relx=0.5, rely=0.0, anchor="n", relwidth=self._header_width_ratio)

        self.title_var = tk.StringVar(value="")
        title_font = self._theme("header", "title_font", default=("Segoe UI", 20, "bold"))
        title_color = self._theme("header", "title_foreground", default="#f0f0f0") or "#f0f0f0"
        self.title_label = tk.Label(
            self.header_panel.inner,
            textvariable=self.title_var,
            anchor="w",
            bg=header_inner_bg,
            fg=title_color,
            font=title_font,
        )
        self.title_label.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 16))

        self.stats_var = tk.StringVar()
        stats_font = self._theme("header", "stats_font", default=("Segoe UI", 14, ""))
        stats_color = self._theme("header", "stats_foreground", default="#dedede") or "#dedede"
        self.stats_label = tk.Label(
            self.header_panel.inner,
            textvariable=self.stats_var,
            anchor="e",
            bg=header_inner_bg,
            fg=stats_color,
            font=stats_font,
        )
        self.stats_label.pack(side=tk.RIGHT)

        self.dialogue_var = tk.StringVar(value="")

        self.content_stack = tk.Frame(self.overlay, bg="", highlightthickness=0, bd=0)
        self.content_stack.place(relx=0.5, rely=1.0, anchor="s", relwidth=self._content_width_ratio)

        dialogue_bg = self._theme("dialogue", "panel_background", default="#1c1c1ccc")
        dialogue_inner_bg = self._solid_color(dialogue_bg, "#1c1c1c")
        dialogue_outline = self._theme("dialogue", "panel_outline", default="")
        dialogue_padding = self._int(self._theme("dialogue", "padding", default=28), 28)
        dialogue_corner = self._int(self._theme("dialogue", "corner_radius", default=28), 28)

        self.dialogue_panel = RoundedPanel(
            self.content_stack,
            corner_radius=dialogue_corner,
            background=dialogue_bg,
            outline=dialogue_outline or "",
            padding=dialogue_padding,
        )
        self.dialogue_panel.inner.configure(bg=dialogue_inner_bg)
        self.dialogue_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        dialogue_font = self._theme("dialogue", "font", default=("Segoe UI", 14, ""))
        dialogue_color = self._theme("dialogue", "foreground", default="#f8f8f2") or "#f8f8f2"
        self.dialogue_label = tk.Label(
            self.dialogue_panel.inner,
            textvariable=self.dialogue_var,
            justify="center",
            anchor="center",
            wraplength=1,
            bg=dialogue_inner_bg,
            fg=dialogue_color,
            font=dialogue_font,
        )
        self.dialogue_label.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.dialogue_panel.inner.bind(
            "<Configure>", lambda event: self._update_dialogue_wrap(event.width)
        )

        options_bg = self._theme("options", "panel_background", default="#1c1c1ccc")
        options_inner_bg = self._solid_color(options_bg, "#1c1c1c")
        options_outline = self._theme("options", "panel_outline", default="")
        options_padding = self._int(self._theme("options", "padding", default=18), 18)
        options_corner = self._int(self._theme("options", "corner_radius", default=24), 24)

        self.options_panel = RoundedPanel(
            self.content_stack,
            corner_radius=options_corner,
            background=options_bg,
            outline=options_outline or "",
            padding=options_padding,
        )
        self.options_panel.inner.configure(bg=options_inner_bg)
        self.options_panel.pack(side=tk.TOP, fill=tk.X)

        self.options_container = tk.Frame(
            self.options_panel.inner,
            bg=options_inner_bg,
            highlightthickness=0,
            bd=0,
        )
        self.options_container.pack(side=tk.TOP, fill=tk.X)

        button_font = self._theme("options", "button_font", default=("Segoe UI", 12, ""))
        button_corner = self._int(self._theme("options", "button_corner_radius", default=18), 18)
        button_height = self._int(self._theme("options", "button_height", default=56), 56)
        button_padding = self._int(self._theme("options", "button_padding", default=22), 22)
        button_horizontal_padding = self._int(
            self._theme("options", "button_horizontal_padding", default=20), 20
        )
        button_fg = self._theme("options", "button_foreground", default="#f5f5f5") or "#f5f5f5"
        button_bg = self._theme("options", "button_background", default="#252525") or "#252525"
        button_hover_bg = self._theme("options", "button_hover_background", default="#343434") or "#343434"
        button_active_bg = self._theme("options", "button_active_background", default="#454545") or "#454545"
        button_disabled_bg = self._theme("options", "button_disabled_background", default="#151515") or "#151515"
        button_disabled_fg = self._theme("options", "button_disabled_foreground", default="#7a7a7a") or "#7a7a7a"

        self.option_buttons: List[RoundedButton] = []

        for index in range(9):
            btn = RoundedButton(
                self.options_container,
                text="",
                command=lambda idx=index: self._on_option(idx),
                corner_radius=button_corner,
                font=button_font,
                foreground=button_fg,
                background=button_bg,
                hover_background=button_hover_bg,
                active_background=button_active_bg,
                disabled_background=button_disabled_bg,
                disabled_foreground=button_disabled_fg,
                padding=button_padding,
                height=button_height,
            )
            btn.pack(side=tk.TOP, fill=tk.X, padx=button_horizontal_padding, pady=0)
            btn.set_text("")
            btn.set_enabled(False)
            self.option_buttons.append(btn)

        self.root.bind("<Configure>", self._on_root_configure)
        self.root.update_idletasks()
        self._on_root_configure(None)

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

    def _theme(self, *keys, default=None):
        value: object = self.theme
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value

    @staticmethod
    def _ratio(value, fallback: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return fallback
        return max(0.0, min(1.0, numeric))

    @staticmethod
    def _int(value, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _solid_color(color, fallback: str) -> str:
        if isinstance(color, str) and color.startswith("#") and len(color) == 9:
            return color[:7]
        return color if isinstance(color, str) else fallback

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

    def _update_dialogue_wrap(self, width: int) -> None:
        wraplength = max(0, width - 40)
        self.dialogue_label.configure(wraplength=wraplength)

    def set_dialogue(self, text: str) -> None:
        self.dialogue_var.set(text)

    def set_options(self, options: List[Tuple[str, Callable[[], None]]]) -> None:
        self.option_handlers = [handler for _, handler in options]
        for index, button in enumerate(self.option_buttons):
            if index < len(options):
                label, _ = options[index]
                self._style_option_button(
                    button,
                    enabled=True,
                    text=f"{index + 1}. {label}",
                )
            else:
                self._style_option_button(button, enabled=False, text="")

    def _style_option_button(
        self,
        button: RoundedButton,
        *,
        enabled: bool,
        text: Optional[str] = None,
    ) -> None:
        if text is not None:
            button.set_text(text)
        elif not enabled:
            button.set_text("")
        button.set_enabled(enabled)

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
        self._background_original = None
        self._background_photo = None
        message_kwargs = {
            "image": "",
            "fg": self._fallback_text_color,
            "bg": self._window_bg,
            "font": self._fallback_font,
        }
        if not key:
            self.background_label.configure(text="No background image", **message_kwargs)
            self.background_label.image = None
            return
        filename = self.images.get(key)
        if not filename:
            self.background_label.configure(text="Missing background", **message_kwargs)
            self.background_label.image = None
            return
        path = IMAGES_DIR / filename
        if not path.exists():
            self.background_label.configure(text="Background file not found", **message_kwargs)
            self.background_label.image = None
            return
        try:
            with Image.open(path) as source:
                self._background_original = source.convert("RGBA")
        except Exception:
            self.background_label.configure(text="Failed to load image", **message_kwargs)
            self.background_label.image = None
            self._background_original = None
            return
        self.background_label.configure(text="")
        self._rescale_background()

    def _set_music(self, key: Optional[str]) -> None:
        if key == self.current_music_key:
            return
        self.current_music_key = key
        audio.play_music(key, self.sounds, SOUNDS_DIR)

    def _rescale_background(self, width: Optional[int] = None, height: Optional[int] = None) -> None:
        if self._background_original is None:
            return
        width = width if width is not None else max(0, self.root.winfo_width())
        height = height if height is not None else max(0, self.root.winfo_height())
        if width <= 0 or height <= 0:
            return
        resized = self._background_original.resize((width, height), Image.LANCZOS)
        self._background_photo = ImageTk.PhotoImage(resized)
        self.background_label.configure(image=self._background_photo, text="")
        self.background_label.image = self._background_photo

    def _on_root_configure(self, _event) -> None:
        width = max(0, self.root.winfo_width())
        height = max(0, self.root.winfo_height())
        if (width, height) == self._last_size:
            return
        self._last_size = (width, height)
        self._update_layout(width, height)
        self._rescale_background(width, height)

    def _update_layout(self, width: int, height: int) -> None:
        header_margin = int(height * self._header_top_margin_ratio)
        self.header_panel.place_configure(
            relx=0.5,
            rely=0.0,
            anchor="n",
            relwidth=self._header_width_ratio,
            y=header_margin,
        )

        bottom_margin = int(height * self._options_bottom_margin_ratio)
        self.content_stack.place_configure(
            relx=0.5,
            rely=1.0,
            anchor="s",
            relwidth=self._content_width_ratio,
            y=-bottom_margin,
        )

        gap_pixels = int(height * self._dialogue_options_gap_ratio)
        self.dialogue_panel.pack_configure(pady=(0, gap_pixels))

        button_spacing = max(0, int(height * self._option_spacing_ratio))
        button_pad = max(0, button_spacing // 2)
        for button in self.option_buttons:
            button.pack_configure(pady=button_pad)

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
