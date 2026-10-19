"""The tally: every judge's ranking of a group becomes points, the points are averaged into a score per result,
and a harness's final score is the average of its results' scores. Ranking the harnesses by it is the final result.

A judge's ranking of n results gives the best (n-1)/(n-1) = 1 point and the worst 0, evenly between (a Borda count).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean

from .stats import kendall_w, spearman


@dataclass
class Standing:
    harness: str
    score: float = 0.0                               # mean Borda score over its results, 0 to 1
    mean_rank: float = 0.0                           # mean place among the harnesses of its groups
    firsts: int = 0
    groups: int = 0
    self_bias: float | None = None                   # points it gave its own results minus what the other judges gave them


@dataclass
class Tally:
    standings: list[Standing] = field(default_factory=list)
    agreement: float | None = None                   # Kendall's W between the judges, averaged over groups
    anchor: float | None = None                      # rank correlation with a deterministic check, where one varies
    judgments: int = 0


def borda(ranking: list[str]) -> dict[str, float]:
    n = len(ranking)
    return {sid: (n - 1 - pos) / (n - 1) for pos, sid in enumerate(ranking)}


def tally(judgments: list[dict], authors: dict[str, str], anchors: dict[str, float] | None = None) -> Tally:
    """judgments are the rows of valid rankings; authors maps submission id to harness (read from the sealed map)."""
    valid = [j for j in judgments if j["ranking"] and not j["error"] and not j["finding"]]
    by_group = defaultdict(list)
    for j in valid:
        by_group[(j["task"], j["repeat"])].append(j)
    points = defaultdict(list)                       # harness -> its results' scores
    places, firsts, groups_of = defaultdict(list), defaultdict(int), defaultdict(int)
    bias = defaultdict(list)
    agreements, anchor_rs = [], []
    for js in by_group.values():
        per_judge = [(j["judge"], borda(j["ranking"])) for j in js]
        scores = {sid: mean(b[sid] for _, b in per_judge) for sid in per_judge[0][1]}
        ordered = sorted(scores, key=scores.get, reverse=True)
        for place, sid in enumerate(ordered, 1):
            h = authors[sid]
            points[h].append(scores[sid])
            places[h].append(place)
            groups_of[h] += 1
            firsts[h] += scores[sid] == scores[ordered[0]]
        for judge, b in per_judge:
            for sid in b:
                others = [o[sid] for who, o in per_judge if who != authors[sid]]
                if authors[sid] == judge and others:
                    bias[judge].append(b[sid] - mean(others))
        if len(js) > 1:
            agreements.append(kendall_w([j["ranking"] for j in js]))
        if anchors and all(s in anchors for s in scores):
            rho = spearman([scores[s] for s in ordered], [anchors[s] for s in ordered])
            if rho is not None:
                anchor_rs.append(rho)
    standings = [Standing(h, mean(p), mean(places[h]), firsts[h], groups_of[h], mean(bias[h]) if bias[h] else None)
                 for h, p in points.items()]
    standings.sort(key=lambda s: (-s.score, s.mean_rank))
    return Tally(standings, mean(agreements) if agreements else None, mean(anchor_rs) if anchor_rs else None, len(valid))


def anchor_scores(run, bench) -> dict[str, float]:
    """The deterministic check's score for each submission, where the benchmark has one. A ground-truth anchor for the
    peer ranking, never part of it."""
    tasks = {t.id: t for t in bench.tasks()}
    out = {}
    for sid, g in run.load("submissions", {}).items():
        scored = bench.check(tasks[g["task"]], run.path / "submissions" / sid)
        if scored is not None:
            out[sid] = scored[0]
    return out
