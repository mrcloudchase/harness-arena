import pytest
from solution import from_roman, to_roman


@pytest.mark.parametrize("n,s", [(1, "I"), (4, "IV"), (9, "IX"), (14, "XIV"), (40, "XL"), (90, "XC"),
                                 (400, "CD"), (1994, "MCMXCIV"), (2024, "MMXXIV"), (3999, "MMMCMXCIX")])
def test_known(n, s):
    assert to_roman(n) == s
    assert from_roman(s) == n


def test_round_trip():
    assert all(from_roman(to_roman(n)) == n for n in range(1, 4000))
