"""Small helpers shared by literature API clients."""

import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_session(headers: dict | None = None) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"], respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "IndonesiaFermentedFoodsMining/1.0"})
    if headers:
        session.headers.update(headers)
    return session


def validate_query(query: str, max_results: int | None) -> str:
    query = query.strip()
    if not query:
        raise ValueError("Query cannot be empty.")
    if max_results is not None and max_results < 1:
        raise ValueError("The article limit must be at least 1.")
    return query


def validate_email(email: str, required: bool = False) -> str:
    email = email.strip()
    if not email and required:
        raise ValueError("Enter a contact email address for PubMed requests.")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter a valid contact email address.")
    return email


def as_list(value) -> list:
    """Handle metadata fields that may contain one value or multiple values."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def integer_or_none(value) -> int | None:
    text = "" if value is None else str(value)
    return int(text) if text.isdigit() else None


def boolean_or_none(value) -> bool | None:
    return {"true": True, "false": False, "1": True, "0": False}.get(str(value).lower())
