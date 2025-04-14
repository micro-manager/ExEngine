from exengine.kernel.queue import PriorityQueue


def test_priority_queue():
    q = PriorityQueue()
    q.put((1, "first"))
    q.put((1, "second"))
    q.put((1, "third"))
    q.put((0, "priority"))
    assert q.get() == (0, "priority")
    assert q.get() == (1, "first")
    assert q.get() == (1, "second")
    assert q.get() == (1, "third")
    assert q.empty()