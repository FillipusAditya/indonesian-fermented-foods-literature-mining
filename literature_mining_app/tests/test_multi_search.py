"""Sequential execution, failure isolation, provenance, and export integrity."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from multi_search import EXPORT_COLUMNS, run_searches
from schema import COLUMNS


def frame(title="Title", doi="10.1/shared"):
    return pd.DataFrame([{"title": title, "doi": doi}], columns=COLUMNS)


class MultiSearchTests(unittest.TestCase):
    def test_fixed_order_sequential_callbacks_and_combined_provenance(self):
        calls, events = [], []
        def search(database, query, credentials, max_results, on_progress):
            calls.append(database)
            on_progress(1, 1)
            return frame(), 1
        queries = {"DOAJ": "doaj query", "Europe PMC": "pmc query"}
        with patch("providers.search", side_effect=search):
            combined, summaries = run_searches(queries, "standard query", {}, 10, events.append)
        self.assertEqual(calls, ["Europe PMC", "DOAJ"])
        self.assertEqual(combined.source_database.tolist(), calls)
        self.assertEqual(combined.executed_query.tolist(), ["pmc query", "doaj query"])
        self.assertEqual(combined.standard_query.tolist(), ["standard query"] * 2)
        self.assertEqual(combined.doi.tolist(), ["10.1/shared"] * 2)
        self.assertEqual(list(combined.columns), EXPORT_COLUMNS)
        self.assertEqual([row["status"] for row in summaries], ["Completed", "Completed"])
        finished_first = next(i for i, event in enumerate(events) if event["database"] == "Europe PMC" and event["status"] == "Completed")
        started_second = next(i for i, event in enumerate(events) if event["database"] == "DOAJ" and event["status"] == "Running")
        self.assertLess(finished_first, started_second)
        self.assertEqual(events[-1]["completed"], 2)

    def test_failed_source_discards_partial_progress_and_continues(self):
        def search(database, query, credentials, max_results, on_progress):
            on_progress(1, 2)
            if database == "Europe PMC":
                raise requests.Timeout("secret URL")
            return frame(), 1
        with patch("providers.search", side_effect=search):
            combined, summaries = run_searches({"Europe PMC": "q", "DOAJ": "q"}, "q", {}, None)
        self.assertEqual(combined.source_database.tolist(), ["DOAJ"])
        self.assertEqual(summaries[0]["status"], "Failed")
        self.assertEqual(summaries[0]["fetched"], 0)
        self.assertNotIn("secret URL", str(summaries))

    def test_all_credentials_are_validated_before_any_request(self):
        with patch("providers.search") as search:
            with self.assertRaisesRegex(ValueError, "Scopus API key"):
                run_searches({"Europe PMC": "q", "Scopus": "q"}, "q", {}, 100)
            search.assert_not_called()
        with patch("providers.search") as search:
            with self.assertRaisesRegex(ValueError, "contact email"):
                run_searches({"PubMed": "q"}, "q", {}, 100)
            search.assert_not_called()

    def test_empty_success_differs_from_all_failed(self):
        with patch("providers.search", return_value=(pd.DataFrame(columns=COLUMNS), 0)):
            combined, summaries = run_searches({"DOAJ": "q"}, "q", {}, 100)
        self.assertTrue(combined.empty)
        self.assertEqual(summaries[0]["status"], "Completed")
        with patch("providers.search", side_effect=ValueError("Source failed.")):
            combined, summaries = run_searches({"DOAJ": "q"}, "q", {}, 100)
        self.assertTrue(combined.empty)
        self.assertEqual(summaries[0]["status"], "Failed")

    def test_limit_and_estimated_counts_are_reported(self):
        with patch("providers.search", return_value=(frame(), 100)):
            _, summaries = run_searches({"DOAJ": "q"}, "q", {}, 1)
        self.assertEqual(summaries[0]["status"], "Limited")
        with patch("providers.search", return_value=(frame(), 100)):
            _, summaries = run_searches({"Semantic Scholar": "q"}, "q", {}, None)
        self.assertEqual(summaries[0]["status"], "Completed")
        self.assertIn("estimated", summaries[0]["message"])

    def test_keys_and_accidental_extra_columns_never_enter_export(self):
        result = frame()
        result["api_key"] = "test-secret"
        with patch("providers.search", return_value=(result, 1)):
            combined, _ = run_searches(
                {"Scopus": "q"}, "q", {"Scopus": {"api_key": "test-secret", "inst_token": "test-token"}}, 100,
            )
        csv = combined.to_csv(index=False)
        self.assertNotIn("api_key", csv)
        self.assertNotIn("test-secret", csv)
        self.assertNotIn("test-token", csv)

    def test_unexpected_failure_is_sanitized_and_next_source_runs(self):
        with patch("providers.search", side_effect=[TypeError("test-secret"), (frame(), 1)]):
            combined, summaries = run_searches({"Europe PMC": "q", "DOAJ": "q"}, "q", {}, 100)
        self.assertEqual(len(combined), 1)
        self.assertNotIn("test-secret", str(summaries))

    def test_empty_selection_and_unsupported_sources_are_rejected(self):
        for queries in [{}, {"Crossref": "q"}, {"Europe PMC": ""}]:
            with self.subTest(queries=queries):
                with self.assertRaises(ValueError):
                    run_searches(queries, "q", {}, 100)


if __name__ == "__main__":
    unittest.main()
