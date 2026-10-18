import pytest
from solution import is_balanced


@pytest.mark.parametrize("s,ok", [("", True), ("()[]{}", True), ("([{}])", True), ("(]", False), ("([)]", False),
                                  ("((", False), (")(", False), ("a(b[c]{d})e", True), ("}", False)])
def test_cases(s, ok):
    assert is_balanced(s) is ok
