"""readme: write the README for a small Python project. Judged against a rubric by a model panel, plus a
deterministic check that the README names the project's public API."""
from hiddenarena.benchmark import Deterministic, Model, Task

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
NAMES = {"slugify": ["slugify", "unslugify", "sep", "max_len"],
         "bucket": ["TokenBucket", "allow", "wait_time", "rate", "capacity"],
         "csvstat": ["csvstat", "--col", "--delim", "count", "mean"]}
RUBRIC = (
    "The first lines say what the project is and does.",
    "It says how to install it or get it running.",
    "It has at least one usage example that matches the real API.",
    "Every public function, class or command is documented with its arguments and behaviour.",
    "It is accurate: it claims nothing the code does not do.",
    "It is concise and well organized, with no filler.",
)


def tasks():
    for id, files in CODE.items():
        yield Task(id, "This folder holds a small Python project. Write README.md for it, for someone who has "
                       "never seen it: what it is, how to use it, and what each public part does.", files)


def deliverables(task):
    return ["README.md"]


def mentions(task, submission):
    text = (submission / "README.md").read_text() if (submission / "README.md").is_file() else ""
    names = NAMES[task.id]
    return sum(n in text for n in names) / len(names), f"names {len(names)} public items"


def judges(task):
    return [Deterministic(mentions, "names-the-api"), Model(RUBRIC, min_agreement=0.6, pairwise=True)]
