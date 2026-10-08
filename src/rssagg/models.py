from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Feed(db.Model):
    __tablename__ = "feeds"
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(512), unique=True)
    title = db.Column(db.String(256), default="")
    category = db.Column(db.String(64), default="")
    etag = db.Column(db.String(128), default="")
    last_poll = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Entry(db.Model):
    __tablename__ = "entries"
    id = db.Column(db.Integer, primary_key=True)
    feed_id = db.Column(db.Integer, db.ForeignKey("feeds.id"), index=True)
    guid = db.Column(db.String(256), unique=True)
    title = db.Column(db.String(512), default="")
    url = db.Column(db.String(1024), default="")
    content = db.Column(db.Text, default="")
    read = db.Column(db.Integer, default=0)
    starred = db.Column(db.Integer, default=0)
    published_at = db.Column(db.DateTime, nullable=True)
