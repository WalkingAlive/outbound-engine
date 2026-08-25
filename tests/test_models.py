from outbound_engine.models import Signal


def test_signal_id_is_stable_for_same_url():
    a = Signal(source="news", target="Acme", title="t1", body="b1", url="https://x.com/a")
    b = Signal(source="news", target="Acme", title="t2", body="b2", url="https://x.com/a")
    assert a.id == b.id


def test_signal_id_differs_without_url():
    a = Signal(source="news", target="Acme", title="Different headline", body="b")
    b = Signal(source="news", target="Acme", title="Other headline", body="b")
    assert a.id != b.id
