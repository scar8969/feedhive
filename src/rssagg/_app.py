import os

from .agg.api import bp
from .agg.fetcher import fetch_feed
from .agg.opml import export_opml, parse_opml
from .agg.search import search
from .models import Entry, Feed, db

from datetime import datetime

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, url_for
from . import paths

# templates/ lives at the project root, next to web/ -- the same layout the
# build produces and the one the Dockerfile and wsgi.py assume.

def build_app():
    """Build the application: configuration, database, then routes."""
    app = Flask(__name__, template_folder=str(paths.TEMPLATES_DIR))
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("RSSAGG_DB_URI", "sqlite:///" + str(paths.INSTANCE_DIR / "rssagg.db"))
    app.config["SECRET_KEY"] = os.environ.get("RSSAGG_SECRET_KEY", "rssagg-local")
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.register_blueprint(bp)

    @app.context_processor
    def _inject():
        return {"app_name": "📰 rssagg", "stats": _stats()}

    def _stats():
        return {"feeds": Feed.query.count(), "entries": Entry.query.count(),
                "unread": Entry.query.filter_by(read=0).count(),
                "starred": Entry.query.filter_by(starred=1).count()}

    def _safe_next(target):
        """Only ever redirect back into this app: a relative path with no scheme."""
        if target and target.startswith("/") and not target.startswith("//"):
            return target
        return url_for("index")

    def _store_entries(feed, feed_data):
        """Write the entries of a fetched feed, skipping duplicates and empty rows."""
        added = 0
        for raw in feed_data.get("entries", []):
            guid = (raw.get("guid") or "").strip()
            link = (raw.get("link") or "").strip()
            published = raw.get("published")
            if hasattr(published, "tm_year"):
                published = datetime(*tuple(published)[:6])
            elif not isinstance(published, datetime):
                published = None
            # guid is UNIQUE in the schema; an entry without one is keyed by its link.
            if guid and Entry.query.filter_by(guid=guid).first():
                continue
            if not guid and link and Entry.query.filter_by(url=link).first():
                continue
            db.session.add(Entry(feed_id=feed.id, guid=guid or link or None,
                                 title=raw.get("title") or "", url=link,
                                 content=raw.get("content") or "", published_at=published))
            added += 1
        return added

    @app.get("/")
    def index():
        q = (request.args.get("q") or "").strip()
        only = request.args.get("only") or ""
        feed_id = request.args.get("feed", type=int)

        if q:
            ids = [row["id"] for row in search(q)]
            query = Entry.query.filter(Entry.id.in_(ids)) if ids else Entry.query.filter(db.false())
        else:
            query = Entry.query
        if feed_id:
            query = query.filter(Entry.feed_id == feed_id)
        if only == "unread":
            query = query.filter(Entry.read == 0)
        elif only == "starred":
            query = query.filter(Entry.starred == 1)

        entries = query.order_by(Entry.published_at.desc(), Entry.id.desc()).limit(200).all()
        feeds = Feed.query.order_by(Feed.title).all()
        return render_template(
            "index.html", entries=entries, feeds=feeds, q=q, only=only, feed_id=feed_id,
            feed_titles={f.id: (f.title or f.url) for f in feeds},
            unread_by_feed={f.id: Entry.query.filter_by(feed_id=f.id, read=0).count() for f in feeds})

    @app.get("/feeds")
    def feeds_page():
        feeds = Feed.query.order_by(Feed.id).all()
        return render_template(
            "feeds.html", feeds=feeds,
            entry_counts={f.id: Entry.query.filter_by(feed_id=f.id).count() for f in feeds},
            unread_by_feed={f.id: Entry.query.filter_by(feed_id=f.id, read=0).count() for f in feeds})

    def _subscribe(url, category):
        """Fetch a feed first, then store it. Returns the Feed or None on failure."""
        url = (url or "").strip()
        if not url:
            flash("A feed URL is required.", "error")
            return None
        if Feed.query.filter_by(url=url).first():
            flash("Already subscribed: %s" % url, "error")
            return None
        feed_data, etag = fetch_feed(url)
        if not feed_data:
            flash("Could not fetch %s -- nothing was stored." % url, "error")
            return None
        feed = Feed(url=url, title=feed_data.get("title") or url, category=category or "",
                    etag=etag or "", last_poll=datetime.utcnow())
        db.session.add(feed)
        db.session.flush()
        added = _store_entries(feed, feed_data)
        db.session.commit()
        flash("Subscribed to %s (%d new entries)." % (feed.title, added), "success")
        return feed

    @app.post("/feeds/add")
    def feed_add():
        _subscribe(request.form.get("url", ""), request.form.get("category", ""))
        return redirect(url_for("feeds_page"))

    @app.post("/feeds/<int:fid>/poll")
    def feed_poll(fid):
        feed = db.session.get(Feed, fid)
        if feed is None:
            flash("No feed with id %s." % fid, "error")
            return redirect(url_for("feeds_page"))
        feed_data, etag = fetch_feed(feed.url, feed.etag or "")
        if not feed_data:
            flash("%s returned nothing (unreachable, or unchanged since the last poll)." % feed.url, "error")
        else:
            added = _store_entries(feed, feed_data)
            if feed_data.get("title"):
                feed.title = feed_data["title"]
            feed.etag = etag or ""
            flash("Polled %s: %d new entries." % (feed.title, added), "success")
        feed.last_poll = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("feeds_page"))

    @app.post("/feeds/<int:fid>/delete")
    def feed_delete(fid):
        feed = db.session.get(Feed, fid)
        if feed is None:
            flash("No feed with id %s." % fid, "error")
            return redirect(url_for("feeds_page"))
        title = feed.title or feed.url
        entry_ids = [e.id for e in Entry.query.filter_by(feed_id=feed.id).all()]
        for row in Entry.query.filter(Entry.feed_id == feed.id).all():
            db.session.delete(row)
        db.session.delete(feed)
        db.session.commit()
        flash("Deleted %s and its %d stored entries." % (title, len(entry_ids)), "success")
        return redirect(url_for("feeds_page"))

    @app.post("/feeds/import")
    def feed_import():
        body = request.form.get("opml", "")
        category = request.form.get("category", "")
        try:
            outlines = parse_opml(body)
        except Exception as exc:
            flash("That is not parseable OPML: %s" % exc, "error")
            return redirect(url_for("feeds_page"))
        if not outlines:
            flash("No <outline xmlUrl=...> found in that document.", "error")
            return redirect(url_for("feeds_page"))
        added = skipped = failed = 0
        for _title, url in outlines:
            if Feed.query.filter_by(url=url).first():
                skipped += 1
                continue
            if _subscribe(url, category) is None:
                failed += 1
            else:
                added += 1
        flash("OPML import: %d added, %d already subscribed, %d unreachable." % (added, skipped, failed),
              "success" if added else "error")
        return redirect(url_for("feeds_page"))

    @app.get("/feeds/export.opml")
    def feed_export():
        feeds = Feed.query.order_by(Feed.id).all()
        return Response(export_opml(feeds), mimetype="text/x-opml",
                        headers={"Content-Disposition": "attachment; filename=feeds.opml"})

    @app.post("/entries/<int:eid>/<action>")
    def entry_set(eid, action):
        entry = db.session.get(Entry, eid)
        if entry is None:
            flash("No entry with id %s." % eid, "error")
        elif action == "read":
            entry.read = 1
            db.session.commit()
        elif action == "unread":
            entry.read = 0
            db.session.commit()
        elif action == "star":
            entry.starred = 1
            db.session.commit()
        elif action == "unstar":
            entry.starred = 0
            db.session.commit()
        else:
            flash("Unknown entry action %r." % action, "error")
        return redirect(_safe_next(request.form.get("next")))

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "feeds": Feed.query.count(), "entries": Entry.query.count()})

    # python -m web.app
    if __name__ == "__main__":
        app.run(host="127.0.0.1", port=5000, debug=False)

    return app

app = build_app()
