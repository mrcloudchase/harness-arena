"""Pairwise judging runs both orders, and so cancels a judge that always picks the first."""
import pytest

from hiddenarena.benchmark import Task
from hiddenarena.models import Panel, parse_scores, parse_winner
from hiddenarena.submission import Submission


def sub(tmp_path, id, text):
    (tmp_path / id).mkdir()
    (tmp_path / id / "solution.py").write_text(text)
    return Submission(id, Task("t", "do it"), tmp_path / id)


class Judge:
    def __init__(self, name, family, pick):
        self.name, self.family, self.pick, self.prompts = name, family, pick, []

    async def ask(self, prompt):
        self.prompts.append(prompt)
        return self.pick(prompt)


async def test_both_orders_are_asked_and_a_first_picker_ties(tmp_path):
    a, b = sub(tmp_path, "S-aaaaaa", "A"), sub(tmp_path, "S-bbbbbb", "B")
    first = Judge("x/1", "x", lambda p: '{"winner": "%s"}' % ("S-aaaaaa" if p.index("S-aaaaaa") < p.index("S-bbbbbb") else "S-bbbbbb"))
    panel = Panel([first, Judge("y/2", "y", lambda p: '{"winner": "S-aaaaaa"}')])
    scores = await panel.prefer(a, b, ("good",))
    assert len(first.prompts) == 2
    assert first.prompts[0].index("S-aaaaaa") < first.prompts[0].index("S-bbbbbb")
    assert first.prompts[1].index("S-bbbbbb") < first.prompts[1].index("S-aaaaaa")
    assert scores["x/1"][0] == 0.5                                 # position bias cancels
    assert scores["y/2"][0] == 1.0                                 # a real preference survives


def test_panel_rules():
    j = lambda f: Judge(f"{f}/m", f, None)
    with pytest.raises(SystemExit):
        Panel([j("openai"), j("openai")])                          # one family is not a panel
    with pytest.raises(SystemExit):
        Panel([j("openai"), j("google")], compared="openai")       # no judge from the compared family
    assert Panel([j("openai"), j("google")], compared="deepseek")


def test_replies_are_parsed_strictly():
    assert parse_scores('x {"items": {"1": {"score": 2, "reason": "r"}}}', 1)[0] == 1.0   # clamped
    with pytest.raises(ValueError):
        parse_scores("no json", 1)
    with pytest.raises(KeyError):
        parse_scores('{"items": {}}', 1)
    with pytest.raises(ValueError):
        parse_winner('{"winner": "S-other"}', ("S-a", "S-b"))
