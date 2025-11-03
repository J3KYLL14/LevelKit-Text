"""PySide6-powered classroom adventure engine."""

from __future__ import annotations

from collections import Counter
import random
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from PySide6 import QtCore, QtGui, QtWidgets

from . import audio
from .models import BattleAction, BattleSpec, OptionSpec, RoomSpec, Stats

# Fallback definitions for engine-created items. Leave empty in the template.
DEFAULT_ITEM_DEFINITIONS: Dict[str, Dict[str, object]] = {}

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = PACKAGE_ROOT / "assets" / "images"
SOUNDS_DIR = PACKAGE_ROOT / "assets" / "sounds"


def _parse_hex_color(color: str, fallback: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    if isinstance(color, str) and color.startswith("#"):
        if len(color) == 9:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            a = int(color[7:9], 16)
            return (r, g, b, a)
        if len(color) == 7:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            return (r, g, b, 255)
    return fallback


def _rgba_stylesheet(color: str, default: str) -> str:
    r, g, b, a = _parse_hex_color(color, _parse_hex_color(default, (0, 0, 0, 255)))
    return f"rgba({r}, {g}, {b}, {a})"


def _ensure_application() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class BackgroundWidget(QtWidgets.QWidget):
    """Widget that paints a scaled background pixmap."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._pixmap: Optional[QtGui.QPixmap] = None

    def set_background(self, pixmap: Optional[QtGui.QPixmap]) -> None:
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802 (Qt naming)
        super().paintEvent(event)
        if not self._pixmap or self._pixmap.isNull():
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        target_size = self.size()
        scaled = self._pixmap.scaled(
            target_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        x = (target_size.width() - scaled.width()) // 2
        y = (target_size.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)


class TranslucentFrame(QtWidgets.QFrame):
    """Rounded frame with translucent background."""

    def __init__(
        self,
        color: str,
        radius: int,
        padding: int,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._radius = radius
        self._padding = padding
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.set_border_color(color)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(0)

    def set_border_color(self, color: str) -> None:
        self.setStyleSheet(
            f"border-radius: {self._radius}px; background-color: {_rgba_stylesheet(color, '#202020cc')};"
        )


class OptionButton(QtWidgets.QPushButton):
    """Push button with rounded translucent styling."""

    def __init__(self, index: int, trigger: Callable[[int], None], parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._index = index
        self._trigger = trigger
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(48)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.clicked.connect(self._handle_click)

    def apply_theme(
        self,
        foreground: str,
        background: str,
        hover: str,
        active: str,
        disabled: str,
        disabled_fg: str,
        radius: int,
    ) -> None:
        stylesheet = f"""
            QPushButton {{
                border: none;
                border-radius: {radius}px;
                padding: 12px 18px;
                color: {_rgba_stylesheet(foreground, '#ffffff')};
                background-color: {_rgba_stylesheet(background, '#252525')};
            }}
            QPushButton:hover {{
                background-color: {_rgba_stylesheet(hover, background)};
            }}
            QPushButton:pressed {{
                background-color: {_rgba_stylesheet(active, hover)};
            }}
            QPushButton:disabled {{
                background-color: {_rgba_stylesheet(disabled, background)};
                color: {_rgba_stylesheet(disabled_fg, '#7a7a7a')};
            }}
        """
        self.setStyleSheet(stylesheet)

    def _handle_click(self) -> None:
        if self._trigger:
            self._trigger(self._index)


class GameApp(QtWidgets.QMainWindow):
    """Top-level PySide6 application managing rooms, battles, and UI."""

    def __init__(
        self,
        rooms: Dict[str, RoomSpec],
        battles: Dict[str, BattleSpec],
        images: Dict[str, str],
        sounds: Dict[str, str],
        defaults_module,
        app: QtWidgets.QApplication,
    ) -> None:
        super().__init__()
        self.qt_app = app

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

        self._fade_effect: Optional[QtWidgets.QGraphicsOpacityEffect] = None
        self._fade_out_animation: Optional[QtCore.QPropertyAnimation] = None
        self._fade_in_animation: Optional[QtCore.QPropertyAnimation] = None
        self._transition_running = False
        self._transition_duration_ms = max(
            0, self._int(self._theme("animations", "fade_duration_ms", default=180), 180)
        )

        self._background_pixmap: Optional[QtGui.QPixmap] = None

        self._build_ui()
        start_room = self.defaults.START_ROOM_ID
        self.go_to(start_room, initial=True)
        self.show()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setWindowTitle(getattr(self.defaults, "GAME_TITLE", "LevelKit-Text"))
        self.resize(self.defaults.WINDOW_WIDTH, self.defaults.WINDOW_HEIGHT)

        window_color = self._solid_color(self._theme("window", "background", default="#101010"), "#101010")
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(window_color))
        self.setPalette(palette)

        self._background = BackgroundWidget()
        central = QtWidgets.QWidget()
        central_layout = QtWidgets.QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        header_color = self._theme("header", "panel_background", default="#202020cc")
        header_padding = self._int(self._theme("header", "padding", default=16), 16) + 8
        header_radius = self._int(self._theme("header", "corner_radius", default=18), 18)
        header_frame = TranslucentFrame(header_color, header_radius, header_padding)
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)
        header_frame.layout().addLayout(header_layout)

        title_box = QtWidgets.QVBoxLayout()
        game_title = getattr(self.defaults, "GAME_TITLE", "LevelKit-Text")
        self.title_label = QtWidgets.QLabel(game_title)
        title_font = self._theme("header", "title_font", default=("Segoe UI", 20, "bold"))
        self.title_label.setFont(self._qt_font(title_font))
        self.title_label.setStyleSheet(
            f"color: {_rgba_stylesheet(self._theme('header', 'title_foreground', default='#f0f0f0'), '#f0f0f0')};"
            "background-color: transparent;"
        )
        title_box.addWidget(self.title_label)

        byline = getattr(self.defaults, "GAME_BYLINE", "")
        self.byline_label = QtWidgets.QLabel(byline)
        byline_font = self._theme("header", "byline_font", default=("Segoe UI", 12, ""))
        self.byline_label.setFont(self._qt_font(byline_font))
        self.byline_label.setStyleSheet(
            f"color: {_rgba_stylesheet(self._theme('header', 'byline_foreground', default='#cccccc'), '#cccccc')};"
            "background-color: transparent;"
        )
        if byline:
            title_box.addWidget(self.byline_label)
        else:
            self.byline_label.hide()
        title_box.addStretch(1)

        header_layout.addLayout(title_box, stretch=3)

        stats_color = self._theme("header", "stats_foreground", default="#dedede")
        stats_font_setting = self._theme("header", "stats_font", default=("Segoe UI", 14, ""))
        if isinstance(stats_font_setting, (tuple, list)) and len(stats_font_setting) >= 2:
            stats_family = stats_font_setting[0]
            stats_size = self._int(stats_font_setting[1], 14) + 4
            stats_weight = stats_font_setting[2] if len(stats_font_setting) > 2 else ""
            stats_font = (stats_family, stats_size, stats_weight)
        else:
            stats_font = ("Segoe UI", 18, "")
        stats_grid = QtWidgets.QGridLayout()
        stats_grid.setContentsMargins(0, 0, 0, 0)
        stats_grid.setHorizontalSpacing(24)
        stats_grid.setVerticalSpacing(4)
        header_layout.addLayout(stats_grid, stretch=2)

        stat_order = [
            ("HP", "hp"),
            ("ATK", "attack"),
            ("LVL", "level"),
            ("MP", "mana"),
            ("DEF", "defence"),
            ("XP", "xp"),
        ]
        self._stat_labels: Dict[str, QtWidgets.QLabel] = {}
        for index, (label_text, key) in enumerate(stat_order):
            row = index // 3
            col = index % 3
            label = QtWidgets.QLabel()
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            label.setFont(self._qt_font(stats_font))
            label.setStyleSheet(f"color: {_rgba_stylesheet(stats_color, '#dedede')}; background-color: transparent;")
            stats_grid.addWidget(label, row, col)
            self._stat_labels[key] = label

        header_row = QtWidgets.QHBoxLayout()
        header_row.setContentsMargins(20, 20, 20, 0)
        header_frame.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        header_row.addWidget(header_frame)
        central_layout.addLayout(header_row)

        content_area = QtWidgets.QWidget()
        bottom_row = QtWidgets.QHBoxLayout(content_area)
        bottom_row.setContentsMargins(20, 10, 20, 40)
        bottom_row.setSpacing(20)

        stack_container = QtWidgets.QWidget()
        stack_container.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
        stack_layout = QtWidgets.QVBoxLayout(stack_container)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.setSpacing(24)
        stack_container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding
        )

        # Dialogue panel
        dialogue_color = self._theme("dialogue", "panel_background", default="#1c1c1ccc")
        dialogue_padding = self._int(self._theme("dialogue", "padding", default=28), 28)
        dialogue_radius = self._int(self._theme("dialogue", "corner_radius", default=28), 28)
        dialogue_frame = TranslucentFrame(dialogue_color, dialogue_radius, dialogue_padding)
        dialogue_layout = QtWidgets.QVBoxLayout()
        dialogue_layout.setContentsMargins(0, 0, 0, 0)
        dialogue_frame.layout().addLayout(dialogue_layout)

        dialogue_font = self._theme("dialogue", "font", default=("Segoe UI", 14, ""))
        dialogue_fg = self._theme("dialogue", "foreground", default="#f8f8f2")
        self.dialogue_label = QtWidgets.QLabel("")
        self.dialogue_label.setWordWrap(True)
        self.dialogue_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop)
        self.dialogue_label.setFont(self._qt_font(dialogue_font))
        self.dialogue_label.setStyleSheet(
            f"color: {_rgba_stylesheet(dialogue_fg, '#f8f8f2')}; background-color: transparent;"
        )
        dialogue_layout.addWidget(self.dialogue_label)

        stack_layout.addStretch(6)
        stack_layout.addWidget(dialogue_frame, stretch=0)

        # Option buttons panel
        options_color = self._theme("options", "panel_background", default="#1c1c1ccc")
        options_padding = self._int(self._theme("options", "padding", default=18), 18)
        options_radius = self._int(self._theme("options", "corner_radius", default=24), 24)
        options_frame = TranslucentFrame(options_color, options_radius, options_padding)
        options_layout = QtWidgets.QGridLayout()
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(12)
        options_frame.layout().addLayout(options_layout)

        button_fg = self._theme("options", "button_foreground", default="#f5f5f5")
        button_bg = self._theme("options", "button_background", default="#252525")
        button_hover = self._theme("options", "button_hover_background", default="#343434")
        button_active = self._theme("options", "button_active_background", default="#454545")
        button_disabled = self._theme("options", "button_disabled_background", default="#151515")
        button_disabled_fg = self._theme("options", "button_disabled_foreground", default="#7a7a7a")
        button_radius = self._int(self._theme("options", "button_corner_radius", default=18), 18)

        self.option_buttons: List[OptionButton] = []
        for index in range(4):
            button = OptionButton(index, self._on_option)
            button.apply_theme(
                foreground=button_fg,
                background=button_bg,
                hover=button_hover,
                active=button_active,
                disabled=button_disabled,
                disabled_fg=button_disabled_fg,
                radius=button_radius,
            )
            row = index // 2
            col = index % 2
            options_layout.addWidget(button, row, col)
            button.hide()
            self.option_buttons.append(button)

        stack_layout.addWidget(options_frame, stretch=0)

        # Inventory panel
        inventory_color = self._theme("inventory", "panel_background", default="#1c1c1ccc")
        inventory_padding = self._int(self._theme("inventory", "padding", default=18), 18)
        inventory_radius = self._int(self._theme("inventory", "corner_radius", default=18), 18)
        inventory_frame = TranslucentFrame(inventory_color, inventory_radius, inventory_padding)
        inventory_frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
        inventory_frame.setMaximumWidth(int(self.width() * 0.12))
        self._inventory_frame = inventory_frame
        inventory_layout = QtWidgets.QVBoxLayout()
        inventory_layout.setContentsMargins(0, 0, 0, 0)
        inventory_layout.setSpacing(8)
        inventory_frame.layout().addLayout(inventory_layout)

        inventory_title_font = self._theme("inventory", "title_font", default=("Segoe UI", 16, "bold"))
        inventory_title_fg = self._theme("inventory", "title_foreground", default="#f0f0f0")
        self.inventory_title = QtWidgets.QLabel("Inventory")
        self.inventory_title.setFont(self._qt_font(inventory_title_font))
        self.inventory_title.setStyleSheet(
            f"color: {_rgba_stylesheet(inventory_title_fg, '#f0f0f0')}; background-color: transparent;"
        )
        inventory_layout.addWidget(self.inventory_title)

        list_font = self._theme("inventory", "list_font", default=("Segoe UI", 12, ""))
        list_fg = self._theme("inventory", "list_foreground", default="#f5f5f5")
        list_stylesheet = f"""
            QListWidget {{
                background: transparent;
                color: {_rgba_stylesheet(list_fg, '#f5f5f5')};
                border: none;
            }}
            QListWidget::item:selected {{
                background-color: {_rgba_stylesheet(button_hover, '#343434')};
            }}
        """

        self.inventory_equipped_label = QtWidgets.QLabel("Equipped")
        equipped_font = self._theme("inventory", "section_font", default=("Segoe UI", 12, "bold"))
        self.inventory_equipped_label.setFont(self._qt_font(equipped_font))
        self.inventory_equipped_label.setStyleSheet(
            f"color: {_rgba_stylesheet(inventory_title_fg, '#f0f0f0')}; background-color: transparent;"
        )
        self.inventory_equipped_label.hide()
        inventory_layout.addWidget(self.inventory_equipped_label)

        self.inventory_equipped_container = QtWidgets.QWidget()
        equipped_layout = QtWidgets.QVBoxLayout(self.inventory_equipped_container)
        equipped_layout.setContentsMargins(0, 0, 0, 0)
        equipped_layout.setSpacing(0)
        inventory_layout.addWidget(self.inventory_equipped_container, stretch=0)
        self.inventory_equipped_container.hide()

        self.inventory_equipped_sections: Dict[str, Dict[str, Any]] = {}
        for slot in ("melee", "ranged", "magic"):
            section_widget = QtWidgets.QWidget()
            section_layout = QtWidgets.QVBoxLayout(section_widget)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(0)

            slot_label = QtWidgets.QLabel(slot.capitalize())
            slot_label.setFont(self._qt_font(equipped_font))
            slot_label.setStyleSheet(
                f"color: {_rgba_stylesheet(inventory_title_fg, '#f0f0f0')}; background-color: transparent;"
            )
            section_layout.addWidget(slot_label)

            list_widget = QtWidgets.QListWidget()
            list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
            list_widget.setStyleSheet(list_stylesheet)
            list_widget.setFont(self._qt_font(list_font))
            list_widget.setFixedHeight(56)
            list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            section_layout.addWidget(list_widget)

            equipped_layout.addWidget(section_widget)
            section_widget.hide()

            self._bind_inventory_list(list_widget)
            self.inventory_equipped_sections[slot] = {
                "widget": section_widget,
                "list": list_widget,
            }

        self.inventory_backpack_label = QtWidgets.QLabel("Backpack")
        self.inventory_backpack_label.setFont(self._qt_font(equipped_font))
        self.inventory_backpack_label.setStyleSheet(
            f"color: {_rgba_stylesheet(inventory_title_fg, '#f0f0f0')}; background-color: transparent;"
        )
        inventory_layout.addWidget(self.inventory_backpack_label)

        self.inventory_backpack_list = QtWidgets.QListWidget()
        self.inventory_backpack_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.inventory_backpack_list.setStyleSheet(list_stylesheet)
        self.inventory_backpack_list.setFont(self._qt_font(list_font))
        inventory_layout.addWidget(self.inventory_backpack_list, stretch=1)

        self._bind_inventory_list(self.inventory_backpack_list)

        detail_font = self._theme("inventory", "detail_font", default=("Segoe UI", 11, ""))
        detail_fg = self._theme("inventory", "detail_foreground", default="#dcdcdc")
        self.inventory_detail_label = QtWidgets.QLabel("")
        self.inventory_detail_label.setWordWrap(True)
        self.inventory_detail_label.setFont(self._qt_font(detail_font))
        self.inventory_detail_label.setStyleSheet(
            f"color: {_rgba_stylesheet(detail_fg, '#dcdcdc')}; background-color: transparent;"
        )
        inventory_layout.addWidget(self.inventory_detail_label)

        hint_font = self._theme("inventory", "hint_font", default=("Segoe UI", 10, ""))
        hint_fg = self._theme("inventory", "hint_foreground", default="#bbbbbb")
        self.inventory_hint_label = QtWidgets.QLabel("Double-click or press Enter to use/equip")
        self.inventory_hint_label.setFont(self._qt_font(hint_font))
        self.inventory_hint_label.setStyleSheet(
            f"color: {_rgba_stylesheet(hint_fg, '#bbbbbb')}; background-color: transparent;"
        )
        inventory_layout.addWidget(self.inventory_hint_label)

        bottom_row.addWidget(stack_container, stretch=7)
        bottom_row.addSpacing(20)
        bottom_row.addWidget(inventory_frame, stretch=3)

        central_layout.addWidget(content_area, stretch=1)

        self._init_transition_effect(content_area)

        # Wrap central widget with background painter
        overlay = QtWidgets.QStackedLayout(self._background)
        overlay.setContentsMargins(0, 0, 0, 0)
        overlay.addWidget(central)
        self.setCentralWidget(self._background)

    def _init_transition_effect(self, widget: QtWidgets.QWidget) -> None:
        """Prepare opacity animations for the main content container."""
        if self._transition_duration_ms <= 0:
            self._fade_effect = None
            self._fade_out_animation = None
            self._fade_in_animation = None
            return

        effect = QtWidgets.QGraphicsOpacityEffect(widget)
        effect.setOpacity(1.0)
        widget.setGraphicsEffect(effect)
        self._fade_effect = effect

        fade_out = QtCore.QPropertyAnimation(effect, b"opacity")
        fade_out.setDuration(self._transition_duration_ms)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QtCore.QEasingCurve.Type.InOutQuad)
        self._fade_out_animation = fade_out

        fade_in = QtCore.QPropertyAnimation(effect, b"opacity")
        fade_in.setDuration(self._transition_duration_ms)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QtCore.QEasingCurve.Type.InOutQuad)
        self._fade_in_animation = fade_in

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _qt_font(spec: Tuple[str, int, str]) -> QtGui.QFont:
        family, size, weight = spec
        font = QtGui.QFont(family, size)
        if "bold" in weight.lower():
            font.setBold(True)
        if "italic" in weight.lower():
            font.setItalic(True)
        return font

    # ------------------------------------------------------------------
    # Theme helpers
    # ------------------------------------------------------------------
    def _theme(self, *keys, default=None):
        value: Any = self.theme
        for key in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(key, default)
        return value

    @staticmethod
    def _ratio(value, fallback: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = fallback
        return max(0.0, min(1.0, numeric))

    @staticmethod
    def _int(value, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _solid_color(color: str, fallback: str) -> str:
        if isinstance(color, str) and color.startswith("#") and len(color) == 9:
            return color[:7]
        return color if isinstance(color, str) else fallback

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------
    @staticmethod
    def _build_stats(starting: Dict[str, int]) -> Stats:
        return Stats(**starting)

    def run(self) -> None:
        self.qt_app.exec()

    # ------------------------------------------------------------------
    # Background handling
    # ------------------------------------------------------------------
    def _set_background(self, key: Optional[str]) -> None:
        self._background_pixmap = None

        if not key:
            self._background.set_background(None)
            return
        filename = self.images.get(key)
        if not filename:
            self._background.set_background(None)
            return
        path = IMAGES_DIR / filename
        if not path.exists():
            self._background.set_background(None)
            return
        pixmap = QtGui.QPixmap(str(path))
        if pixmap.isNull():
            self._background.set_background(None)
            return
        self._background_pixmap = pixmap
        self._background.set_background(pixmap)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        if self._background_pixmap:
            self._background.set_background(self._background_pixmap)
        if hasattr(self, "_inventory_frame") and self._inventory_frame:
            max_width = max(180, int(self.width() * 0.14))
            self._inventory_frame.setMaximumWidth(max_width)

    # ------------------------------------------------------------------
    # Dialogue and options
    # ------------------------------------------------------------------
    def set_dialogue(self, text: str) -> None:
        self.dialogue_label.setText(text)

    def _append_dialogue(self, text: str) -> None:
        current = self.dialogue_label.text()
        combined = f"{current}\n{text}" if current else text
        self.dialogue_label.setText(combined)

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
                button.setText(f"{idx + 1}. {label}")
                button.show()
                button.setEnabled(enabled)
            else:
                button.hide()
        # Ensure handler list length matches displayed buttons
        if len(self.option_handlers) < len(limited):
            self.option_handlers.extend([lambda: None] * (len(limited) - len(self.option_handlers)))

    def _execute_with_transition(self, handler: Callable[[], None]) -> None:
        """Run an action after fading the content out, then fade back in."""
        if not self._fade_effect or not self._fade_out_animation or not self._fade_in_animation:
            handler()
            return
        if self._transition_running:
            return
        self._transition_running = True

        fade_out = self._fade_out_animation
        fade_in = self._fade_in_animation
        effect = self._fade_effect

        fade_out.stop()
        fade_in.stop()

        start_value = effect.opacity()
        fade_out.setStartValue(start_value)
        fade_out.setEndValue(0.0)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)

        def on_fade_out_finished() -> None:
            fade_out.finished.disconnect(on_fade_out_finished)
            try:
                handler()
            except Exception:
                effect.setOpacity(1.0)
                if fade_in.state() == QtCore.QAbstractAnimation.State.Running:
                    fade_in.stop()
                try:
                    fade_in.finished.disconnect(on_fade_in_finished)
                except (RuntimeError, TypeError):
                    pass
                self._transition_running = False
                raise
            fade_in.start()

        def on_fade_in_finished() -> None:
            fade_in.finished.disconnect(on_fade_in_finished)
            effect.setOpacity(1.0)
            self._transition_running = False

        fade_out.finished.connect(on_fade_out_finished)
        fade_in.finished.connect(on_fade_in_finished)
        fade_out.start()

    def _on_option(self, index: int) -> None:
        if self._transition_running:
            return
        if index >= len(self.option_handlers):
            return
        handler = self.option_handlers[index]
        self._execute_with_transition(handler)

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
            label.setText(values.get(key, ""))

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
    def _bind_inventory_list(self, list_widget: QtWidgets.QListWidget) -> None:
        list_widget.itemActivated.connect(
            lambda itm, lst=list_widget: self._inventory_activate(itm, lst)
        )
        list_widget.currentRowChanged.connect(
            lambda row, lst=list_widget: self._on_inventory_selection_changed(lst, row)
        )

    def _refresh_inventory_panel(self) -> None:
        equipped_lists = [section["list"] for section in self.inventory_equipped_sections.values()]
        for lst in equipped_lists + [self.inventory_backpack_list]:
            lst.blockSignals(True)
            lst.clear()

        has_equipped = False
        first_equipped_list: Optional[QtWidgets.QListWidget] = None
        for slot, section in self.inventory_equipped_sections.items():
            section_widget = section["widget"]
            list_widget: QtWidgets.QListWidget = section["list"]
            item_id = self.equipment.get(slot)
            if item_id:
                name = self._item_name(item_id)
                list_item = QtWidgets.QListWidgetItem(name)
                list_item.setData(QtCore.Qt.ItemDataRole.UserRole, item_id)
                list_widget.addItem(list_item)
                section_widget.show()
                if not has_equipped:
                    first_equipped_list = list_widget
                has_equipped = True
            else:
                section_widget.hide()

        self.inventory_equipped_label.setVisible(has_equipped)
        self.inventory_equipped_container.setVisible(has_equipped)

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
                list_item = QtWidgets.QListWidgetItem(f"{name}{suffix}")
                list_item.setData(QtCore.Qt.ItemDataRole.UserRole, item_id)
                self.inventory_backpack_list.addItem(list_item)
        else:
            placeholder = QtWidgets.QListWidgetItem("Empty")
            placeholder.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
            self.inventory_backpack_list.addItem(placeholder)

        for lst in equipped_lists + [self.inventory_backpack_list]:
            lst.blockSignals(False)

        if has_equipped and first_equipped_list and first_equipped_list.count() > 0:
            first_equipped_list.setCurrentRow(0)
        else:
            first_selectable = next(
                (
                    idx
                    for idx in range(self.inventory_backpack_list.count())
                    if self.inventory_backpack_list.item(idx).flags()
                    & QtCore.Qt.ItemFlag.ItemIsEnabled
                ),
                -1,
            )
            if first_selectable >= 0:
                self.inventory_backpack_list.setCurrentRow(first_selectable)
            else:
                self.inventory_detail_label.setText("")

    def _on_inventory_selection_changed(
        self, list_widget: QtWidgets.QListWidget, row: int
    ) -> None:
        if row < 0:
            self.inventory_detail_label.setText("")
            return
        item = list_widget.item(row)
        if not item:
            self.inventory_detail_label.setText("")
            return
        item_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not item_id:
            self.inventory_detail_label.setText("")
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
        self.inventory_detail_label.setText(detail_text)

    def _inventory_activate(
        self,
        item: QtWidgets.QListWidgetItem,
        _source: Optional[QtWidgets.QListWidget] = None,
    ) -> None:
        item_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not item_id:
            return
        if self._use_item(item_id):
            if self.inventory.get(item_id, 0) <= 0:
                self.inventory.pop(item_id, None)
            self._refresh_inventory_panel()

    def open_inventory(self, _event: Optional[object] = None) -> None:
        if not self.inventory:
            QtWidgets.QMessageBox.information(self, "Inventory", "Your inventory is empty.")
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Inventory")
        dialog_layout = QtWidgets.QVBoxLayout(dialog)
        list_widget = QtWidgets.QListWidget()
        for item_id, count in self.inventory.items():
            name = self._item_name(item_id)
            suffix = f" x{count}" if count > 1 else ""
            slot = self._equipped_slot(item_id)
            equipped_tag = f" [Equipped: {slot.capitalize()}]" if slot else ""
            list_item = QtWidgets.QListWidgetItem(f"{name}{suffix}{equipped_tag}")
            list_item.setData(QtCore.Qt.ItemDataRole.UserRole, item_id)
            list_widget.addItem(list_item)
        list_widget.itemActivated.connect(lambda itm: self._dialog_use_item(itm, dialog))
        dialog_layout.addWidget(list_widget)
        use_button = QtWidgets.QPushButton("Use")
        use_button.clicked.connect(lambda: self._dialog_use_item(list_widget.currentItem(), dialog))
        dialog_layout.addWidget(use_button)
        dialog.exec()

    def _dialog_use_item(self, item: Optional[QtWidgets.QListWidgetItem], dialog: QtWidgets.QDialog) -> None:
        if not item:
            return
        item_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
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
            dialog.accept()

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
            QtWidgets.QMessageBox.information(
                self,
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
        QtWidgets.QMessageBox.information(self, "Inventory", f"Used {definition.get('name', item_id)}.")
        return True

    def _equip_weapon(self, item_id: str, definition: Dict[str, Any], *, notify: bool = True) -> bool:
        slot = self._weapon_slot(definition)
        current = self.equipment.get(slot)
        if current == item_id:
            if notify:
                QtWidgets.QMessageBox.information(
                    self,
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
            QtWidgets.QMessageBox.information(
                self,
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
        self.title_label.setText(display_title)
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

    def _option_available(self, option) -> bool:
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

    def _handle_room_option(self, option) -> None:
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
        self.close()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802 (Qt naming)
        self.on_close()
        event.accept()

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # noqa: N802 (Qt naming)
        key = event.key()
        if QtCore.Qt.Key.Key_1 <= key <= QtCore.Qt.Key.Key_4:
            self._on_option(key - QtCore.Qt.Key.Key_1)
            return
        if key in (QtCore.Qt.Key.Key_I, QtCore.Qt.Key.Key_Return):
            self.open_inventory()
            return
        super().keyPressEvent(event)

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


def create_app(
    rooms: Dict[str, RoomSpec],
    battles: Dict[str, BattleSpec],
    images: Dict[str, str],
    sounds: Dict[str, str],
    defaults_module,
) -> GameApp:
    app = _ensure_application()
    return GameApp(rooms, battles, images, sounds, defaults_module, app)
