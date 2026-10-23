"""Build a Boolean expression tree and compile it to native search syntax."""

from dataclasses import dataclass

from providers import MULTI_DATABASES


@dataclass(frozen=True)
class Term:
    text: str
    phrase: bool = False


@dataclass(frozen=True)
class Junction:
    operator: str
    children: tuple


@dataclass(frozen=True)
class Exclude:
    included: object
    excluded: object


def make_term(text: str, phrase: bool = False) -> Term:
    text = " ".join(text.split())
    if not text:
        raise ValueError("Each term needs a value. Remove unused terms or fill them in.")
    # Native field tags, operators and wildcards must never be injected as terms.
    if any(not (character.isalnum() or character in " -_'.") for character in text):
        raise ValueError("Use words, numbers, spaces, hyphens, periods, underscores, or apostrophes in terms. Field tags, quotes, operators, and wildcards are not supported in the builder.")
    if not any(character.isalnum() for character in text):
        raise ValueError("A term must contain a word or number.")
    if not phrase and (" " in text or text.upper() in ("AND", "OR", "NOT", "ANDNOT")):
        raise ValueError("Enable Exact phrase for multiword terms or literal operator words, or enter separate terms.")
    return Term(text, phrase)


def join(operator: str, children: list):
    if operator not in ("AND", "OR"):
        raise ValueError("Groups can only be combined with AND or OR.")
    if not children:
        raise ValueError("Add at least one term to each group.")
    return children[0] if len(children) == 1 else Junction(operator, tuple(children))


def build_expression(groups: list[dict], combine: str = "AND"):
    included, excluded = [], []
    for group in groups:
        terms = [make_term(item["text"], item.get("phrase", False)) for item in group["terms"]]
        node = join(group.get("operator", "OR"), terms)
        (excluded if group.get("exclude", False) else included).append(node)
    if not included:
        raise ValueError("Add at least one included group. A search cannot contain exclusions only.")
    node = join(combine, included)
    for exclusion in excluded:
        node = Exclude(node, exclusion)
    return node


def compile_query(node, database: str = "Standard") -> str:
    if database != "Standard" and database not in MULTI_DATABASES:
        raise ValueError("This database is not supported in standard Boolean mode.")

    def render(current):
        if isinstance(current, Term):
            quoted = current.phrase or any(not char.isalnum() for char in current.text)
            value = f'"{current.text}"' if quoted else current.text
            if database == "arXiv":
                return f"all:{value}"
            if database == "Scopus":
                return f"TITLE-ABS-KEY({value})"
            return value
        if isinstance(current, Junction):
            operator = current.operator
            if database == "Semantic Scholar":
                operator = "+" if operator == "AND" else "|"
            return "(" + f" {operator} ".join(render(child) for child in current.children) + ")"
        if isinstance(current, Exclude):
            left, right = render(current.included), render(current.excluded)
            if database == "Semantic Scholar":
                return f"({left} + -({right}))"
            operator = {"arXiv": "ANDNOT", "Scopus": "AND NOT", "Standard": "AND NOT"}.get(database, "NOT")
            return f"({left} {operator} {right})"
        raise ValueError("Unsupported Boolean expression.")

    return render(node)
