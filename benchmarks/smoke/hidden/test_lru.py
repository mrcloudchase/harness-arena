from solution import LRUCache


def test_eviction():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    assert c.get(1) == 1
    c.put(3, 3)
    assert c.get(2) == -1
    assert c.get(3) == 3


def test_update_counts_as_use():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.put(1, 10)
    c.put(3, 3)
    assert c.get(1) == 10 and c.get(2) == -1


def test_missing():
    assert LRUCache(1).get(7) == -1
