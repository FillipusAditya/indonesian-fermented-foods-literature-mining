"""Test OpenAlex pagination, notebook mapping, and credentials handling."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openalex import normalize_paper, search_papers
from schema import COLUMNS


def response(papers, total, cursor=None):
    result = Mock()
    result.json.return_value = {
        "meta": {"count": total, "next_cursor": cursor}, "results": papers,
    }
    return result


class OpenAlexTests(unittest.TestCase):
    def setUp(self):
        session_patch = patch("openalex.requests.Session")
        self.session = session_patch.start().return_value.__enter__.return_value
        self.addCleanup(session_patch.stop)
        sleep_patch = patch("openalex.time.sleep")
        sleep_patch.start()
        self.addCleanup(sleep_patch.stop)

    def test_manual_query_pagination_and_credentials(self):
        self.session.get.side_effect = [
            response([{"id": "W1"}], 2, "next"),
            response([{"id": "W2"}], 2),
        ]
        query = '(tempe OR tempeh) AND "fermented food"'
        progress = Mock()
        frame, total = search_papers(query, "test-secret", None, progress)
        self.assertEqual((len(frame), total), (2, 2))
        self.assertEqual(list(frame.columns), COLUMNS)
        self.assertEqual(frame.openalex_id.tolist(), ["W1", "W2"])
        self.assertEqual(frame.source_database.tolist(), ["OpenAlex", "OpenAlex"])
        self.session.headers.update.assert_called_once_with({
            "User-Agent": "IndonesiaFermentedFoodsMining/1.0",
            "Authorization": "Bearer test-secret",
        })
        for call in self.session.get.call_args_list:
            self.assertEqual(call.kwargs["params"]["search"], query)
            self.assertNotIn("api_key", call.kwargs["params"])
        self.assertEqual(self.session.get.call_args.kwargs["params"]["cursor"], "next")
        self.assertNotIn("test-secret", frame.to_csv(index=False))
        progress.assert_called_with(2, 2)

    def test_notebook_mapping_and_abstract_word_order(self):
        record = normalize_paper({
            "id": "W1", "doi": "https://doi.org/10.1/example", "title": "Tempeh",
            "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/123"},
            "abstract_inverted_index": {"food": [1, 3], "Fermented": [0], "is": [2]},
            "authorships": [{"author": {"display_name": "A"}}, {"author": {"display_name": "B"}}],
            "primary_location": {"source": {"display_name": "Journal"},
                                 "pdf_url": "https://example.org/p.pdf", "landing_page_url": "https://example.org"},
            "open_access": {"is_oa": True}, "publication_year": 2025,
            "type": "article", "language": "en", "cited_by_count": 4,
        }, "tempeh")
        self.assertEqual(record["abstract"], "Fermented food is food")
        self.assertEqual(record["authors"], "A; B")
        self.assertEqual(record["journal"], "Journal")
        self.assertTrue(record["is_open_access"])
        self.assertEqual(record["citation_count"], 4)
        self.assertEqual(record["pdf_url"], "https://example.org/p.pdf")
        self.assertIsNone(record["europe_pmc_id"])

    def test_missing_metadata_and_empty_results(self):
        self.assertIsNone(normalize_paper({}, "q")["abstract"])
        self.assertIsNone(normalize_paper({}, "q")["journal"])
        self.session.get.return_value = response([], 0)
        frame, total = search_papers("missing", "key")
        self.assertTrue(frame.empty)
        self.assertEqual(total, 0)
        self.assertEqual(frame.to_csv(index=False).strip(), ",".join(COLUMNS))

    def test_article_limit(self):
        self.session.get.return_value = response([{"id": "W1"}, {"id": "W2"}], 10, "next")
        frame, total = search_papers("tempeh", "key", 1)
        self.assertEqual((len(frame), total), (1, 10))
        self.assertEqual(self.session.get.call_args.kwargs["params"]["per_page"], 1)
        self.assertEqual(self.session.get.call_count, 1)

    def test_invalid_inputs_make_no_requests(self):
        for query, key, limit in [(" ", "key", 1), ("tempeh", "key", 0)]:
            with self.assertRaises(ValueError):
                search_papers(query, key, limit)
        self.session.get.assert_not_called()

    def test_optional_key_first_page(self):
        self.session.get.return_value = response([{"id": "W1"}], 300, "next")
        frame, total = search_papers("tempeh", max_results=1)
        self.assertEqual((len(frame), total), (1, 300))
        headers = self.session.headers.update.call_args.args[0]
        self.assertNotIn("Authorization", headers)

    def test_optional_key_does_not_allow_silent_truncation(self):
        self.session.get.return_value = response([{"id": "W1"}], 300, "next")
        with self.assertRaisesRegex(ValueError, "beyond the first page"):
            search_papers("tempeh", max_results=None)
        self.assertEqual(self.session.get.call_count, 1)

    def test_invalid_payload(self):
        self.session.get.return_value.json.return_value = {"error": "bad query"}
        with self.assertRaisesRegex(ValueError, "invalid response"):
            search_papers("tempeh", "key")

    def test_stalled_cursor(self):
        self.session.get.return_value = response([{"id": "W1"}], 10, "*")
        with self.assertRaisesRegex(ValueError, "stopped"):
            search_papers("tempeh", "key", None)

    def test_later_failure_does_not_return_partial_success(self):
        self.session.get.side_effect = [response([{"id": "W1"}], 2, "next"), requests.Timeout()]
        with self.assertRaises(requests.Timeout):
            search_papers("tempeh", "key", None)

    def test_authentication_http_error(self):
        self.session.get.return_value.raise_for_status.side_effect = requests.HTTPError("401")
        with self.assertRaises(requests.HTTPError):
            search_papers("tempeh", "key")


if __name__ == "__main__":
    unittest.main()
