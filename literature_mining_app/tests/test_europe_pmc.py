"""Offline checks for retrieval and the notebook-compatible export."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from europe_pmc import COLUMNS, normalize_paper, search_papers


def response(papers, total, cursor=None):
    result = Mock()
    result.json.return_value = {
        "hitCount": total,
        "resultList": {"result": papers},
        "nextCursorMark": cursor,
    }
    return result


class SearchTests(unittest.TestCase):
    def setUp(self):
        session_patch = patch("europe_pmc.requests.Session")
        self.session = session_patch.start().return_value.__enter__.return_value
        self.addCleanup(session_patch.stop)
        sleep_patch = patch("europe_pmc.time.sleep")
        sleep_patch.start()
        self.addCleanup(sleep_patch.stop)

    def test_cursor_pagination_and_schema(self):
        self.session.get.side_effect = [
            response([{"id": "1", "source": "MED"}], 2, "next"),
            response([{"id": "2", "source": "MED"}], 2, "last"),
        ]
        progress = Mock()
        frame, total = search_papers("tempeh", None, progress)
        self.assertEqual(total, 2)
        self.assertEqual(list(frame.columns), COLUMNS)
        self.assertEqual(frame.europe_pmc_id.tolist(), ["1", "2"])
        self.assertEqual(self.session.get.call_args_list[1].kwargs["params"]["cursorMark"], "next")
        self.assertEqual(self.session.get.call_args.kwargs["params"]["resultType"], "core")
        progress.assert_called_with(2, 2)

    def test_limit_and_query_provenance(self):
        self.session.get.return_value = response([{"id": "1"}, {"id": "2"}], 20, "next")
        frame, total = search_papers("  tempeh  ", 1)
        self.assertEqual((len(frame), total), (1, 20))
        self.assertEqual(frame.iloc[0]["query"], "tempeh")
        self.assertEqual(self.session.get.call_args.kwargs["params"]["pageSize"], 1)
        self.assertEqual(self.session.get.call_count, 1)

    def test_empty_results_have_csv_headers(self):
        self.session.get.return_value = response([], 0)
        frame, total = search_papers("missing")
        self.assertTrue(frame.empty)
        self.assertEqual(total, 0)
        self.assertEqual(frame.to_csv(index=False).strip(), ",".join(COLUMNS))

    def test_missing_optional_metadata(self):
        record = normalize_paper({"id": "1", "pubYear": "unknown"}, "q")
        self.assertIsNone(record["publication_year"])
        self.assertIsNone(record["journal"])
        self.assertIsNone(record["pdf_url"])
        self.assertIsNone(record["is_open_access"])

    def test_notebook_mapping_and_unicode_csv(self):
        self.session.get.return_value = response([{
            "id": "123", "source": "MED", "pmid": "123", "pubYear": "2025",
            "title": "Tempe – fermentasi", "abstractText": "<p>Abstrak, baris\nbaru</p>",
            "journalInfo": {"journal": {"title": "Food Journal"}},
            "fullTextUrlList": {"fullTextUrl": [{"documentStyle": "pdf", "url": "https://example.org/p.pdf"}]},
            "pubTypeList": {"pubType": ["Review", "Journal Article"]},
            "isOpenAccess": "Y",
        }], 1)
        frame, _ = search_papers("tempe")
        paper = frame.iloc[0]
        self.assertEqual(paper["journal"], "Food Journal")
        self.assertEqual(paper["publication_year"], 2025)
        self.assertEqual(paper["publication_type"], "Review; Journal Article")
        self.assertEqual(paper["pdf_url"], "https://example.org/p.pdf")
        self.assertTrue(paper["is_open_access"])
        self.assertEqual(paper["url"], "https://europepmc.org/article/MED/123")
        self.assertTrue(frame.to_csv(index=False).encode("utf-8-sig").startswith(b"\xef\xbb\xbf"))

    def test_stalled_cursor_does_not_return_partial_success(self):
        self.session.get.return_value = response([{"id": "1"}], 20, "*")
        with self.assertRaisesRegex(ValueError, "stopped"):
            search_papers("tempeh", None)

    def test_failure_on_later_page_does_not_return_partial_success(self):
        self.session.get.side_effect = [
            response([{"id": "1"}], 2, "next"), requests.Timeout("timeout"),
        ]
        with self.assertRaises(requests.Timeout):
            search_papers("tempeh", None)

    def test_api_error_and_invalid_payload(self):
        self.session.get.return_value.json.return_value = {"errMsg": "Invalid query"}
        with self.assertRaisesRegex(ValueError, "valid"):
            search_papers("TITLE:(")

    def test_http_error(self):
        self.session.get.return_value.raise_for_status.side_effect = requests.HTTPError("400")
        with self.assertRaises(requests.HTTPError):
            search_papers("TITLE:(")

    def test_blank_query_and_invalid_limit(self):
        for query, limit in [(" ", 5), ("tempeh", 0)]:
            with self.assertRaises(ValueError):
                search_papers(query, limit)
        self.session.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
