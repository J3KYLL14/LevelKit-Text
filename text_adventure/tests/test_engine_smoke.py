import unittest

import tkinter as tk

from text_adventure.engine import core, loader
from text_adventure.game import defaults


class EngineSmokeTests(unittest.TestCase):
    def test_app_initialises(self) -> None:
        try:
            root = tk.Tk()
            root.destroy()
        except tk.TclError:
            self.skipTest("Tk unavailable")

        images, sounds, rooms, battles = loader.load_all()
        app = core.create_app(rooms, battles, images, sounds, defaults)
        app.root.update_idletasks()
        app.on_close()


if __name__ == "__main__":
    unittest.main()
