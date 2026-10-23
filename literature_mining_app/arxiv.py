"""arXiv Atom API search without an API key."""

import time
import xml.etree.ElementTree as ET
from collections.abc import Callable

import pandas as pd

from common import create_session, integer_or_none, validate_query
from schema import COLUMNS

BASE_URL = "https://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def normalize_paper(entry: ET.Element, query: str) -> dict:
    def text(path):
        value = entry.findtext(path, default="", namespaces=NS)
        return " ".join(value.split()) or None

    date = text("atom:published")
    links = entry.findall("atom:link", NS)
    return {
        "doi": text("arxiv:doi"),
        "title": text("atom:title"),
        "authors": "; ".join(
            " ".join((author.findtext("atom:name", default="", namespaces=NS)).split())
            for author in entry.findall("atom:author", NS)
        ) or None,
        "abstract": text("atom:summary"),
        "publication_year": integer_or_none(date[:4]) if date else None,
        "publication_date": date[:10] if date else None,
        "journal": text("arxiv:journal_ref"),
        "is_open_access": True,
        "publication_type": "preprint",
        "url": next((link.get("href") for link in links if link.get("rel") == "alternate"), None) or text("atom:id"),
        "pdf_url": next((link.get("href") for link in links if link.get("type") == "application/pdf" or link.get("title") == "pdf"), None),
        "source_database": "arXiv",
        "query": query,
    }


def search_papers(
    query: str,
    max_results: int | None = 500,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, int]:
    query = validate_query(query, max_results)
    records = []
    seen_ids = set()
    with create_session() as session:
        while True:
            size = 100 if max_results is None else min(100, max_results - len(records))
            response = session.get(
                BASE_URL,
                params={"search_query": query, "start": len(records), "max_results": size,
                        "sortBy": "relevance", "sortOrder": "descending"},
                timeout=(10, 90),
            )
            response.raise_for_status()
            try:
                feed = ET.fromstring(response.content)
            except ET.ParseError as exc:
                raise ValueError("arXiv returned an invalid Atom feed. Please try again.") from exc
            entries = feed.findall("atom:entry", NS)
            if any(entry.findtext("atom:id", default="", namespaces=NS).startswith("http://arxiv.org/api/errors") for entry in entries):
                raise ValueError("arXiv rejected the query. Check its syntax or narrow the search.")
            count = feed.findtext("opensearch:totalResults", namespaces=NS)
            if count is None:
                raise ValueError("arXiv did not return a result count. Check your query syntax.")
            total = int(count)
            target = total if max_results is None else min(total, max_results)
            if target > 30000:
                raise ValueError("arXiv retrieval is limited to 30,000 results per query in this app. Narrow your query or choose a smaller limit.")
            for entry in entries[:size]:
                identifier = entry.findtext("atom:id", namespaces=NS)
                if not identifier or identifier in seen_ids:
                    raise ValueError("arXiv returned a missing or repeated record. Please try again.")
                seen_ids.add(identifier)
                records.append(normalize_paper(entry, query))
            if on_progress:
                on_progress(len(records), total)
            if len(records) >= target:
                break
            if not entries:
                raise ValueError("arXiv retrieval stopped before completion. Please try again.")
            time.sleep(3.1)
    return pd.DataFrame(records, columns=COLUMNS, dtype=object), total
