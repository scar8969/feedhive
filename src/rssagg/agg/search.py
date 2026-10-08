def search(q, limit=50):
    """FTS5 over entries (title + content); falls back to LIKE if FTS5 is missing."""
    from ..models import Entry, db
    q = (q or "").strip()
    if not q:
        return []
    ids = []
    try:
        db.session.execute(db.text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS entry_fts USING fts5(title, content)"))
        db.session.execute(db.text(
            "INSERT INTO entry_fts(rowid, title, content) "
            "SELECT id, title, content FROM entries WHERE id NOT IN (SELECT rowid FROM entry_fts)"))
        db.session.commit()
        rows = db.session.execute(db.text(
            "SELECT rowid FROM entry_fts WHERE entry_fts MATCH :q LIMIT :lim"),
            {"q": q, "lim": limit}).fetchall()
        ids = [r[0] for r in rows]
    except Exception:
        db.session.rollback()
        ids = []
    if ids:
        entries = Entry.query.filter(Entry.id.in_(ids)).limit(limit).all()
    else:
        like = "%" + q + "%"
        entries = Entry.query.filter(
            db.or_(Entry.title.like(like), Entry.content.like(like))).limit(limit).all()
    return [{"id": e.id, "title": e.title, "url": e.url, "feed_id": e.feed_id} for e in entries]
