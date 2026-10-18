#!/usr/bin/env python3
"""rssagg CLI - manage feeds and entries from the terminal.

Heavy imports (Flask app, database) are deferred into the individual command
handlers so that ``python cli.py --help`` works even on a machine where the
optional runtime dependencies are not importable yet.
"""

import argparse
import sys


def _app():
    """Build the Flask app and push an application context (imported lazily)."""
    try:
        from ._app import app
    except ModuleNotFoundError as exc:  # environment guard
        sys.stderr.write(
            "error: cannot import the application (%s).\n"
            "       Install the requirements and run from the project root:\n"
            "       pip install -r requirements.txt\n" % exc
        )
        raise SystemExit(2)
    ctx = app.app_context()
    ctx.push()
    return app, ctx


def cmd_feeds(args):
    from .models import Entry, Feed

    app, ctx = _app()
    try:
        rows = Feed.query.order_by(Feed.id).all()
        if args.json:
            import json

            print(
                json.dumps(
                    [
                        {
                            "id": f.id,
                            "title": f.title,
                            "url": f.url,
                            "category": f.category,
                            "unread": Entry.query.filter_by(feed_id=f.id, read=0).count(),
                        }
                        for f in rows
                    ]
                )
            )
            return 0
        if not rows:
            print("no feeds yet - add one with:  cli.py add <url>")
            return 0
        print("%-4s %-30s %-42s %s" % ("id", "title", "url", "unread"))
        for f in rows:
            unread = Entry.query.filter_by(feed_id=f.id, read=0).count()
            print("%-4s %-30s %-42s %s" % (f.id, (f.title or "")[:30], f.url[:42], unread))
        return 0
    finally:
        ctx.pop()


def cmd_add(args):
    from .models import Feed

    app, ctx = _app()
    try:
        existing = Feed.query.filter_by(url=args.url).first()
        if existing:
            print("already subscribed: %s (id=%s)" % (existing.title, existing.id))
            return 1
        client = app.test_client()
        resp = client.post("/api/feeds", json={"url": args.url, "category": args.category})
        if resp.status_code != 200:
            print(
                "failed (%s): %s" % (resp.status_code, resp.get_data(as_text=True)), file=sys.stderr
            )
            return 1
        data = resp.get_json()
        print("subscribed: %s (id=%s)" % (data.get("title", args.url), data.get("id")))
        return 0
    finally:
        ctx.pop()


def cmd_poll(args):
    """Re-fetch feeds and store any new entries."""
    from .models import Feed

    app, ctx = _app()
    try:
        q = Feed.query
        if args.id:
            q = q.filter_by(id=args.id)
        polled = 0
        client = app.test_client()
        for feed in q.all():
            resp = client.post("/api/feeds", json={"url": feed.url})
            if resp.status_code in (200, 409):
                polled += 1
                print("polled %s" % feed.url)
            else:
                print("!! %s -> %s" % (feed.url, resp.status_code))
        print("%d feed(s) polled" % polled)
        return 0
    finally:
        ctx.pop()


def cmd_entries(args):
    from .models import Entry

    app, ctx = _app()
    try:
        q = Entry.query
        if args.unread:
            q = q.filter_by(read=0)
        if args.starred:
            q = q.filter_by(starred=1)
        if args.feed:
            q = q.filter_by(feed_id=args.feed)
        rows = q.order_by(Entry.id.desc()).limit(args.limit).all()
        if args.json:
            import json

            print(
                json.dumps(
                    [
                        {
                            "id": e.id,
                            "title": e.title,
                            "url": e.url,
                            "read": bool(e.read),
                            "starred": bool(e.starred),
                        }
                        for e in rows
                    ]
                )
            )
            return 0
        if not rows:
            print("no entries match")
            return 0
        for e in rows:
            flag = "*" if e.starred else (" " if e.read else "o")
            print("%s %-4s %-60s %s" % (flag, e.id, (e.title or "")[:60], (e.url or "")[:50]))
        return 0
    finally:
        ctx.pop()


def cmd_mark(args):
    from .models import Entry, db

    app, ctx = _app()
    try:
        entry = db.session.get(Entry, args.id)
        if entry is None:
            print("no entry with id=%s" % args.id, file=sys.stderr)
            return 1
        if args.what == "read":
            entry.read = 1
        elif args.what == "unread":
            entry.read = 0
        elif args.what == "star":
            entry.starred = 1
        elif args.what == "unstar":
            entry.starred = 0
        db.session.commit()
        print("entry %s -> %s" % (entry.id, args.what))
        return 0
    finally:
        ctx.pop()


def cmd_search(args):
    from .agg.search import search

    app, ctx = _app()
    try:
        rows = search(args.query)
        if args.json:
            import json

            print(json.dumps(rows))
            return 0
        if not rows:
            print("no matches for %r" % args.query)
            return 0
        for row in rows:
            print(
                "%-4s %-60s %s"
                % (row.get("id"), (row.get("title") or "")[:60], (row.get("url") or "")[:50])
            )
        return 0
    finally:
        ctx.pop()


def cmd_opml_import(args):
    from .agg.opml import parse_opml

    app, ctx = _app()
    try:
        with open(args.file, encoding="utf-8") as fh:
            feeds = parse_opml(fh.read())
        print("parsed %d feed(s) from %s" % (len(feeds), args.file))
        for feed in feeds:
            print("  %-42s %s" % (feed.get("url", "")[:42], feed.get("title", "")))
        return 0
    finally:
        ctx.pop()


def cmd_opml_export(args):
    from .agg.opml import export_opml
    from .models import Feed

    app, ctx = _app()
    try:
        feeds = [{"url": f.url, "title": f.title, "category": f.category} for f in Feed.query.all()]
        text = export_opml(feeds)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(text)
            print("wrote %d feed(s) to %s" % (len(feeds), args.out))
        else:
            print(text)
        return 0
    finally:
        ctx.pop()


def cmd_serve(args):
    from ._app import app

    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="cli.py",
        description="rssagg - self-hosted RSS aggregator with full-text search",
        epilog="Environment: RSSAGG_DB_URI and RSSAGG_SECRET_KEY override the database\n"
        "URI and the Flask secret. See README.md.",
    )
    sub = p.add_subparsers(dest="cmd", metavar="<command>")

    s = sub.add_parser("feeds", help="list subscribed feeds")
    s.add_argument("--json", action="store_true", help="emit JSON")
    s.set_defaults(func=cmd_feeds)

    s = sub.add_parser("add", help="subscribe to a feed URL")
    s.add_argument("url", help="feed URL (RSS or Atom)")
    s.add_argument("--category", default="", help="optional category label")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("poll", help="re-fetch feeds and store new entries")
    s.add_argument("--id", type=int, default=None, help="poll only this feed id")
    s.set_defaults(func=cmd_poll)

    s = sub.add_parser("entries", help="list stored entries")
    s.add_argument("--limit", type=int, default=20, help="max rows (default 20)")
    s.add_argument("--feed", type=int, default=None, help="filter by feed id")
    s.add_argument("--unread", action="store_true", help="only unread entries")
    s.add_argument("--starred", action="store_true", help="only starred entries")
    s.add_argument("--json", action="store_true", help="emit JSON")
    s.set_defaults(func=cmd_entries)

    s = sub.add_parser("mark", help="mark an entry read/unread/starred")
    s.add_argument("id", type=int, help="entry id")
    s.add_argument("what", choices=["read", "unread", "star", "unstar"], help="state to apply")
    s.set_defaults(func=cmd_mark)

    s = sub.add_parser("search", help="full-text search entries")
    s.add_argument("query", help="search terms")
    s.add_argument("--json", action="store_true", help="emit JSON")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("opml-import", help="parse an OPML subscription list")
    s.add_argument("file", help="path to an .opml file")
    s.set_defaults(func=cmd_opml_import)

    s = sub.add_parser("opml-export", help="export subscriptions as OPML")
    s.add_argument("--out", default="", help="write to this file instead of stdout")
    s.set_defaults(func=cmd_opml_export)

    s = sub.add_parser("serve", help="run the web UI")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=5000)
    s.add_argument("--debug", action="store_true")
    s.set_defaults(func=cmd_serve)

    return p


def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)
    if not getattr(args, "cmd", None):
        p.print_help()
        return 0
    return args.func(args) or 0
