"""Exercise the visual builder and multi-source Streamlit workflow."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import requests
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from schema import COLUMNS


class MultiUITests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=30).run()
        self.app.radio(key="search_mode").set_value("Multiple Databases").run()

    def test_mode_has_eight_checkboxes_and_no_free_text_query(self):
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.text_area), 0)
        choices = [item.label for item in self.app.checkbox if str(item.key).startswith("multi_select_")]
        self.assertEqual(len(choices), 8)
        self.assertNotIn("Crossref", choices)
        self.assertNotIn("Springer Nature", choices)
        self.assertTrue(self.app.button(key="search_multi").disabled)

    def test_builder_add_remove_and_phrase_preview(self):
        self.app.text_input(key="builder_term_0_0").set_value("tempe").run()
        self.app.button(key="add_term_0").click().run()
        self.assertEqual(self.app.text_input(key="builder_term_0_0").value, "tempe")
        self.app.text_input(key="builder_term_0_1").set_value("tempeh").run()
        self.app.button(key="add_group").click().run()
        self.app.text_input(key="builder_term_1_0").set_value("fermented food")
        self.app.checkbox(key="builder_phrase_1_0").check().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any('(tempe OR tempeh)' in item.value and '"fermented food"' in item.value for item in self.app.code))
        self.app.button(key="remove_term_0_0").click().run()
        self.assertEqual(self.app.text_input(key="builder_term_0_1").value, "tempeh")
        self.app.button(key="remove_group_1").click().run()
        self.assertFalse(self.app.exception)

    def test_credentials_follow_selection_and_validation_precedes_network(self):
        self.app.checkbox(key="multi_select_PubMed").check().run()
        self.app.checkbox(key="multi_select_Scopus").check().run()
        self.app.text_input(key="builder_term_0_0").set_value("tempeh").run()
        self.assertEqual(self.app.text_input(key="multi_email_PubMed").value, "")
        self.assertEqual(self.app.text_input(key="multi_api_key_Scopus").value, "")
        with patch("providers.search") as search:
            self.app.button(key="search_multi").click().run()
        search.assert_not_called()
        self.assertEqual(len(self.app.warning), 2)
        self.assertFalse(self.app.exception)

    def test_combined_csv_persists_with_one_failed_source(self):
        self.app.checkbox(key="multi_select_Europe PMC").check().run()
        self.app.checkbox(key="multi_select_DOAJ").check().run()
        self.app.text_input(key="builder_term_0_0").set_value("tempeh").run()
        frame = pd.DataFrame([{"title": "Tempeh", "abstract": "Abstract"}], columns=COLUMNS)
        with patch("providers.search", side_effect=[requests.Timeout(), (frame, 1)]) as search:
            self.app.button(key="search_multi").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual([call.args[0] for call in search.call_args_list], ["Europe PMC", "DOAJ"])
        result = self.app.session_state["multi_result"]
        self.assertEqual(result["frame"].source_database.tolist(), ["DOAJ"])
        self.assertIn(b"standard_query", result["csv"])
        self.assertIn(b"executed_query", result["csv"])
        self.assertEqual(len(self.app.get("download_button")), 1)
        self.assertTrue(any("Some sources failed" in warning.value for warning in self.app.warning))
        with patch("providers.search") as search:
            self.app.run()
        search.assert_not_called()
        self.assertEqual(len(self.app.get("download_button")), 1)

    def test_no_download_when_every_source_fails(self):
        self.app.checkbox(key="multi_select_DOAJ").check().run()
        self.app.text_input(key="builder_term_0_0").set_value("tempeh").run()
        with patch("providers.search", side_effect=ValueError("Query failed.")):
            self.app.button(key="search_multi").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.get("download_button")), 0)
        self.assertIn("Every selected source failed", self.app.error[0].value)

    def test_all_results_disables_limit_and_is_forwarded_per_source(self):
        self.app.checkbox(key="multi_select_DOAJ").check().run()
        self.app.text_input(key="builder_term_0_0").set_value("tempeh").run()
        self.app.selectbox(key="multi_scope").select("All results").run()
        self.assertTrue(self.app.number_input(key="multi_limit").disabled)
        with patch("providers.search", return_value=(pd.DataFrame(columns=COLUMNS), 0)) as search:
            self.app.button(key="search_multi").click().run()
        self.assertIsNone(search.call_args.args[3])
        self.assertEqual(len(self.app.get("download_button")), 1)
        self.app.selectbox(key="multi_scope").select("Limit articles per API").run()
        self.assertFalse(self.app.number_input(key="multi_limit").disabled)

    def test_invalid_builder_makes_no_requests(self):
        self.app.checkbox(key="multi_select_DOAJ").check().run()
        self.app.text_input(key="builder_term_0_0").set_value("tempe*").run()
        with patch("providers.search") as search:
            self.app.button(key="search_multi").click().run()
        search.assert_not_called()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.warning)


if __name__ == "__main__":
    unittest.main()
