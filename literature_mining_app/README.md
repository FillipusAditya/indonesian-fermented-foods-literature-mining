# Literature Mining App

A simple, responsive Streamlit app for Europe PMC, OpenAlex, Crossref,
Semantic Scholar, PubMed, CORE, DOAJ, Springer Nature, Scopus, and arXiv, based on
`notebooks/literature_mining_api_exploration.ipynb`.
The interface, query guides, and error messages are in English.

## Search modes

**Single Database** keeps the native-query workflow for all ten providers.
**Multiple Databases** uses a visual Boolean builder for Europe PMC, OpenAlex,
Semantic Scholar, CORE, DOAJ, Scopus, PubMed, and arXiv. Crossref and Springer
Nature remain in Single Database mode. No LLM is used.

In Multiple Databases mode:

1. Check the databases to search. Credentials appear only for selected sources.
2. Add concept groups and terms. Choose AND/OR within each group, and AND/OR
   between included groups. Enable **Exact phrase** for multiword entries.
3. Mark a group as **Exclude group** to subtract it from the entire included
   expression. At least one included group is required. All exclusions apply
   to the combined included expression, irrespective of the AND/OR selector.
4. Inspect the read-only standard query and native query previews.
5. Complete required credentials and choose an article limit **per API**, or
   **All results**. The limit field disables immediately for All results.
6. Click **Search selected databases**. Sources run sequentially in the fixed
   order displayed above, with overall progress, current-source progress,
   and a Waiting/Running/Completed/Limited/Failed status table.
7. Review the per-source results and download one **combined CSV**.

The builder creates an expression tree; source-specific compilers render its
Boolean structure without string substitution or rewriting user concepts.
Terms cannot contain native field tags, wildcard operators, quotes, or
parentheses. Periods, apostrophes, underscores, and hyphens are treated as
literal punctuation and quoted during compilation. Use the phrase checkbox
instead of typing quote characters. This first version supports one level
of concept groups, not arbitrary nested groups or proximity operators.

Native search scopes are shown with the translations. Scopus uses
TITLE-ABS-KEY, arXiv uses all:, and the other sources use their default search
scope. Indexing, stemming, Automatic Term Mapping, and phrase matching differ
between providers; preserving Boolean structure does not make their search
results equivalent. Limits from each API still apply.

All required credentials are checked before the first source starts. A failed
source does not stop the queue, but none of its partial records are exported.
Successful sources with zero results are distinguished from failures. When
all sources fail, no download is shown. Partial-source and article-limit
exports are labeled in the result summary. Changing selected databases or
search mode clears previous results. Other edits leave the last run visible
with its original query and limit, until a new search starts.

## Run

From the repository root, using Python 3.10 or newer:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r literature_mining_app/requirements.txt
.venv\Scripts\python -m streamlit run literature_mining_app/app.py
```

Open the address printed by Streamlit, usually http://localhost:8501.
On Windows, `py` can replace `python` when creating the virtual environment.
The application folder is now `literature_mining_app`.

## Credentials

| Database | Email | API key |
| --- | --- | --- |
| Europe PMC | Not needed | Not needed |
| OpenAlex | Not needed | Optional for the first page; required for subsequent cursor pages |
| Crossref | Optional, recommended for the polite pool | Optional Metadata Plus subscriber key |
| Semantic Scholar | Not needed | Optional; anonymous traffic shares capacity |
| PubMed | Required in this app to identify NCBI requests | Optional NCBI key |
| CORE | Not needed | Optional for public metadata search |
| DOAJ | Not needed | Not needed for article search |
| Springer Nature | Not needed | Required, with Meta v2 API access |
| Scopus | Not needed | Required, with Scopus entitlement; institutional token optional |
| arXiv | Not needed | Not needed |

The form changes immediately when a database is selected. Optional fields may
be left empty. Keys use password fields. Credentials are kept in the current
widget session and sent only to the selected API; they are not written to
files, CSV exports, or result metadata. Raw HTTP exception messages are not
displayed. Keys are sent in headers for OpenAlex, Crossref, Semantic Scholar,
CORE, and Scopus. NCBI and Springer Nature expect keys in request parameters.
The optional Scopus institutional token is also sent in a header.

## Use

For Single Database mode:

1. Select a database and read its query syntax guide.
2. Fill in the applicable credentials, leaving optional fields empty if desired.
3. Write the query manually. The field starts empty; the app only trims
   surrounding whitespace and does not build or translate query expressions.
4. Choose a result limit or **All results**, then click **Search literature**.
5. Wait for the spinner and progress indicator, inspect the preview, and click
   **Download CSV** to download the file.

| Database | Parameter and example |
| --- | --- |
| Europe PMC | `query`: `TITLE_ABS:(tempe OR tempeh) AND Indonesia*` |
| OpenAlex | `search`: `(tempe OR tempeh) AND Indonesia` |
| Crossref | `query.bibliographic`: `Indonesian fermented foods` |
| Semantic Scholar | bulk `query`: `(tempeh \| tempe) + Indonesia` |
| PubMed | ESearch `term`: `(tempe[tiab] OR tempeh[tiab]) AND Indonesia[tiab]` |
| CORE | `q`: `(title:tempe OR title:tempeh) AND Indonesia` |
| DOAJ | Path query: `bibjson.title:tempeh` |
| Springer Nature | `q`: `"fermented food"` |
| Scopus | `query`: `TITLE-ABS-KEY(tempe OR tempeh) AND TITLE-ABS-KEY(Indonesia)` |
| arXiv | `search_query`: `(all:tempe OR all:tempeh) AND all:Indonesia` |

Crossref uses ranked bibliographic text, without Boolean matching guarantees,
and restricts results to journal articles as in the notebook. Semantic Scholar
uses bulk search with `+`, `|`, and `-` operators; the reported total is an
estimate. OpenAlex uses standard `search`, so wildcards requiring `search.exact`
are not exposed. Other API filter parameters are not exposed in this version.

CORE supports field lookups and Boolean expressions. DOAJ supports fielded
query-string searches, but disables wildcard and regular-expression queries.
Springer Nature uses its own constraint syntax; spaces combine constraints
and quoted arguments preserve phrases. Scopus uses advanced-search field
codes. arXiv uses field prefixes with AND, OR, and ANDNOT. The page displays
provider-specific examples and links to the official query documentation.

## Pagination and export

- Single Database exports use the notebook's 22 columns, including the submitted
  query and source database. Multiple Databases exports add `standard_query` and
  `executed_query` for a total of 24 columns. The existing `query` column holds
  the executed native query. Unavailable fields remain empty.
- Combined exports preserve duplicate articles from different sources.
  Downloading or rerunning the page does not rerun searches; a new API search
  starts only when its search button is clicked. Credentials are not included
  in combined exports or source status summaries.
- Abstracts and PDF links are included only when supplied by the source.
  OpenAlex abstracts are reconstructed from the inverted index. Europe PMC
  and Crossref abstracts may contain original markup.
- Europe PMC and OpenAlex use cursors. Crossref uses a cursor and stops on a
  short page. Semantic Scholar uses continuation tokens, independent of its
  estimated count. Pages are spaced 1.1 seconds apart.
- PubMed uses ESearch history and EFetch MEDLINE batches of up to 100 records.
  Biopython parses MEDLINE without global Entrez email or key state. Requests
  are spaced 0.4 seconds apart, including the first EFetch, with or without a key.
- PubMed can retrieve at most 10,000 records per query. Broad queries can use
  a smaller explicit limit; **All results** above that cap asks you to narrow
  the query rather than silently truncate the export.
- Without an OpenAlex key, use a limit of 100 or fewer (the default for that
  provider). If further cursor pages are needed, the app asks for a key and
  does not export a partial result as a successful search.
- API failures clear the prior download. Switching databases also clears old
  results; results otherwise persist across reruns in the same session.
- CORE uses work-search offset pagination, spaced 6.2 seconds apart for
  conservative use of its public metadata tier. Account quotas still apply.
  This app does not download or export CORE full text.
- DOAJ keeps its page size fixed while paging, with at most 100 records per
  page. Its search API exposes at most 1,000 records; larger retrieval targets
  ask the user to narrow the query or select a smaller limit.
- Springer Nature uses `/meta/v2/json`, one-based `s` offsets and `p` page sizes
  up to 20. Available fields and query constraints depend on the key's plan.
- Scopus uses the STANDARD search view. Standard offset paging supports up to
  5,000 results. Enable **Use subscriber cursor pagination** for larger sets
  when entitled. An API key alone does not grant access. Abstracts and full
  author lists may be absent; these are exported only if returned by the API.
  No additional abstract/PDF requests are made.
- arXiv reads Atom metadata with the Python standard XML parser. Requests are
  spaced 3.1 seconds apart, with up to 30,000 matches per query in this app.
  Results are preprints. Journal references may be source citation strings.
  Only metadata and links are retrieved; PDFs are not downloaded.
- CSV is UTF-8 with BOM for Excel and downloads only after a click. Empty
  results can be downloaded as a header-only CSV. The preview shows at most
  100 articles, while the CSV contains all fetched records.
- Results are collected in session memory. Broad queries need more RAM and
  time, and remain subject to each API's service limits.

## Files and tests

`app.py` selects the search mode. `single_search.py` preserves native queries;
`multi_ui.py` contains the visual builder and multi-source result interface.
`boolean_query.py` defines the expression tree and native query compilers;
`multi_search.py` runs selected sources sequentially and combines results.
`providers.py` centralizes source dispatch and credential validation.
`credentials_ui.py` shares the credential widgets between modes, and `layout.py`
contains the responsive header. `query_guides.py` holds native query guidance,
`schema.py` defines CSV columns, and each database has its own client module.
`common.py` provides shared validation and HTTP retry setup.

```powershell
.venv\Scripts\python -m unittest discover -s literature_mining_app/tests -v
```

Tests cover metadata mapping, pagination, result limits, empty results,
credentials, API failures, and Streamlit interactions using mock responses.
Additional tests verify Boolean translations and grouping, literal terms,
sequential execution order, credential preflight, partial/all-source failure,
duplicate retention, provenance columns, dynamic builder controls, and result
persistence without duplicate API calls.

## Official references

- [Europe PMC search help](https://europepmc.org/help)
- [OpenAlex authentication](https://help.openalex.org/api/authentication/) and [search](https://help.openalex.org/api/searching/)
- [Crossref access](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/) and [queries](https://github.com/CrossRef/rest-api-doc#queries)
- [Semantic Scholar bulk search](https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/get_graph_get_paper_bulk_search)
- [NCBI usage guidelines](https://www.ncbi.nlm.nih.gov/books/NBK25497/), [PubMed search help](https://pubmed.ncbi.nlm.nih.gov/help/), and [NCBI disclaimer](https://www.ncbi.nlm.nih.gov/About/disclaimer.html)
- [CORE API](https://api.core.ac.uk/docs/v3)
- [DOAJ API](https://doaj.org/api/v4/docs)
- [Springer Nature Meta v2](https://dev.springernature.com/docs/api-endpoints/meta-api/) and [query constraints](https://dev.springernature.com/docs/supported-query-params/)
- [Scopus Search API](https://dev.elsevier.com/documentation/ScopusSearchAPI.wadl) and [authentication](https://dev.elsevier.com/tecdoc_api_authentication.html)
- [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html) and [terms](https://info.arxiv.org/help/api/tou.html)

Thank you to arXiv for use of its open access interoperability.
