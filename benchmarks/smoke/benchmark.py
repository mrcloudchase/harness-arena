"""smoke: five small Python tasks. Peers rank the results; hidden pytest tests are the ground-truth anchor."""
from pathlib import Path

from harness_arena.benchmark import Task
from harness_arena.checks import pytest_check

HIDDEN = Path(__file__).parent / "hidden"
SPECS = {
    "roman": "to_roman(n: int) -> str for 1 <= n <= 3999, and from_roman(s: str) -> int, its inverse",
    "wordfreq": "top_words(text: str, n: int) -> list[tuple[str, int]]: the n most frequent words, lowercased, "
                "ignoring punctuation, most frequent first, ties in alphabetical order",
    "intervals": "merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]: merge overlapping or touching "
                 "closed intervals, returned sorted",
    "lru": "class LRUCache(capacity: int) with get(key) -> value or -1, and put(key, value); a full cache "
           "evicts the least recently used key; get and put both count as a use",
    "balanced": "is_balanced(s: str) -> bool: true when every (), [] and {} in s is closed in the right order; "
                "other characters are ignored",
}


def tasks():
    for id, spec in SPECS.items():
        yield Task(id, f"Write solution.py, a Python module that defines {spec}. Use only the standard library.")


def deliverables(task):
    return ["solution.py"]


CRITERIA = ("Correctness comes first: the code must behave correctly on ordinary and edge-case inputs, so try it. Among results "
            "that are equally correct, prefer the clearer, simpler and more idiomatic code. A result with no code is the worst.")
check_tests = pytest_check(HIDDEN)


def criteria(task):
    return CRITERIA


def check(task, submission):
    return check_tests(task, submission)


def reference(task):
    return {"solution.py": (Path(__file__).parent / "reference" / task.id / "solution.py").read_text()}
