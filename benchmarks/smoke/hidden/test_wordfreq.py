from solution import top_words


def test_counts_and_order():
    assert top_words("the cat and the hat and the bat", 2) == [("the", 3), ("and", 2)]


def test_case_and_punctuation():
    assert top_words("Hi, hi! HI? ho.", 5) == [("hi", 3), ("ho", 1)]


def test_ties_alphabetical():
    assert top_words("b a c", 3) == [("a", 1), ("b", 1), ("c", 1)]


def test_empty():
    assert top_words("", 3) == []
