import unittest
from dataclasses import replace

from text_adventure.engine import loader, validator
from engine.models import OptionSpec
from text_adventure.game import defaults


class ValidatorTests(unittest.TestCase):
    def test_missing_room_detection(self) -> None:
        images, sounds, rooms, battles = loader.load_all()
        start_room = rooms[defaults.START_ROOM_ID]
        broken_room = replace(start_room, options=start_room.options + [OptionSpec(label="Fall into void", to="missing")])
        broken_rooms = dict(rooms)
        broken_rooms[start_room.id] = broken_room

        ok, message = validator.validate(broken_rooms, images, sounds, battles, defaults)
        self.assertFalse(ok)
        self.assertIn("missing room", message.lower())


if __name__ == "__main__":
    unittest.main()
