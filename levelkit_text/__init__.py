"""LevelKit-Text engine package."""

import sys
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_VENDOR_DIR = _PACKAGE_DIR / "vendor"
if _VENDOR_DIR.exists():
    vendor_path = str(_VENDOR_DIR)
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)

from . import engine as _engine
from . import game as _game

sys.modules.setdefault("engine", _engine)
sys.modules.setdefault("engine.models", _engine.models)
sys.modules.setdefault("engine.loader", _engine.loader)
sys.modules.setdefault("engine.core", _engine.core)
sys.modules.setdefault("engine.audio", _engine.audio)
sys.modules.setdefault("engine.validator", _engine.validator)

sys.modules.setdefault("game", _game)
sys.modules.setdefault("game.defaults", _game.defaults)

__all__ = ["engine", "game"]
