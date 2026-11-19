import unittest

from gate import lexical


class StemTest(unittest.TestCase):
    def test_inflections_agree(self):
        self.assertEqual(lexical.tokens("upgrade"), lexical.tokens("upgraded"))
        self.assertEqual(lexical.tokens("change"), lexical.tokens("changes"))
        self.assertEqual(lexical.tokens("release"), lexical.tokens("released"))
        self.assertEqual(lexical.tokens("notes"), lexical.tokens("note"))

    def test_stopwords_dropped(self):
        self.assertEqual(lexical.tokens("the a of it"), [])

    def test_short_words_dropped(self):
        self.assertEqual(lexical.tokens("a I ok"), [])


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.docs = [
            "review a diff before merge, label findings by severity",
            "reproduce the bug as a failing test before the fix",
            "plan the schema migration and the rollback",
        ]
        self.index = lexical.Index(self.docs)

    def test_exact_document_ranks_first(self):
        ranking = self.index.rank("review this diff by severity")
        self.assertEqual(ranking[0][0], 0)
        self.assertGreater(ranking[0][1], 0.0)

    def test_unrelated_prompt_scores_zero_everywhere(self):
        ranking = self.index.rank("zzz qqq")
        self.assertEqual(ranking[0][1], 0.0)

    def test_cosine_of_identical_vectors_is_one(self):
        vec = self.index.vector_for("rollback schema")
        self.assertAlmostEqual(lexical.cosine(vec, vec), 1.0, places=6)

    def test_ranking_is_deterministic(self):
        self.assertEqual(self.index.rank("bug test"), self.index.rank("bug test"))


if __name__ == "__main__":
    unittest.main()
