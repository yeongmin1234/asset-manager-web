import unittest

from app.services.product_match_service import (
    FUZZY_MATCH_THRESHOLD,
    MAX_FUZZY_CANDIDATES,
    SHORT_QUERY_THRESHOLD,
    normalize_product_text,
    prepare_product_search_fields,
    rank_product_matches,
)


def products(*rows):
    result = []
    for code, name, size in rows:
        item = {"item_code": code, "item_name": name, "size": size, "unit": "EA"}
        item["_search"] = prepare_product_search_fields(item)
        result.append(item)
    return result


class ProductMatchServiceTest(unittest.TestCase):
    def setUp(self):
        self.items = products(
            ("101006", "랜턴블랙", "기본"),
            ("101007", "뉴랜턴블랙", "신형"),
            ("101008", "랜턴블랙L", "L"),
            ("201001", "토스터화이트", "기본"),
            ("201002", "뉴토스터화이트", "신형"),
        )

    def test_normalization_preserves_code_delimiters_and_options(self):
        self.assertEqual(normalize_product_text("  랜턴  블랙 "), "랜턴 블랙")
        self.assertEqual(normalize_product_text("101011-L/XL"), "101011-l/xl")
        self.assertEqual(normalize_product_text("랜턴 블랙", compact=True), "랜턴블랙")

    def test_required_search_priority(self):
        cases = {
            "101006": "exact_code", "랜턴블랙": "exact_name",
            "랜턴 블랙": "space_normalized", "랜턴블": "prefix", "턴블랙": "partial",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(rank_product_matches(self.items, query)["match_type"], expected)

    def test_one_and_two_character_typos_and_aliases(self):
        one = rank_product_matches(self.items, "랜턴블렉")
        self.assertEqual(one["match_type"], "fuzzy")
        self.assertEqual(one["items"][0]["item_name"], "랜턴블랙")
        alias = rank_product_matches(self.items, "토스타화이트")
        self.assertEqual(alias["match_type"], "fuzzy")
        self.assertEqual(alias["items"][0]["item_name"], "토스터화이트")
        duplicate = rank_product_matches(self.items, "토스터화이이트")
        self.assertEqual(duplicate["match_type"], "fuzzy")

    def test_short_query_threshold_prevents_false_positive(self):
        self.assertGreater(SHORT_QUERY_THRESHOLD, FUZZY_MATCH_THRESHOLD)
        self.assertEqual(rank_product_matches(self.items, "램프")["items"], [])

    def test_no_match_and_maximum_limit(self):
        self.assertEqual(rank_product_matches(self.items, "완전히다른검색어")["match_type"], "none")
        many = products(*[(str(index), "랜턴블랙{}".format(index), "") for index in range(20)])
        self.assertLessEqual(len(rank_product_matches(many, "랜턴블랙오타")["items"]), MAX_FUZZY_CANDIDATES)

    def test_sort_tie_uses_short_name_then_code(self):
        tied = products(("B", "토스터화이트L", ""), ("A", "토스터화이트", ""))
        result = rank_product_matches(tied, "토스타화이트")["items"]
        self.assertEqual(result[0]["item_code"], "A")

    def test_partial_code_is_candidate_but_code_typo_is_not_corrected(self):
        partial = rank_product_matches(self.items, "1010")
        self.assertEqual(partial["match_type"], "code_prefix")
        self.assertGreater(len(partial["items"]), 1)
        self.assertEqual(rank_product_matches(self.items, "191006")["items"], [])


if __name__ == "__main__":
    unittest.main()
