"""Provider-specific guidance for manually written search expressions."""

import streamlit as st

GUIDES = {
    "Europe PMC": {
        "description": "Search indexed metadata and available full text. Use uppercase AND, OR, NOT, double quotes for phrases, and parentheses for groups. The default operator is AND.",
        "examples": [
            ("Either term", "tempe OR tempeh"),
            ("Group concepts", "(tempe OR tempeh) AND Indonesia*"),
            ("Phrase", '"fermented food"'),
            ("Exclude a term", "fermentation NOT alcohol"),
            ("Title or abstract", "TITLE_ABS:(tempe OR tempeh)"),
            ("Title / abstract", "TITLE:tempeh / ABSTRACT:tempeh"),
            ("Publication years", "PUB_YEAR:[2020 TO 2026]"),
            ("Publication dates", "FIRST_PDATE:[2020-01-01 TO 2026-12-31]"),
            ("Open access", "OPEN_ACCESS:Y"),
        ],
        "note": "Your expression is sent to the query parameter. Use * for word endings.",
        "links": "[Query help](https://europepmc.org/help) · [REST API](https://europepmc.org/RestfulWebService)",
    },
    "OpenAlex": {
        "description": "Search titles, abstracts, full text, and keywords using the search parameter. Use uppercase AND, OR, NOT, quotes, and parentheses; the default operator is AND. Search applies stemming and removes stop words.",
        "examples": [
            ("Group concepts", "(tempe OR tempeh) AND Indonesia"),
            ("Phrase", '"fermented food" AND Indonesia'),
            ("Exclude a term", "fermentation NOT alcohol"),
        ],
        "note": "Enter only the expression, without a URL or search= prefix. Europe PMC field tags are not supported. Wildcards require search.exact, which this app does not use. Write alternatives with OR. An API key is required beyond the first cursor page; without one, use an article limit of 100 or fewer.",
        "links": "[Search help](https://help.openalex.org/api/searching/) · [Authentication](https://help.openalex.org/api/authentication/) · [Get a key](https://openalex.org/settings/api)",
    },
    "Crossref": {
        "description": "Enter plain bibliographic text. Crossref returns relevance-ranked matches rather than strict Boolean results; AND, OR, NOT, parentheses, and quoted phrases do not provide Boolean matching guarantees.",
        "examples": [
            ("Topic", "Indonesian fermented foods"),
            ("Food and compound", "tempeh polyamines"),
            ("Food and region", "tempeh Indonesia"),
        ],
        "note": "The app sends query.bibliographic and restricts results to journal articles, as in the notebook. Not every query word must occur in each result. Enter search text only; separate filter parameters are not exposed. Email is optional and recommended for the polite pool. A Metadata Plus key is optional for subscribers.",
        "links": "[Query documentation](https://github.com/CrossRef/rest-api-doc#queries) · [Access and authentication](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)",
    },
    "Semantic Scholar": {
        "description": "Bulk search matches titles and abstracts. Use the operators below rather than assuming Europe PMC or PubMed syntax. Spaces imply AND; use parentheses to group concepts.",
        "examples": [
            ("AND", "tempeh + Indonesia"),
            ("OR", "tempeh | tempe"),
            ("NOT", "fermentation -alcohol"),
            ("Phrase", '"fermented food" + Indonesia'),
            ("Group concepts", "(tempeh | tempe) + Indonesia"),
            ("Word endings", "ferment*"),
            ("Fuzzy / proximity", 'ferment~2 / "fermented food"~3'),
        ],
        "note": "The app uses /paper/search/bulk, which supports this syntax and token pagination. It does not search full text. Totals are estimates. API key is optional; anonymous requests share service capacity and may be throttled.",
        "links": "[Bulk search documentation](https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/get_graph_get_paper_bulk_search) · [Get a key](https://www.semanticscholar.org/product/api)",
    },
    "PubMed": {
        "description": "Use uppercase AND, OR, NOT and parentheses. PubMed evaluates Boolean expressions left to right. Use field tags to restrict the search and double quotes to request phrases.",
        "examples": [
            ("Title / abstract", "(tempe[tiab] OR tempeh[tiab]) AND Indonesia[tiab]"),
            ("Compounds", "tempeh[tiab] AND (polyamine*[tiab] OR GABA[tiab])"),
            ("MeSH term", '"Fermented Foods"[mh]'),
            ("Publication dates", '"2020/01/01"[dp] : "2026/12/31"[dp]'),
            ("Exclude a term", "fermentation NOT alcohol"),
        ],
        "note": "Wildcards need at least four preceding characters and disable Automatic Term Mapping. Quoted phrases depend on PubMed's phrase index. Contact email is required in this app to identify E-utilities requests; the NCBI API key is optional. Retrieve up to 10,000 articles per query; narrow the query for larger exports. Requests are spaced below three per second, with or without a key.",
        "links": "[Search help](https://pubmed.ncbi.nlm.nih.gov/help/) · [E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25499/) · [NCBI account](https://www.ncbi.nlm.nih.gov/account/) · [NCBI disclaimer](https://www.ncbi.nlm.nih.gov/About/disclaimer.html)",
    },
    "CORE": {
        "description": "Search CORE work metadata using its q parameter. Use field lookups, uppercase Boolean operators, quoted phrases, and parentheses for grouped concepts.",
        "examples": [
            ("Title", 'title:"tempeh"'),
            ("Alternative titles", '(title:tempe OR title:tempeh)'),
            ("Abstract", 'abstract:"fermented food"'),
            ("Combine concepts", '(title:tempe OR title:tempeh) AND Indonesia'),
        ],
        "note": "API key is optional for public metadata searches. The app exports metadata and available abstracts, without downloading full text. CORE applies account-specific token allowances; broad queries may exhaust them. Requests are conservatively spaced about six seconds apart.",
        "links": "[API documentation](https://api.core.ac.uk/docs/v3) · [Get a key](https://core.ac.uk/services/api)",
    },
    "DOAJ": {
        "description": "Search open-access article metadata using the DOAJ query-string syntax. Use uppercase AND, OR, NOT, quotes for phrases, parentheses, and field names such as bibjson.title or bibjson.abstract.",
        "examples": [
            ("Title", 'bibjson.title:tempeh'),
            ("Abstract phrase", 'bibjson.abstract:"fermented food"'),
            ("Alternative titles", '(bibjson.title:tempe OR bibjson.title:tempeh)'),
            ("Year range", 'bibjson.year:[2020 TO 2026]'),
        ],
        "note": "No API key or email is needed for public searches. Wildcards and regular expressions are disabled by DOAJ. Search retrieval is capped at 1,000 records; narrow the query or set a limit of 1,000 or fewer. Use DOAJ's separate data dump for larger harvesting tasks.",
        "links": "[API documentation](https://doaj.org/api/v4/docs) · [Public data dump](https://doaj.org/docs/public-data-dump/)",
    },
    "Springer Nature": {
        "description": "Search the Meta v2 API using a manually written q expression. Plain words search across available fields. Spaces combine constraints; quote multiword arguments. Supported constraints depend on the API plan.",
        "examples": [
            ("Plain words", 'tempeh fermentation'),
            ("Phrase", '"fermented food"'),
            ("Tagged keyword", 'keyword:fermentation'),
            ("Online publication dates", 'fermentation onlinedatefrom:2020-01-01 onlinedateto:2026-12-31'),
        ],
        "note": "A Meta API key is required. The app uses /meta/v2/json, not the Full Text API. Title, abstract, and other metadata are exported when returned by your access plan. Do not assume Europe PMC, Scopus, or PubMed field syntax applies.",
        "links": "[Meta v2 documentation](https://dev.springernature.com/docs/api-endpoints/meta-api/) · [Query constraints](https://dev.springernature.com/docs/supported-query-params/) · [Developer portal](https://dev.springernature.com/)",
    },
    "Scopus": {
        "description": "Use Scopus advanced-search expressions with field codes, uppercase AND, OR, AND NOT, parentheses, and quoted phrases. The expression is sent to the Scopus Search query parameter.",
        "examples": [
            ("Title, abstract, keywords", 'TITLE-ABS-KEY(tempeh)'),
            ("Combine concepts", 'TITLE-ABS-KEY(tempe OR tempeh) AND TITLE-ABS-KEY(Indonesia)'),
            ("Phrase", 'TITLE-ABS-KEY("fermented food")'),
            ("Publication years", 'TITLE-ABS-KEY(tempeh) AND PUBYEAR > 2019'),
            ("Exclude a term", 'TITLE-ABS-KEY(fermentation) AND NOT TITLE-ABS-KEY(alcohol)'),
        ],
        "note": "An Elsevier API key and appropriate Scopus entitlement are required. An institutional token is optional when supplied by Elsevier. Standard paging supports up to 5,000 results; subscriber cursor pagination can retrieve larger sets when entitled. The app uses the STANDARD metadata view: abstracts and full author lists may be unavailable, and PDF files are not retrieved.",
        "links": "[Search API](https://dev.elsevier.com/documentation/ScopusSearchAPI.wadl) · [Search syntax](https://dev.elsevier.com/tips/ScopusSearchTips.htm) · [Authentication](https://dev.elsevier.com/tecdoc_api_authentication.html)",
    },
    "arXiv": {
        "description": "Search arXiv preprint metadata with search_query. Use field prefixes such as all:, ti: (title), abs: (abstract), au: (author), or cat: (category). Boolean operators are AND, OR, and ANDNOT.",
        "examples": [
            ("All fields", 'all:tempeh'),
            ("Title or abstract", 'ti:fermentation OR abs:fermentation'),
            ("Phrase", 'all:"fermented food"'),
            ("Combine concepts", '(all:tempe OR all:tempeh) AND all:Indonesia'),
            ("Exclude a term", 'all:fermentation ANDNOT all:alcohol'),
        ],
        "note": "No API key or email is needed. Results are preprints and should be assessed accordingly. The app retrieves Atom metadata and abstract/PDF links, without downloading PDFs. Requests are spaced at least three seconds apart. Up to 30,000 results per query are supported in this app; narrow larger searches.",
        "links": "[API manual](https://info.arxiv.org/help/api/user-manual.html) · [API terms](https://info.arxiv.org/help/api/tou.html)",
    },
}


def show_query_guide(database: str) -> None:
    guide = GUIDES[database]
    with st.expander(f"{database} query syntax guide"):
        st.write(guide["description"])
        rows = ["| Purpose | Example query |", "| --- | --- |"]
        for purpose, example in guide["examples"]:
            # Escape the Semantic Scholar OR operator inside Markdown tables.
            example = example.replace("|", "\\|")
            rows.append(f"| {purpose} | `{example}` |")
        st.markdown("\n".join(rows))
        st.info(guide["note"])
        st.markdown(guide["links"])
