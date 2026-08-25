import tempfile
from pathlib import Path

import pytest

from outbound_engine.models import Signal, Target
from outbound_engine.storage import Storage


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmp:
        yield Storage(db_path=Path(tmp) / "test.db")


def test_upsert_and_list_targets(store):
    store.upsert_target(Target(name="Jane Doe", type="person", keywords=["seed round"]))
    targets = store.list_targets()
    assert len(targets) == 1
    assert targets[0].name == "Jane Doe"
    assert targets[0].keywords == ["seed round"]


def test_upsert_target_overwrites(store):
    store.upsert_target(Target(name="Jane Doe", type="person", notes="v1"))
    store.upsert_target(Target(name="Jane Doe", type="person", notes="v2"))
    targets = store.list_targets()
    assert len(targets) == 1
    assert targets[0].notes == "v2"


def test_remove_target(store):
    store.upsert_target(Target(name="Jane Doe", type="person"))
    assert store.remove_target("Jane Doe") is True
    assert store.remove_target("Jane Doe") is False
    assert store.list_targets() == []


def test_save_signals_dedupes(store):
    sig = Signal(source="news", target="Jane Doe", title="Jane raises seed", body="...", url="https://example.com/a")
    new1 = store.save_signals([sig])
    new2 = store.save_signals([sig])
    assert len(new1) == 1
    assert len(new2) == 0


def test_unsurfaced_and_mark_surfaced(store):
    sig = Signal(source="news", target="Jane Doe", title="t", body="b")
    store.save_signals([sig])
    assert len(store.unsurfaced_signals()) == 1
    store.mark_surfaced([sig.id])
    assert len(store.unsurfaced_signals()) == 0


def test_save_and_load_latest_brief(store):
    from outbound_engine.models import DailyBrief

    brief = DailyBrief(generated_for="you", summary="test summary", recommendations=[])
    store.save_brief(brief)
    loaded = store.latest_brief()
    assert loaded.summary == "test summary"


def test_repos(store):
    store.add_repo("/tmp/foo")
    store.add_repo("/tmp/foo")  # idempotent
    assert store.list_repos() == ["/tmp/foo"]
