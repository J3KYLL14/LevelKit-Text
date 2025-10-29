"""Cross-platform audio helpers using only the Python standard library."""

import platform
import subprocess
from pathlib import Path
from typing import Dict, Optional


_CURRENT_PROCESS: Optional[subprocess.Popen] = None
_CURRENT_KEY: Optional[str] = None


def _stop_process() -> None:
    global _CURRENT_PROCESS, _CURRENT_KEY
    if _CURRENT_PROCESS is not None:
        _CURRENT_PROCESS.terminate()
        _CURRENT_PROCESS = None
    _CURRENT_KEY = None


def play_music(key: Optional[str], sounds: Dict[str, str], base_path: Path) -> None:
    """Play the sound registered for ``key`` if available."""
    global _CURRENT_PROCESS, _CURRENT_KEY
    if key is None:
        stop_music()
        return
    if key == _CURRENT_KEY:
        return
    stop_music()
    filename = sounds.get(key)
    if not filename:
        return
    file_path = base_path / filename
    if not file_path.exists():
        return
    system = platform.system().lower()
    if system.startswith("win"):
        try:
            import winsound

            winsound.PlaySound(str(file_path), winsound.SND_ASYNC | winsound.SND_LOOP)
            _CURRENT_KEY = key
        except Exception:
            pass
        return
    command = []
    if system == "darwin":
        command = ["afplay", str(file_path)]
    else:
        command = ["paplay", str(file_path)]
        try:
            _CURRENT_PROCESS = subprocess.Popen(command)
            _CURRENT_KEY = key
            return
        except FileNotFoundError:
            command = ["aplay", str(file_path)]
    try:
        _CURRENT_PROCESS = subprocess.Popen(command)
        _CURRENT_KEY = key
    except Exception:
        _CURRENT_PROCESS = None
        _CURRENT_KEY = None


def stop_music() -> None:
    """Stop any currently playing music."""
    system = platform.system().lower()
    if system.startswith("win"):
        try:
            import winsound

            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
    else:
        _stop_process()
