"""Entry point for the LevelKit-Text experience."""

import sys
import traceback

from engine import core, loader, validator
from game import defaults


def main() -> int:
    try:
        images, sounds, rooms, battles = loader.load_all()
        if "--validate" in sys.argv[1:]:
            ok, message = validator.validate(rooms, images, sounds, battles, defaults)
            print(message)
            return 0 if ok else 1

        app = core.create_app(rooms, battles, images, sounds, defaults)
        app.run()
        return 0
    except loader.LoaderError as exc:
        print(f"LevelKit could not start.\n{exc}")
        return 1
    except Exception as exc:
        brief = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        print(
            "LevelKit could not start because something went wrong while the game was running.\n"
            f"Problem: {brief}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
