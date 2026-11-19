"""Deterministic lexical routing.

Tier 2 answers two questions without spending a token: does a skill's description
carry the words users actually say, and do two descriptions collide? The scorer is
stemmed TF-IDF with cosine similarity, which is an approximation and says so in the
README. It cannot judge semantics; it can catch the two bugs that dominate real
trigger failures: missing vocabulary (false negative) and an over-broad description
that outranks the right skill (false positive).
"""

import math
import re

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "can", "do", "for",
    "from", "get", "has", "have", "how", "i", "if", "in", "into", "is", "it", "its",
    "me", "my", "of", "on", "or", "our", "please", "should", "so", "that", "the",
    "their", "them", "then", "there", "this", "to", "use", "want", "was", "we",
    "what", "when", "which", "will", "with", "you", "your",
}

WORD_RE = re.compile(r"[a-z0-9]+")


VOWELS = set("aeiou")


def _stem(word: str) -> str:
    """Crude, symmetric stemmer. Symmetric matters more than correct: `upgrade` and
    `upgraded` must land on the same token or the router splits one concept in two.
    The README states what this cannot do."""
    if len(word) > 4 and word.endswith("ies"):
        word = word[:-3] + "y"
    elif len(word) > 4 and word.endswith("es") and word[:-2].endswith(("s", "x", "z", "ch", "sh")):
        word = word[:-2]
    elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    if len(word) > 4 and word.endswith(("ing", "ed")):
        word = word[:-3] if word.endswith("ing") else word[:-2]
        if len(word) > 2 and word[-1] == word[-2] and word[-1] not in VOWELS:
            word = word[:-1]
    if len(word) >= 5 and word.endswith("e"):
        word = word[:-1]
    return word


def tokens(text: str) -> list:
    return [
        _stem(w) for w in WORD_RE.findall(text.lower())
        if w not in STOPWORDS and len(w) > 2
    ]


class Index:
    """TF-IDF over a fixed set of documents."""

    def __init__(self, docs: list):
        self.vectors = []
        df = {}
        tokenized = [tokens(d) for d in docs]
        for toks in tokenized:
            for term in set(toks):
                df[term] = df.get(term, 0) + 1
        total = max(len(tokenized), 1)
        self.idf = {term: math.log(total / count) + 1.0 for term, count in df.items()}
        for toks in tokenized:
            self.vectors.append(self._vector(toks))

    def _vector(self, toks: list) -> dict:
        tf = {}
        for term in toks:
            tf[term] = tf.get(term, 0) + 1
        vec = {t: (1.0 + math.log(c)) * self.idf.get(t, 1.0) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def vector_for(self, text: str) -> dict:
        return self._vector(tokens(text))

    def score(self, text: str, index: int) -> float:
        return cosine(self.vector_for(text), self.vectors[index])

    def rank(self, text: str) -> list:
        return sorted(
            ((i, self.score(text, i)) for i in range(len(self.vectors))),
            key=lambda pair: (-pair[1], pair[0]),
        )


def cosine(a: dict, b: dict) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())
