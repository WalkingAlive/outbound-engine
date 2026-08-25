from unittest.mock import patch

from outbound_engine.connectors.news import fetch_news


class FakeEntry(dict):
    def get(self, key, default=None):
        return dict.get(self, key, default)


class FakeParsed:
    bozo = False

    def __init__(self, entries):
        self.entries = entries


def test_fetch_news_maps_entries_to_signals():
    entries = [
        FakeEntry(
            title="Acme raises $10M seed",
            summary="Acme Corp announced a $10M seed round.",
            link="https://news.example.com/acme-seed",
            published="Mon, 25 Aug 2026 10:00:00 GMT",
            source={"title": "Example News"},
        )
    ]
    with patch("outbound_engine.connectors.news.feedparser.parse", return_value=FakeParsed(entries)):
        signals = fetch_news("Acme Corp", limit=5)

    assert len(signals) == 1
    assert signals[0].source == "news"
    assert signals[0].target == "Acme Corp"
    assert "Acme raises" in signals[0].title
    assert signals[0].url == "https://news.example.com/acme-seed"


def test_fetch_news_handles_empty_feed():
    with patch("outbound_engine.connectors.news.feedparser.parse", return_value=FakeParsed([])):
        signals = fetch_news("Nobody Interesting")
    assert signals == []
