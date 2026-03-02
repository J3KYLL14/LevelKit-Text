"""Entry point for the LevelKit-Text experience."""

import sys

from engine import core, loader, validator
from game import defaults


def main() -> int:
    images, sounds, rooms, battles = loader.load_all()
    if "--validate" in sys.argv[1:]:
        ok, message = validator.validate(rooms, images, sounds, battles, defaults)
        print(message)
        return 0 if ok else 1

    app = core.create_app(rooms, battles, images, sounds, defaults)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
