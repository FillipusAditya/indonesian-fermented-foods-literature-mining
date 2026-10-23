"""Reference translations and validation for the visual query model."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from boolean_query import build_expression, compile_query
from providers import MULTI_DATABASES


def group(*terms, operator="OR", exclude=False):
    return {"terms": [{"text": term, "phrase": " " in term} for term in terms],
            "operator": operator, "exclude": exclude}


class BooleanQueryTests(unittest.TestCase):
    def test_reference_translation_preserves_grouping(self):
        node = build_expression([group("tempe", "tempeh"), group("GABA", "gamma aminobutyric acid")])
        reference = '((tempe OR tempeh) AND (GABA OR "gamma aminobutyric acid"))'
        for database in ["Standard", "Europe PMC", "OpenAlex", "CORE", "DOAJ", "PubMed"]:
            with self.subTest(database=database):
                self.assertEqual(compile_query(node, database), reference)
        self.assertEqual(compile_query(node, "Semantic Scholar"), '((tempe | tempeh) + (GABA | "gamma aminobutyric acid"))')
        self.assertEqual(compile_query(node, "arXiv"), '((all:tempe OR all:tempeh) AND (all:GABA OR all:"gamma aminobutyric acid"))')
        self.assertEqual(compile_query(node, "Scopus"), '((TITLE-ABS-KEY(tempe) OR TITLE-ABS-KEY(tempeh)) AND (TITLE-ABS-KEY(GABA) OR TITLE-ABS-KEY("gamma aminobutyric acid")))')

    def test_exclusion_applies_to_the_entire_included_expression(self):
        node = build_expression([group("tempe"), group("tempeh"), group("biofuel", "wine", exclude=True)], combine="OR")
        self.assertEqual(compile_query(node), '((tempe OR tempeh) AND NOT (biofuel OR wine))')
        self.assertEqual(compile_query(node, "PubMed"), '((tempe OR tempeh) NOT (biofuel OR wine))')
        self.assertEqual(compile_query(node, "Semantic Scholar"), '((tempe | tempeh) + -((biofuel | wine)))')
        self.assertEqual(compile_query(node, "arXiv"), '((all:tempe OR all:tempeh) ANDNOT (all:biofuel OR all:wine))')

    def test_multiple_exclusions_and_within_group_and(self):
        node = build_expression([group("tempeh", "Indonesia", operator="AND"), group("biofuel", exclude=True), group("wine", exclude=True)])
        self.assertEqual(compile_query(node), '(((tempeh AND Indonesia) AND NOT biofuel) AND NOT wine)')

    def test_terms_are_literals_and_punctuation_is_quoted(self):
        node = build_expression([group("gadB", "gamma-aminobutyric")])
        self.assertEqual(compile_query(node, "Semantic Scholar"), '(gadB | "gamma-aminobutyric")')
        node = build_expression([group("L. plantarum")])
        self.assertEqual(compile_query(node, "arXiv"), 'all:"L. plantarum"')

    def test_unsafe_native_syntax_is_rejected_before_conversion(self):
        for text in ["TITLE:tempeh", "tempe*", "a OR b", "(tempe)", '"tempe"', "tempe | tempeh", "a+b", "", "---"]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    build_expression([{"terms": [{"text": text, "phrase": False}]}])

    def test_explicit_phrases_and_no_pure_negative_searches(self):
        with self.assertRaisesRegex(ValueError, "Exact phrase"):
            build_expression([{"terms": [{"text": "fermented food", "phrase": False}]}])
        with self.assertRaisesRegex(ValueError, "included group"):
            build_expression([group("biofuel", exclude=True)])
        with self.assertRaises(ValueError):
            build_expression([group("tempeh")], combine="XOR")

    def test_unsupported_sources_are_not_silently_rewritten(self):
        node = build_expression([group("tempeh")])
        self.assertEqual(len(MULTI_DATABASES), 8)
        for database in ["Crossref", "Springer Nature"]:
            with self.assertRaisesRegex(ValueError, "not supported"):
                compile_query(node, database)


if __name__ == "__main__":
    unittest.main()
