== curl ==
# POST /api/feeds  {"url":"https://news.ycombinator.com/rss","category":"tech"}
# GET  /api/feeds
# GET  /api/entries?feed=1&unread=1
# POST /api/entries/1/read | /star
# GET  /api/search?q=postgres

== session plan ==
# Session 1: fetcher (fixture + etag) + opml → tests
# Session 2: api (feeds/entries/read/star) + search FTS5 → tests
# Session 3: web templates (reader) → screenshots → README → CI/Docker/Pages → tag
