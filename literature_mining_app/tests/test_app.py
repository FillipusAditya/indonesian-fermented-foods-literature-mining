"""Exercise form validation, result persistence, and failed searches."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import requests
from streamlit.testing.v1 import AppTest
from streamlit.proto.TextInput_pb2 import TextInput

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from europe_pmc import COLUMNS


class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=20).run()

    def test_initial_page_and_blank_query(self):
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.text_area[0].value, "")
        self.assertEqual(len(self.app.text_input), 0)
        self.assertEqual(len(self.app.get("download_button")), 0)
        self.app.text_area[0].set_value(" ")
        self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        self.assertIn("Enter a query", self.app.warning[0].value)

    def test_result_survives_rerun_and_failure_clears_download(self):
        frame = pd.DataFrame([{"title": "Tempeh", "abstract": "Abstract"}], columns=COLUMNS)
        self.app.text_area[0].set_value("tempeh")
        with patch("europe_pmc.search_papers", return_value=(frame, 1)):
            self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.get("download_button")), 1)
        self.assertEqual(self.app.metric[1].value, "1")
        self.app.run()
        self.assertEqual(len(self.app.get("download_button")), 1)
        with patch("europe_pmc.search_papers", side_effect=requests.Timeout):
            self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.get("download_button")), 0)
        self.assertIn("too long", self.app.error[0].value)

    def test_all_results_and_no_matches(self):
        frame = pd.DataFrame(columns=COLUMNS)
        self.app.text_area[0].set_value("tempeh")
        self.app.selectbox[1].select("All results")
        with patch("europe_pmc.search_papers", return_value=(frame, 0)) as search:
            self.app.button[0].click().run()
        self.assertIsNone(search.call_args.args[1])
        self.assertFalse(self.app.exception)
        self.assertTrue(any("No matching articles" in item.value for item in self.app.info))
        self.assertEqual(len(self.app.get("download_button")), 1)

    def test_openalex_key_is_conditional_and_optional(self):
        self.app.selectbox[0].select("OpenAlex").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.text_input[0].label, "OpenAlex API key (optional)")
        self.assertEqual(self.app.text_input[0].proto.type, TextInput.PASSWORD)
        self.assertEqual(self.app.text_area[0].value, "")
        self.assertIn("OpenAlex", self.app.expander[0].label)
        self.app.text_area[0].set_value('"fermented food" AND Indonesia')
        frame = pd.DataFrame(columns=COLUMNS)
        with patch("openalex.search_papers", return_value=(frame, 0)) as search:
            self.app.button[0].click().run()
        self.assertEqual(search.call_args.args[1:3], ("", 100))
        self.assertFalse(self.app.exception)

    def test_openalex_query_and_export_without_key(self):
        self.app.selectbox[0].select("OpenAlex").run()
        query = '(tempe OR tempeh) AND Indonesia'
        self.app.text_area[0].set_value(query)
        self.app.text_input[0].set_value("test-secret")
        frame = pd.DataFrame([{"title": "Tempeh", "query": query}], columns=COLUMNS)
        with patch("openalex.search_papers", return_value=(frame, 1)) as search:
            self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(search.call_args.args[:3], (query, "test-secret", 100))
        result = self.app.session_state["search_result"]
        self.assertEqual(result["database"], "OpenAlex")
        self.assertTrue(result["filename"].startswith("openalex_"))
        self.assertNotIn(b"test-secret", result["csv"])
        self.app.selectbox[0].select("Europe PMC").run()
        self.assertEqual(len(self.app.get("download_button")), 0)
        self.assertEqual(len(self.app.text_input), 0)

    def test_new_provider_fields_and_optional_keys(self):
        empty = pd.DataFrame(columns=COLUMNS)
        for database, module, email_required in [
            ("Crossref", "crossref", False),
            ("Semantic Scholar", "semantic_scholar", False),
            ("PubMed", "pubmed", True),
        ]:
            with self.subTest(database=database):
                self.app.selectbox[0].select(database).run()
                self.assertFalse(self.app.exception)
                self.assertIn(database, self.app.expander[0].label)
                self.app.text_area[0].set_value("tempeh")
                if email_required:
                    with patch(f"{module}.search_papers") as search:
                        self.app.button[0].click().run()
                    search.assert_not_called()
                    self.assertIn("contact email", self.app.warning[0].value)
                    self.app.text_input[0].set_value("researcher@example.org")
                with patch(f"{module}.search_papers", return_value=(empty, 0)) as search:
                    self.app.button[0].click().run()
                self.assertFalse(self.app.exception)
                if database == "Semantic Scholar":
                    self.assertEqual(search.call_args.args[1], "")
                else:
                    self.assertEqual(search.call_args.args[2], "")
                self.assertEqual(self.app.session_state["search_result"]["database"], database)

    def test_invalid_optional_email_is_rejected_before_request(self):
        self.app.selectbox[0].select("Crossref").run()
        self.app.text_input[0].set_value("invalid-address")
        self.app.text_area[0].set_value("tempeh")
        with patch("crossref.search_papers") as search:
            self.app.button[0].click().run()
        search.assert_not_called()
        self.assertIn("valid contact email", self.app.warning[0].value)

    def test_openalex_auth_error_is_friendly_and_does_not_leak_key(self):
        self.app.selectbox[0].select("OpenAlex").run()
        self.app.text_area[0].set_value("tempeh")
        self.app.text_input[0].set_value("test-secret")
        response = requests.Response()
        response.status_code = 401
        error = requests.HTTPError("test-secret", response=response)
        with patch("openalex.search_papers", side_effect=error):
            self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        self.assertIn("rejected the API key", self.app.error[0].value)
        self.assertNotIn("test-secret", self.app.error[0].value)
        self.assertEqual(len(self.app.get("download_button")), 0)

    def test_pubmed_retry_and_validation_errors_do_not_crash_the_page(self):
        self.app.selectbox[0].select("PubMed").run()
        self.app.text_input[0].set_value("researcher@example.org")
        self.app.text_area[0].set_value("tempeh[tiab]")
        for error, message in [
            (requests.exceptions.RetryError("retry exhausted"), "after retries"),
            (ValueError("PubMed returned an invalid search response."), "invalid search response"),
        ]:
            with self.subTest(error=type(error).__name__):
                with patch("pubmed.search_papers", side_effect=error):
                    self.app.button[0].click().run()
                self.assertFalse(self.app.exception)
                self.assertIn(message, self.app.error[0].value)
                self.assertEqual(len(self.app.get("download_button")), 0)

    def test_additional_providers_credentials_and_dispatch(self):
        empty = pd.DataFrame(columns=COLUMNS)
        for database, module, requires_key, has_key in [
            ("CORE", "core", False, True), ("DOAJ", "doaj", False, False),
            ("Springer Nature", "springer_nature", True, True),
            ("Scopus", "scopus", True, True), ("arXiv", "arxiv", False, False),
        ]:
            with self.subTest(database=database):
                self.app.selectbox[0].select(database).run()
                self.assertFalse(self.app.exception)
                self.assertIn(database, self.app.expander[0].label)
                self.assertEqual(bool(self.app.text_input), has_key)
                self.app.text_area[0].set_value("manual query")
                if requires_key:
                    with patch(f"{module}.search_papers") as search:
                        self.app.button[0].click().run()
                    search.assert_not_called()
                    self.assertIn("API key", self.app.warning[0].value)
                    self.app.text_input[0].set_value("test-secret")
                if database == "Scopus":
                    self.app.text_input[1].set_value("test-inst-token")
                    self.app.checkbox[0].check().run()
                with patch(f"{module}.search_papers", return_value=(empty, 0)) as search:
                    self.app.button[0].click().run()
                self.assertFalse(self.app.exception)
                self.assertEqual(search.call_args.args[0], "manual query")
                result = self.app.session_state["search_result"]
                self.assertEqual(result["database"], database)
                self.assertNotIn(b"test-secret", result["csv"])
                if database == "Scopus":
                    self.assertEqual(search.call_args.kwargs, {"inst_token": "test-inst-token", "use_cursor": True})
                    self.assertNotIn(b"test-inst-token", result["csv"])

    def test_all_results_disables_article_limit_for_new_provider(self):
        self.app.selectbox[0].select("DOAJ").run()
        self.app.selectbox[1].select("All results").run()
        self.assertTrue(self.app.number_input[0].disabled)
        self.app.selectbox[1].select("Limit article count").run()
        self.assertFalse(self.app.number_input[0].disabled)


if __name__ == "__main__":
    unittest.main()
