"""Offline tests for new provider pagination and credential boundaries."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import crossref
import pubmed
import semantic_scholar
from common import validate_email
from schema import COLUMNS


def json_response(data):
    response = Mock()
    response.json.return_value = data
    return response


def crossref_response(papers, total, cursor="next"):
    return json_response({"message": {"items": papers, "total-results": total, "next-cursor": cursor}})


def semantic_response(papers, total, token=None):
    return json_response({"data": papers, "total": total, "token": token})


def history_response(total):
    return json_response({"esearchresult": {"count": str(total), "querykey": "1", "webenv": "history"}})


def medline_response(ids):
    response = Mock()
    response.text = "\n".join(
        f"PMID- {identifier}\nTI  - Tempeh\nAB  - Abstract\nDP  - 2025 Jan\n\n"
        for identifier in ids
    )
    return response


class NewProviderTests(unittest.TestCase):
    def session_for(self, module):
        session_patch = patch(f"{module}.create_session")
        factory = session_patch.start()
        self.addCleanup(session_patch.stop)
        sleep_patch = patch(f"{module}.time.sleep")
        sleep_patch.start()
        self.addCleanup(sleep_patch.stop)
        return factory, factory.return_value.__enter__.return_value

    def test_crossref_public_access_and_exact_limit(self):
        factory, session = self.session_for("crossref")
        session.get.return_value = crossref_response([{"DOI": "10.1/a"}, {"DOI": "10.1/b"}], 10)
        frame, total = crossref.search_papers("tempeh Indonesia", max_results=1)
        self.assertEqual((len(frame), total), (1, 10))
        self.assertEqual(list(frame.columns), COLUMNS)
        factory.assert_called_once_with({})
        params = session.get.call_args.kwargs["params"]
        self.assertNotIn("mailto", params)
        self.assertEqual(params["query.bibliographic"], "tempeh Indonesia")
        self.assertEqual(params["rows"], 1)

    def test_crossref_cursor_and_optional_credentials(self):
        factory, session = self.session_for("crossref")
        papers = [{"DOI": f"10.1/{index}"} for index in range(100)]
        session.get.side_effect = [crossref_response(papers, 101), crossref_response([{"DOI": "10.1/last"}], 101)]
        frame, _ = crossref.search_papers("tempeh", "researcher@example.org", "test-secret", None)
        self.assertEqual(len(frame), 101)
        factory.assert_called_once_with({"Crossref-Plus-API-Token": "Bearer test-secret"})
        params = session.get.call_args.kwargs["params"]
        self.assertEqual(params["cursor"], "next")
        self.assertEqual(params["mailto"], "researcher@example.org")
        self.assertNotIn("test-secret", frame.to_csv(index=False))
        self.assertNotIn("researcher@example.org", frame.to_csv(index=False))

    def test_crossref_stalled_cursor_is_an_error(self):
        _, session = self.session_for("crossref")
        papers = [{"DOI": str(index)} for index in range(100)]
        session.get.return_value = crossref_response(papers, 200, "*")
        with self.assertRaisesRegex(ValueError, "stopped"):
            crossref.search_papers("tempeh", max_results=None)

    def test_crossref_mapping(self):
        paper = crossref.normalize_paper({
            "DOI": "10.1/a", "title": ["Title"], "container-title": ["Journal"],
            "author": [{"given": "A", "family": "B"}, {"name": "Team"}],
            "published": {"date-parts": [[2025, 3]]}, "abstract": "<jats:p>Text</jats:p>",
            "link": [{"content-type": "application/pdf", "URL": "https://example.org/a.pdf"}],
            "is-referenced-by-count": 5,
        }, "query")
        self.assertEqual(paper["publication_date"], "2025-03")
        self.assertEqual(paper["authors"], "A B; Team")
        self.assertEqual(paper["pdf_url"], "https://example.org/a.pdf")
        self.assertEqual(paper["citation_count"], 5)
        self.assertEqual(paper["journal"], "Journal")

    def test_semantic_public_access_exact_limit(self):
        factory, session = self.session_for("semantic_scholar")
        session.get.return_value = semantic_response([{"paperId": "a"}, {"paperId": "b"}], 100, "next")
        query = '(tempe | tempeh) + Indonesia'
        frame, total = semantic_scholar.search_papers(query, max_results=1)
        self.assertEqual((len(frame), total), (1, 100))
        factory.assert_called_once_with({})
        self.assertEqual(session.get.call_args.kwargs["params"]["query"], query)
        self.assertEqual(list(frame.columns), COLUMNS)

    def test_semantic_token_and_estimated_total(self):
        factory, session = self.session_for("semantic_scholar")
        session.get.side_effect = [
            semantic_response([{"paperId": "a"}], 1, "next"),
            semantic_response([{"paperId": "b"}], 10),
        ]
        frame, total = semantic_scholar.search_papers("tempeh", "test-secret", None)
        self.assertEqual((len(frame), total), (2, 10))
        factory.assert_called_once_with({"x-api-key": "test-secret"})
        self.assertEqual(session.get.call_args.kwargs["params"]["token"], "next")
        self.assertNotIn("test-secret", frame.to_csv(index=False))

    def test_semantic_token_cycle_is_an_error(self):
        _, session = self.session_for("semantic_scholar")
        session.get.side_effect = [
            semantic_response([{"paperId": "a"}], 100, "next"),
            semantic_response([{"paperId": "b"}], 100, "next"),
        ]
        with self.assertRaisesRegex(ValueError, "stopped"):
            semantic_scholar.search_papers("tempeh", max_results=None)

    def test_semantic_mapping(self):
        paper = semantic_scholar.normalize_paper({
            "paperId": "a", "corpusId": 123, "externalIds": {"DOI": "10.1/a", "PubMed": "1"},
            "authors": [{"name": "A"}, {"name": "B"}], "venue": "Venue",
            "publicationTypes": ["Review", "JournalArticle"],
            "openAccessPdf": {"url": "https://example.org/a.pdf"},
        }, "q")
        self.assertEqual(paper["pmid"], "1")
        self.assertEqual(paper["semantic_scholar_corpus_id"], 123)
        self.assertEqual(paper["authors"], "A; B")
        self.assertEqual(paper["journal"], "Venue")
        self.assertEqual(paper["publication_type"], "Review; JournalArticle")

    def test_pubmed_email_is_required_but_key_is_optional(self):
        _, session = self.session_for("pubmed")
        session.get.side_effect = [history_response(1), medline_response(["123"])]
        frame, total = pubmed.search_papers("tempeh[tiab]", "researcher@example.org")
        self.assertEqual((len(frame), total), (1, 1))
        self.assertEqual(frame.iloc[0]["pmid"], "123")
        self.assertEqual(frame.iloc[0]["publication_year"], 2025)
        self.assertEqual(frame.iloc[0]["url"], "https://pubmed.ncbi.nlm.nih.gov/123/")
        for call in session.get.call_args_list:
            self.assertNotIn("api_key", call.kwargs["params"])
            self.assertEqual(call.kwargs["params"]["email"], "researcher@example.org")

    def test_pubmed_history_batches_and_optional_key(self):
        _, session = self.session_for("pubmed")
        session.get.side_effect = [history_response(101), medline_response(map(str, range(100))), medline_response(["100"])]
        progress = Mock()
        frame, total = pubmed.search_papers("tempeh", "researcher@example.org", "test-secret", None, progress)
        self.assertEqual((len(frame), total), (101, 101))
        params = session.get.call_args.kwargs["params"]
        self.assertEqual((params["retstart"], params["retmax"]), (100, 1))
        self.assertEqual(params["api_key"], "test-secret")
        self.assertEqual(params["WebEnv"], "history")
        progress.assert_called_with(101, 101)
        self.assertNotIn("test-secret", frame.to_csv(index=False))

    def test_pubmed_cap_and_limited_broad_query(self):
        _, session = self.session_for("pubmed")
        session.get.return_value = history_response(20000)
        with self.assertRaisesRegex(ValueError, "10,000"):
            pubmed.search_papers("tempeh", "researcher@example.org", max_results=None)
        session.get.side_effect = [history_response(20000), medline_response(["123"])]
        frame, total = pubmed.search_papers("tempeh", "researcher@example.org", max_results=1)
        self.assertEqual((len(frame), total), (1, 20000))

    def test_pubmed_missing_email_rejected_before_request(self):
        _, session = self.session_for("pubmed")
        with self.assertRaisesRegex(ValueError, "contact email"):
            pubmed.search_papers("tempeh", "")
        session.get.assert_not_called()

    def test_pubmed_invalid_history_and_incomplete_fetch(self):
        _, session = self.session_for("pubmed")
        session.get.return_value = json_response({"esearchresult": {"count": "1"}})
        with self.assertRaisesRegex(ValueError, "search history"):
            pubmed.search_papers("tempeh", "researcher@example.org")
        session.get.side_effect = [history_response(2), medline_response(["123"])]
        with self.assertRaisesRegex(ValueError, "stopped"):
            pubmed.search_papers("tempeh", "researcher@example.org")

    def test_pubmed_mapping(self):
        paper = pubmed.normalize_paper({
            "PMID": "123", "TI": "Title", "AU": ["A", "B"], "DP": "2024 Jan-Feb",
            "AID": ["10.1/example [doi]"], "PT": ["Review"], "LA": ["eng"], "JT": "Journal",
        }, "q")
        self.assertEqual(paper["doi"], "10.1/example")
        self.assertEqual(paper["publication_year"], 2024)
        self.assertEqual(paper["publication_date"], "2024 Jan-Feb")
        self.assertEqual(paper["language"], "eng")

    def test_pubmed_doi_fields_accept_text_or_lists(self):
        cases = [
            ({"LID": "10.1/lid [doi]"}, "10.1/lid"),
            ({"LID": ["10.1/lid [doi]"]}, "10.1/lid"),
            ({"AID": "10.1/aid [doi]"}, "10.1/aid"),
            ({"AID": ["10.1/aid [doi]"], "LID": "10.1/lid [doi]"}, "10.1/aid"),
            ({"AID": ["article-id [pii]"], "LID": "10.1/lid [doi]"}, "10.1/lid"),
            ({"AID": None, "LID": "article-id [pii]"}, None),
            ({}, None),
        ]
        for record, expected in cases:
            with self.subTest(record=record):
                self.assertEqual(pubmed.normalize_paper(record, "q")["doi"], expected)

    def test_pubmed_retrieval_parses_real_medline_identifier_types(self):
        _, session = self.session_for("pubmed")
        fetched = Mock()
        fetched.text = (
            "PMID- 123\nTI  - Tempeh\nAID - 12345 [pii]\n"
            "LID - 10.1/example [doi]\n\n"
        )
        session.get.side_effect = [history_response(1), fetched]
        frame, total = pubmed.search_papers("tempeh", "researcher@example.org")
        self.assertEqual(total, 1)
        self.assertEqual(frame.iloc[0]["doi"], "10.1/example")
        self.assertIn("10.1/example", frame.to_csv(index=False))

    def test_all_new_providers_empty_results_keep_headers(self):
        for module, payload, kwargs in [
            (crossref, crossref_response([], 0), {}),
            (semantic_scholar, semantic_response([], 0), {}),
            (pubmed, history_response(0), {"email": "researcher@example.org"}),
        ]:
            with self.subTest(module=module.__name__):
                _, session = self.session_for(module.__name__)
                session.get.return_value = payload
                frame, total = module.search_papers("missing", **kwargs)
                self.assertEqual(total, 0)
                self.assertTrue(frame.empty)
                self.assertEqual(frame.to_csv(index=False).strip(), ",".join(COLUMNS))

    def test_new_providers_http_errors_do_not_return_partial_results(self):
        for module, payload, kwargs in [
            (crossref, crossref_response([{}] * 100, 101), {}),
            (semantic_scholar, semantic_response([{}], 2, "next"), {}),
            (pubmed, history_response(1), {"email": "researcher@example.org"}),
        ]:
            with self.subTest(module=module.__name__):
                _, session = self.session_for(module.__name__)
                session.get.side_effect = [payload, requests.Timeout()]
                with self.assertRaises(requests.Timeout):
                    module.search_papers("tempeh", max_results=None, **kwargs)

    def test_email_validation(self):
        self.assertEqual(validate_email(""), "")
        self.assertEqual(validate_email(" researcher@example.org "), "researcher@example.org")
        with self.assertRaises(ValueError):
            validate_email("invalid")


if __name__ == "__main__":
    unittest.main()
