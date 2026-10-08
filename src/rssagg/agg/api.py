from .fetcher import fetch_feed
from .search import search
from ..models import Entry, Feed, db

from datetime import datetime

from flask import Blueprint, jsonify, request

bp = Blueprint("agg", __name__)

def _as_dt(value):
    """feedparser hands back time.struct_time; DateTime columns need datetime."""
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime(*tuple(value)[:6])
    except Exception:
        return None

def _entry_or_404(id):
    eid = int(id) if str(id).isdigit() else None
    e = db.session.get(Entry, eid) if eid is not None else None
    if e is None:
        return None
    return e

@bp.post("/api/feeds")
def add_feed():
    d = request.get_json(force=True, silent=True) or {}
    url = d.get("url", "")
    if not url:
        return jsonify({"error": "url required"}), 400
    if Feed.query.filter_by(url=url).first():
        return jsonify({"error": "feed exists"}), 409
    feed_data, etag = fetch_feed(url)
    if not feed_data:
        return jsonify({"error": "feed unreachable", "url": url}), 502
    feed = Feed(url=url, title=feed_data.get("title") or url,
                category=d.get("category", ""), etag=etag or "",
                last_poll=datetime.utcnow())
    db.session.add(feed)
    db.session.flush()
    for e in feed_data.get("entries", []):
        guid = e.get("guid") or e.get("link") or ""
        if not guid or Entry.query.filter_by(guid=guid).first():
            continue
        db.session.add(Entry(feed_id=feed.id, guid=guid,
                             title=e.get("title", ""), url=e.get("link", ""),
                             content=e.get("content", ""),
                             published_at=_as_dt(e.get("published"))))
    db.session.commit()
    return jsonify({"id": feed.id, "title": feed.title})

@bp.get("/api/feeds")
def list_feeds():
    return jsonify({"feeds": [{"id": f.id, "title": f.title, "category": f.category,
                               "unread": Entry.query.filter_by(feed_id=f.id, read=0).count()}
                              for f in Feed.query.all()]})

@bp.get("/api/entries")
def entries():
    feed_id = request.args.get("feed", type=int)
    q = Entry.query
    if feed_id:
        q = q.filter_by(feed_id=feed_id)
    if request.args.get("unread"):
        q = q.filter_by(read=0)
    rows = [{"id": e.id, "title": e.title, "url": e.url, "read": bool(e.read),
             "starred": bool(e.starred), "feed_id": e.feed_id,
             "published": e.published_at.isoformat() if e.published_at else ""}
            for e in q.order_by(Entry.published_at.desc()).limit(100).all()]
    return jsonify({"entries": rows})

@bp.post("/api/entries/<id>/read")
def mark_read(id):
    e = _entry_or_404(id)
    if e is None:
        return jsonify({"error": "not_found"}), 404
    e.read = 1
    db.session.commit()
    return jsonify({"status": "read", "id": e.id})

@bp.post("/api/entries/<id>/star")
def star(id):
    e = _entry_or_404(id)
    if e is None:
        return jsonify({"error": "not_found"}), 404
    e.starred = 1 - e.starred
    db.session.commit()
    return jsonify({"status": "starred" if e.starred else "unstarred", "id": e.id})

@bp.get("/api/search")
def do_search():
    return jsonify({"entries": search(request.args.get("q", ""))})
