"""Can a program tell which harness wrote a submission? A leave-one-out naive Bayes classifier over the words
of each submission tries; if it beats chance, what gave it away is a fingerprint.

Only words found in comments and prose files are offered back to the scrubber as new terms, because
redacting those never changes what a submission does.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .stats import p_at_least

WORD = re.compile(r"[a-z_][a-z0-9_]{2,}")
MIN_SUPPORT = 2                                      # a fingerprint shows up in at least this many of a harness's submissions
ALPHA = 0.05


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def classify(samples: list[tuple[str, str]]) -> tuple[int, float]:
    """samples are (harness, text). Returns how many were guessed right, leaving each out, and how likely
    that many are by luck."""
    labels = sorted({label for label, _ in samples})
    if len(labels) < 2:
        return 0, 1.0
    counts = {label: Counter() for label in labels}
    docs = [(label, Counter(words(text))) for label, text in samples]
    for label, doc in docs:
        counts[label].update(doc)
    vocab = {w for c in counts.values() for w in c}
    right = 0
    for label, doc in docs:
        scores = {}
        for other in labels:
            seen = counts[other] - doc if other == label else counts[other]
            total = sum(seen.values()) + len(vocab)
            scores[other] = sum(n * math.log((seen[w] + 1) / total) for w, n in doc.items())
        right += max(scores, key=scores.get) == label
    return right, p_at_least(right, [1 / len(labels)] * len(samples))


def exclusive_terms(samples: list[tuple[str, str, str]]) -> set[str]:
    """samples are (harness, full text, prose). Words that recur in one harness's prose and appear nowhere in any
    other harness's submissions."""
    out = set()
    for label in {s[0] for s in samples}:
        recurring = Counter(w for h, _, prose in samples if h == label for w in set(words(prose)))
        elsewhere = {w for h, text, _ in samples if h != label for w in words(text)}
        out |= {w for w, n in recurring.items() if n >= MIN_SUPPORT and w not in elsewhere}
    return out
