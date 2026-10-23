"""Offline checks for CORE, DOAJ, Springer Nature, Scopus, and arXiv."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import arxiv
import core
import doaj
import scopus
import springer_nature
from schema import COLUMNS


def json_response(data):
    response = Mock()
    response.json.return_value = data
    return response


def springer_response(papers, total):
    return json_response({"records": papers, "result": [{"total": str(total)}]})


def scopus_response(papers, total, cursor=None):
    return json_response({"search-results": {
        "entry": papers, "opensearch:totalResults": str(total), "cursor": {"@next": cursor},
    }})


def atom_response(ids, total, error=False):
    entries = []
    for identifier in ids:
        url = "http://arxiv.org/api/errors#incorrect_query" if error else f"https://arxiv.org/abs/{identifier}"
        entries.append(f"""<entry><id>{url}</id><title>Title\n test</title>
        <summary>Abstract text</summary><published>2025-01-02T00:00:00Z</published>
        <author><name>A Author</name></author><arxiv:doi>10.1/example</arxiv:doi>
        <link rel="alternate" href="{url}"/>
        <link title="pdf" type="application/pdf" href="https://arxiv.org/pdf/{identifier}"/>
        </entry>""")
    response = Mock()
    response.content = (
        '<feed xmlns="http://www.w3.org/2005/Atom" '
        'xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" '
        'xmlns:arxiv="http://arxiv.org/schemas/atom">'
        f'<opensearch:totalResults>{total}</opensearch:totalResults>'
        + "".join(entries) + '</feed>'
    ).encode("utf-8")
    return response


class AdditionalProviderTests(unittest.TestCase):
    def session_for(self, module):
        session_patch = patch(f"{module}.create_session")
        factory = session_patch.start()
        self.addCleanup(session_patch.stop)
        sleep_patch = patch(f"{module}.time.sleep")
        sleep = sleep_patch.start()
        self.addCleanup(sleep_patch.stop)
        return factory, factory.return_value.__enter__.return_value, sleep

    def test_core_public_and_authenticated_search(self):
        factory, session, _ = self.session_for("core")
        session.get.return_value = json_response({"totalHits": 50, "results": [{"id": 1}]})
        query = 'title:"tempeh"'
        frame, total = core.search_papers(query, max_results=1)
        self.assertEqual((len(frame), total), (1, 50))
        factory.assert_called_with({})
        self.assertEqual(session.get.call_args.kwargs["params"]["q"], query)
        core.search_papers(query, "test-secret", 1)
        factory.assert_called_with({"Authorization": "Bearer test-secret"})
        self.assertNotIn("test-secret", frame.to_csv(index=False))

    def test_core_offset_uses_actual_page_length_and_supports_snake_case(self):
        _, session, sleep = self.session_for("core")
        session.get.side_effect = [
            json_response({"total_hits": 2, "results": [{"id": 1}]}),
            json_response({"total_hits": 2, "results": [{"id": 2}]}),
        ]
        frame, _ = core.search_papers("tempeh", max_results=None)
        self.assertEqual(len(frame), 2)
        self.assertEqual(session.get.call_args.kwargs["params"]["offset"], 1)
        sleep.assert_called_with(6.2)

    def test_core_repeated_results_are_rejected(self):
        _, session, _ = self.session_for("core")
        session.get.return_value = json_response({"totalHits": 3, "results": [{"id": 1}]})
        with self.assertRaisesRegex(ValueError, "repeated"):
            core.search_papers("tempeh", max_results=None)

    def test_core_metadata_mapping(self):
        paper = core.normalize_paper({
            "id": 1, "authors": [{"name": "A"}, "B"], "yearPublished": 2024,
            "language": {"code": "en"}, "journals": [{"title": "Journal"}],
            "downloadUrl": "https://example.org/a.pdf", "citationCount": 0,
        }, "q")
        self.assertEqual(paper["authors"], "A; B")
        self.assertEqual(paper["language"], "en")
        self.assertEqual(paper["pdf_url"], "https://example.org/a.pdf")
        self.assertEqual(paper["citation_count"], 0)

    def test_doaj_pagination_keeps_page_size_and_encodes_query(self):
        _, session, _ = self.session_for("doaj")
        session.get.side_effect = [
            json_response({"total": 200, "page": 1, "results": [{"id": str(i)} for i in range(100)]}),
            json_response({"total": 200, "page": 2, "results": [{"id": str(i)} for i in range(100, 200)]}),
        ]
        frame, total = doaj.search_papers('bibjson.title:"fermented food"', 150)
        self.assertEqual((len(frame), total), (150, 200))
        params = session.get.call_args.kwargs["params"]
        self.assertEqual(params, {"page": 2, "pageSize": 100})
        self.assertIn('%22fermented%20food%22', session.get.call_args.args[0])

    def test_doaj_all_results_cap_and_smaller_limit(self):
        _, session, _ = self.session_for("doaj")
        session.get.return_value = json_response({"total": 1001, "results": [{"id": "a"}]})
        with self.assertRaisesRegex(ValueError, "1,000"):
            doaj.search_papers("fermentation", None)
        frame, total = doaj.search_papers("fermentation", 1)
        self.assertEqual((len(frame), total), (1, 1001))

    def test_doaj_doi_selection_and_available_links(self):
        paper = doaj.normalize_paper({"id": "abc", "bibjson": {
            "title": "Title", "year": "2024", "month": "6", "author": [{"name": "A"}],
            "identifier": [{"type": "issn", "id": "1234"}, {"type": "doi", "id": "10.1/a"}],
            "journal": {"title": "Journal", "language": ["en", "id"]},
            "link": [{"url": "https://example.org/a.pdf", "type": "fulltext", "content_type": "application/pdf"}],
        }}, "q")
        self.assertEqual(paper["doi"], "10.1/a")
        self.assertEqual(paper["publication_date"], "2024-06")
        self.assertEqual(paper["language"], "en; id")
        self.assertTrue(paper["is_open_access"])
        self.assertEqual(paper["pdf_url"], paper["url"])

    def test_springer_required_key_and_one_based_paging(self):
        _, session, _ = self.session_for("springer_nature")
        with self.assertRaisesRegex(ValueError, "API key"):
            springer_nature.search_papers("fermentation", "")
        session.get.assert_not_called()
        session.get.side_effect = [springer_response([{"doi": "10.1/a"}], 2), springer_response([{"doi": "10.1/b"}], 2)]
        frame, total = springer_nature.search_papers('keyword:fermentation', "test-secret", None)
        self.assertEqual((len(frame), total), (2, 2))
        calls = session.get.call_args_list
        self.assertEqual([call.kwargs["params"]["s"] for call in calls], [1, 2])
        self.assertEqual(calls[0].kwargs["params"]["q"], "keyword:fermentation")
        self.assertNotIn("test-secret", frame.to_csv(index=False))

    def test_springer_metadata_mapping(self):
        paper = springer_nature.normalize_paper({
            "doi": "10.1/a", "publicationDate": "2024-01-02", "openaccess": "false",
            "creators": [{"creator": "A"}], "publicationName": "Journal",
            "abstract": "Abstract", "url": [{"format": "html", "value": "https://example.org/a"}],
        }, "q")
        self.assertEqual(paper["authors"], "A")
        self.assertFalse(paper["is_open_access"])
        self.assertEqual(paper["publication_year"], 2024)
        self.assertEqual(paper["url"], "https://example.org/a")

    def test_scopus_required_key_and_optional_institutional_token(self):
        factory, session, _ = self.session_for("scopus")
        with self.assertRaisesRegex(ValueError, "API key"):
            scopus.search_papers("TITLE-ABS-KEY(tempeh)", "")
        session.get.assert_not_called()
        session.get.return_value = scopus_response([{"dc:title": "Title"}], 1)
        frame, _ = scopus.search_papers("TITLE-ABS-KEY(tempeh)", "key", inst_token="token")
        factory.assert_called_with({"X-ELS-APIKey": "key", "Accept": "application/json", "X-ELS-Insttoken": "token"})
        self.assertNotIn("apiKey", session.get.call_args.kwargs["params"])
        self.assertNotIn("token", frame.to_csv(index=False))

    def test_scopus_standard_paging_and_cap(self):
        _, session, _ = self.session_for("scopus")
        session.get.side_effect = [scopus_response([{"dc:title": "A"}], 2), scopus_response([{"dc:title": "B"}], 2)]
        frame, _ = scopus.search_papers("q", "key", None)
        self.assertEqual(len(frame), 2)
        self.assertEqual(session.get.call_args.kwargs["params"]["start"], 1)
        session.get.side_effect = None
        session.get.return_value = scopus_response([{}], 5001)
        with self.assertRaisesRegex(ValueError, "5,000"):
            scopus.search_papers("q", "key", None)

    def test_scopus_cursor_paging(self):
        _, session, _ = self.session_for("scopus")
        session.get.side_effect = [scopus_response([{"dc:title": "A"}], 2, "next"), scopus_response([{"dc:title": "B"}], 2)]
        frame, _ = scopus.search_papers("q", "key", None, use_cursor=True)
        self.assertEqual(len(frame), 2)
        self.assertEqual(session.get.call_args.kwargs["params"]["cursor"], "next")
        self.assertNotIn("start", session.get.call_args.kwargs["params"])

    def test_scopus_empty_sentinel_and_stalled_cursor(self):
        _, session, _ = self.session_for("scopus")
        session.get.return_value = scopus_response([{"error": "No results"}], 0)
        frame, _ = scopus.search_papers("q", "key")
        self.assertTrue(frame.empty)
        session.get.return_value = scopus_response([{"dc:title": "A"}], 2, "*")
        with self.assertRaisesRegex(ValueError, "stopped"):
            scopus.search_papers("q", "key", None, use_cursor=True)

    def test_scopus_metadata_mapping(self):
        paper = scopus.normalize_paper({
            "prism:doi": "10.1/a", "dc:creator": "A", "prism:coverDate": "2024-01-01",
            "citedby-count": 0, "openaccess": "0", "prism:publicationName": "Journal",
            "link": [{"@ref": "scopus", "@href": "https://www.scopus.com/record/1"}],
        }, "q")
        self.assertEqual(paper["authors"], "A")
        self.assertEqual(paper["citation_count"], 0)
        self.assertFalse(paper["is_open_access"])
        self.assertEqual(paper["url"], "https://www.scopus.com/record/1")

    def test_arxiv_atom_pagination_and_pacing(self):
        factory, session, sleep = self.session_for("arxiv")
        session.get.side_effect = [atom_response(["1"], 2), atom_response(["2"], 2)]
        query = 'all:"fermented food"'
        frame, total = arxiv.search_papers(query, None)
        self.assertEqual((len(frame), total), (2, 2))
        factory.assert_called_with()
        self.assertEqual(session.get.call_args.kwargs["params"]["start"], 1)
        self.assertEqual(session.get.call_args.kwargs["params"]["search_query"], query)
        sleep.assert_called_with(3.1)

    def test_arxiv_mapping(self):
        feed = ET.fromstring(atom_response(["1"], 1).content)
        paper = arxiv.normalize_paper(feed.find("atom:entry", arxiv.NS), "q")
        self.assertEqual(paper["title"], "Title test")
        self.assertEqual(paper["doi"], "10.1/example")
        self.assertEqual(paper["publication_date"], "2025-01-02")
        self.assertEqual(paper["authors"], "A Author")
        self.assertEqual(paper["pdf_url"], "https://arxiv.org/pdf/1")

    def test_arxiv_bad_feed_error_entry_cap_and_repeated_id(self):
        _, session, _ = self.session_for("arxiv")
        bad = Mock(content=b"not XML")
        for response, message in [
            (bad, "invalid Atom"), (atom_response(["error"], 1, error=True), "rejected"),
            (atom_response(["1"], 30001), "30,000"),
        ]:
            with self.subTest(message=message):
                session.get.return_value = response
                with self.assertRaisesRegex(ValueError, message):
                    arxiv.search_papers("q", None)
        session.get.side_effect = [atom_response(["1"], 2), atom_response(["1"], 2)]
        with self.assertRaisesRegex(ValueError, "repeated"):
            arxiv.search_papers("q", None)

    def test_all_five_empty_results_preserve_schema(self):
        cases = [
            (core, json_response({"totalHits": 0, "results": []}), {}),
            (doaj, json_response({"total": 0, "results": []}), {}),
            (springer_nature, springer_response([], 0), {"api_key": "key"}),
            (scopus, scopus_response([], 0), {"api_key": "key"}),
            (arxiv, atom_response([], 0), {}),
        ]
        for module, response, kwargs in cases:
            with self.subTest(provider=module.__name__):
                _, session, _ = self.session_for(module.__name__)
                session.get.return_value = response
                frame, total = module.search_papers("missing", **kwargs)
                self.assertEqual(total, 0)
                self.assertEqual(frame.to_csv(index=False).strip(), ",".join(COLUMNS))

    def test_all_five_failures_do_not_return_partial_results(self):
        cases = [
            (core, json_response({"totalHits": 2, "results": [{"id": 1}]}), {}),
            (doaj, json_response({"total": 2, "results": [{"id": "1"}]}), {}),
            (springer_nature, springer_response([{}], 2), {"api_key": "key"}),
            (scopus, scopus_response([{}], 2), {"api_key": "key"}),
            (arxiv, atom_response(["1"], 2), {}),
        ]
        for module, response, kwargs in cases:
            with self.subTest(provider=module.__name__):
                _, session, _ = self.session_for(module.__name__)
                session.get.side_effect = [response, requests.Timeout()]
                with self.assertRaises(requests.Timeout):
                    module.search_papers("q", max_results=None, **kwargs)


if __name__ == "__main__":
    unittest.main()
