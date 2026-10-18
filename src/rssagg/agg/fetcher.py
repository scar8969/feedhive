import urllib.request

import feedparser


def fetch_feed(url, etag=""):
    headers = {"User-Agent": "rssagg/1.0"}
    if etag:
        headers["If-None-Match"] = etag
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            if r.status == 304:
                return None, etag
            new_etag = r.headers.get("ETag", "")
            raw = r.read()
    except Exception:
        return None, etag
    d = feedparser.parse(raw)
    entries = []
    for e in d.entries:
        entries.append(
            {
                "guid": e.get("id", e.get("link", "")),
                "title": e.get("title", ""),
                "link": e.get("link", ""),
                "content": e.get("summary", ""),
                "published": e.get("published_parsed"),
            }
        )
    return {"title": d.feed.get("title", url), "entries": entries}, new_etag
