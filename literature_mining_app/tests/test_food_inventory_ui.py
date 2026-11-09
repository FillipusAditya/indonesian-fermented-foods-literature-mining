"""Check the inventory page and navigation from a visitor's perspective."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class FoodInventoryPageTests(unittest.TestCase):
    def test_browse_search_and_return_to_tools(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()
        self.assertEqual(app.get("segmented_control")[0].value, "Tools")

        app.get("segmented_control")[0].set_value("Indonesia Fermented Food").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("download_button")), 0)
        self.assertEqual(len(app.get("pills")), 1)
        self.assertTrue(any(button.label == "Next →" for button in app.button))

        app.get("segmented_control")[1].set_value("Indonesia").run()
        self.assertFalse(app.exception)
        self.assertTrue(any(button.label == "Berikutnya →" for button in app.button))

        app.text_input(key="food_search").set_value("tempe").run()
        self.assertFalse(app.exception)
        self.assertGreater(len(app.button), 0)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state["selected_food_id"])

        app.get("segmented_control")[0].set_value("Tools").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.text_area), 1)
        self.assertEqual(app.selectbox[0].label, "Basis data literatur")
        self.assertTrue(any("Penelusuran Literatur" in item.value for item in app.markdown))

        app.radio(key="search_mode_idn").set_value("Beberapa Basis Data").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.subheader[0].value, "Pilih Basis Data")


if __name__ == "__main__":
    unittest.main()
