"""readme: write the README for a small Python project. Ranked by the peer harnesses alone: no deterministic check."""
from harness_arena.benchmark import Task

CODE = {
    "slugify": {"slugify.py": '''import re
import unicodedata


def slugify(text, sep="-", max_len=None):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", sep, text.lower()).strip(sep)
    if max_len and len(slug) > max_len:
        slug = slug[:max_len].rstrip(sep)
    return slug


def unslugify(slug, sep="-"):
    return slug.replace(sep, " ").title()
'''},
    "bucket": {"ratelimit.py": '''import time


class TokenBucket:
    def __init__(self, rate, capacity, clock=time.monotonic):
        self.rate, self.capacity, self.clock = rate, capacity, clock
        self.tokens, self.stamp = capacity, clock()

    def _refill(self):
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.stamp) * self.rate)
        self.stamp = now

    def allow(self, cost=1):
        self._refill()
        if cost > self.tokens:
            return False
        self.tokens -= cost
        return True

    def wait_time(self, cost=1):
        self._refill()
        return max(0.0, (cost - self.tokens) / self.rate)
'''},
    "csvstat": {"csvstat.py": '''import argparse
import csv
import sys


def main(argv=None):
    p = argparse.ArgumentParser(description="Summarize a numeric CSV column")
    p.add_argument("file")
    p.add_argument("--col", required=True)
    p.add_argument("--delim", default=",")
    a = p.parse_args(argv)
    with open(a.file, newline="") as f:
        rows = list(csv.DictReader(f, delimiter=a.delim))
    if rows and a.col not in rows[0]:
        print(f"no column {a.col!r}", file=sys.stderr)
        return 2
    values = []
    for r in rows:
        try:
            values.append(float(r[a.col]))
        except ValueError:
            pass
    if not values:
        print("no numeric values", file=sys.stderr)
        return 1
    print(f"count={len(values)} min={min(values)} max={max(values)} mean={sum(values) / len(values):.4g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''},
}
CRITERIA = ("A better README tells a newcomer, in order: what the project is and does; how to get it running; at least one "
            "usage example that matches the real code; and what every public function, class or command does with its "
            "arguments. It must be accurate to the code in the folder, concise and well organised, with no filler. A README "
            "that claims things the code does not do is worse than a short honest one.")


def tasks():
    for id, files in CODE.items():
        yield Task(id, "This folder holds a small Python project. Write README.md for it, for someone who has "
                       "never seen it: what it is, how to use it, and what each public part does.", files)


def deliverables(task):
    return ["README.md"]


def criteria(task):
    return CRITERIA
