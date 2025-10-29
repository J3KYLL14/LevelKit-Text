"""Classroom text adventure engine package."""

import sys

from . import engine as _engine
from . import game as _game

sys.modules.setdefault("engine", _engine)
sys.modules.setdefault("engine.models", _engine.models)
sys.modules.setdefault("engine.loader", _engine.loader)
sys.modules.setdefault("engine.core", _engine.core)
sys.modules.setdefault("engine.audio", _engine.audio)
sys.modules.setdefault("engine.save", _engine.save)
sys.modules.setdefault("engine.validator", _engine.validator)

sys.modules.setdefault("game", _game)
sys.modules.setdefault("game.defaults", _game.defaults)

__all__ = ["engine", "game"]
