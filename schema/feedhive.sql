-- 📰 rssagg schema
CREATE TABLE feeds(id INTEGER PRIMARY KEY, url TEXT UNIQUE, title TEXT, category TEXT, etag TEXT, last_poll DATETIME, created_at DATETIME);
CREATE TABLE entries(id INTEGER PRIMARY KEY, feed_id INTEGER REFERENCES feeds(id), guid TEXT UNIQUE, title TEXT, url TEXT, content TEXT, read INTEGER DEFAULT 0, starred INTEGER DEFAULT 0, published_at DATETIME);
