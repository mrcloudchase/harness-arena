"""The few statistics the blindness audit and the tally need, in plain Python."""
from __future__ import annotations

from statistics import correlation, StatisticsError


def p_at_least(k: int, chances: list[float]) -> float:
    """The probability of at least k right out of guesses that are each right with their own chance, by luck alone
    (a Poisson binomial, computed exactly)."""
    dist = [1.0]
    for p in chances:
        dist = [(dist[i] if i < len(dist) else 0) * (1 - p) + (dist[i - 1] * p if i else 0) for i in range(len(dist) + 1)]
    return sum(dist[k:])


def kendall_w(rankings: list[list[str]]) -> float:
    """How much judges agree on an ordering: 1 is identical rankings, 0 is none. Needs two judges and two items."""
    m, items = len(rankings), rankings[0]
    n = len(items)
    if m < 2 or n < 2:
        return 0.0
    sums = {i: sum(r.index(i) + 1 for r in rankings) for i in items}
    mean = m * (n + 1) / 2
    return 12 * sum((s - mean) ** 2 for s in sums.values()) / (m ** 2 * (n ** 3 - n))


def spearman(xs: list[float], ys: list[float]) -> float | None:
    """Rank correlation (ties share their average rank), or None when either side never varies."""
    def ranks(v):
        return [sum((x < value) + (x == value) / 2 for x in v) + 0.5 for value in v]
    try:
        return correlation(ranks(xs), ranks(ys))
    except StatisticsError:
        return None
