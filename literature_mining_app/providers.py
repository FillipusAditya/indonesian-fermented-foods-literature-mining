"""Provider dispatch shared by single and sequential multi-API searches."""

import requests

import arxiv
import core
import crossref
import doaj
import europe_pmc
import openalex
import pubmed
import scopus
import semantic_scholar
import springer_nature
from common import validate_email

DATABASES = [
    "Europe PMC", "OpenAlex", "Crossref", "Semantic Scholar", "PubMed",
    "CORE", "DOAJ", "Springer Nature", "Scopus", "arXiv",
]
MULTI_DATABASES = [
    "Europe PMC", "OpenAlex", "Semantic Scholar", "CORE", "DOAJ", "Scopus", "PubMed", "arXiv",
]
SEARCH_SCOPES = {
    "Europe PMC": "Indexed metadata and available full text",
    "OpenAlex": "Titles, abstracts, full text, and keywords; stemming applies",
    "Semantic Scholar": "Titles and abstracts; stemming applies",
    "CORE": "CORE's indexed work search fields",
    "DOAJ": "Indexed article metadata",
    "Scopus": "Titles, abstracts, and keywords",
    "PubMed": "PubMed default search; Automatic Term Mapping may apply",
    "arXiv": "All searchable arXiv metadata fields",
}


def validate_credentials(database: str, credentials: dict) -> None:
    if database in ("PubMed", "Crossref"):
        validate_email(credentials.get("email", ""), required=database == "PubMed")
    if database in ("Scopus", "Springer Nature") and not credentials.get("api_key", "").strip():
        raise ValueError(f"Enter your {database} API key before starting the search.")


def search(database, query, credentials, max_results, on_progress):
    """Keep provider-specific call signatures and credentials in one place."""
    key = credentials.get("api_key", "")
    email = credentials.get("email", "")
    if database == "Europe PMC":
        return europe_pmc.search_papers(query, max_results, on_progress)
    if database == "OpenAlex":
        return openalex.search_papers(query, key, max_results, on_progress)
    if database == "Crossref":
        return crossref.search_papers(query, email, key, max_results, on_progress)
    if database == "Semantic Scholar":
        return semantic_scholar.search_papers(query, key, max_results, on_progress)
    if database == "PubMed":
        return pubmed.search_papers(query, email, key, max_results, on_progress)
    if database == "CORE":
        return core.search_papers(query, key, max_results, on_progress)
    if database == "DOAJ":
        return doaj.search_papers(query, max_results, on_progress)
    if database == "Springer Nature":
        return springer_nature.search_papers(query, key, max_results, on_progress)
    if database == "Scopus":
        return scopus.search_papers(
            query, key, max_results, on_progress,
            inst_token=credentials.get("inst_token", ""),
            use_cursor=credentials.get("use_cursor", False),
        )
    if database == "arXiv":
        return arxiv.search_papers(query, max_results, on_progress)
    raise ValueError("Unsupported literature database.")


def error_message(database: str, exc: Exception) -> str:
    """Describe failures without exposing request URLs or credentials."""
    if isinstance(exc, requests.Timeout):
        return f"{database} took too long to respond. Try again or narrow your query."
    if isinstance(exc, requests.HTTPError):
        code = exc.response.status_code if exc.response is not None else None
        if code in (401, 403):
            return f"{database} rejected the API key or access is restricted. Check your key and account access."
        if code in (400, 422):
            return f"{database} rejected the request. Check your query syntax, query length, and credentials."
        if code in (402, 429):
            return f"{database} usage or rate limit reached. Check your API allowance and try again later."
        return f"{database} could not process the request. Please try again."
    if isinstance(exc, requests.exceptions.RetryError):
        return f"{database} remained unavailable or rate limited after retries. Please try again later."
    if isinstance(exc, requests.RequestException):
        return f"Could not connect to {database}. Check your connection and try again."
    if isinstance(exc, ValueError):
        return str(exc)
    return f"{database} could not process its results. No partial data from this source was exported."
