import unittest

from text_adventure.engine import loader
from text_adventure.game import defaults


class LoaderTests(unittest.TestCase):
    def test_loads_content(self) -> None:
        images, sounds, rooms, battles = loader.load_all()
        self.assertTrue(images)
        self.assertTrue(sounds)
        self.assertTrue(rooms)
        self.assertTrue(battles)
        self.assertIn(defaults.START_ROOM_ID, rooms)
        for room in rooms.values():
            self.assertEqual(room.id, room.id)  # sanity check instantiation
        self.assertIn("simple_goblin", battles)


if __name__ == "__main__":
    unittest.main()
