"""B6 rssagg — tests. Run: pytest test_feedhive.py"""
import sys, os

import pytest

feedparser_ok = True
try:
    import feedparser
except ImportError:
    feedparser_ok = False

OPML = """<?xml version="1.0"?>
<opml version="2.0"><body>
<outline text="HN" title="HN" type="rss" xmlUrl="https://news.ycombinator.com/rss"/>
<outline text="arXiv" title="arXiv" type="rss" xmlUrl="https://arxiv.org/rss/cs.AI"/>
</body></opml>"""

@pytest.mark.skipif(not feedparser_ok, reason="feedparser not installed")
def test_parse_opml():
    from rssagg.agg.opml import parse_opml
    feeds = parse_opml(OPML)
    assert len(feeds) == 2
    assert feeds[0][1] == "https://news.ycombinator.com/rss"

@pytest.mark.skipif(not feedparser_ok, reason="feedparser not installed")
def test_export_opml_roundtrip():
    from rssagg.agg.opml import export_opml, parse_opml
    feeds = [type("F", (), {"title": "HN", "url": "https://hn/rss"})()]
    xml = export_opml(feeds)
    assert "HN" in xml and "https://hn/rss" in xml
    assert len(parse_opml(xml)) == 1
