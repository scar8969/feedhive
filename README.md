<p align="center">
  <img src="docs/assets/screens/root.png" alt="feedhive running" width="900">
</p>

<h1 align="center">feedhive</h1>

<p align="center"><b>Subscribe by URL, poll on a schedule, read and search in one place.</b></p>

<p align="center">
  <a href="#quality-gates"><img src="https://img.shields.io/badge/tests-22%20passed-2ea44f" alt="tests: 22 passed"></a> <a href="#quality-gates"><img src="https://img.shields.io/badge/coverage-44.5%-yellow" alt="coverage: 44.5%"></a> <a href="#api"><img src="https://img.shields.io/badge/routes-12%20answered-0969da" alt="routes: 12 answered"></a> <a href="#requirements"><img src="https://img.shields.io/badge/python-3.11%2B-3776ab" alt="python: 3.11+"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f" alt="license: MIT"></a>
</p>

feedhive fetches the feeds you add, parses them with feedparser, deduplicates entries by GUID, and gives you read/star state, search and OPML import/export.

---

**Contents** &nbsp;·&nbsp; [Why](#why-this-exists) &nbsp;·&nbsp; [What it does](#what-it-does) &nbsp;·&nbsp; [Quickstart](#quickstart) &nbsp;·&nbsp; [API](#api) &nbsp;·&nbsp; [Screenshots](#screenshots) &nbsp;·&nbsp; [Measured](#measured-not-estimated) &nbsp;·&nbsp; [Architecture](#architecture) &nbsp;·&nbsp; [Quality gates](#quality-gates) &nbsp;·&nbsp; [Deploy](#deploy) &nbsp;·&nbsp; [Limits](#limits-stated-rather-than-hidden)

## Why this exists

Feed readers rot when they lose your read state or duplicate entries on every poll. Keying entries by GUID and storing read/star as rows makes polling idempotent, which is the whole game.

## What it does

| Capability | How it works |
| --- | --- |
| **Idempotent polling** | Entries are keyed by GUID, so a repeated poll inserts nothing. |
| **Read and star state** | Per-entry flags with dedicated routes for toggling them. |
| **Search** | Full-text-ish search across titles and summaries. |
| **OPML in and out** | Move a subscription list between this and any other reader. |
| **CLI** | add, poll, entries, mark, search, opml-import, opml-export. |

## Quickstart

```sh
git clone https://github.com/scar8969/feedhive.git
cd feedhive
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python wsgi.py                                 # http://127.0.0.1:8000
```

The same work from the CLI:

```sh
python -m rssagg.cli --help
```

Commands: `feeds`, `add`, `poll`, `entries`, `mark`, `search`, `opml-import`, `opml-export`, `serve`.

A first request:

```sh
curl -s http://127.0.0.1:8000/api/feeds | head
```

## Requirements

- Python **3.11+** — CI runs 3.11, 3.12 and 3.13.
- Runtime dependencies: `Flask>=3.0`, `Flask-SQLAlchemy>=3.1`, `SQLAlchemy>=2.0`, `PyYAML>=6.0`, `feedparser`.
- No JavaScript build step: every page is server-rendered Jinja.

## API

Every route below is in [`openapi/feedhive.yaml`](openapi/feedhive.yaml) and is exercised by the live probe recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/api/feeds` | list |
| `POST` | `/api/feeds` | add feed |
| `GET` | `/api/entries` | entries |
| `POST` | `/api/entries/<id>/read` | mark read |
| `POST` | `/api/entries/<id>/star` | star |
| `GET` | `/api/search` | search |

## Screenshots

Captured from the running service with headless Chromium at 1440×900, one image per page, committed under [`docs/assets/screens/`](docs/assets/screens/).

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/feeds.png" alt="/feeds" width="100%"><br><sub><code>/feeds</code> &middot; 47.1 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/healthz.png" alt="/healthz" width="100%"><br><sub><code>/healthz</code> &middot; 8.3 KB</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/livez.png" alt="/livez" width="100%"><br><sub><code>/livez</code> &middot; 7.3 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/metrics.png" alt="/metrics" width="100%"><br><sub><code>/metrics</code> &middot; 14.8 KB</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/readyz.png" alt="/readyz" width="100%"><br><sub><code>/readyz</code> &middot; 7.7 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/version.png" alt="/version" width="100%"><br><sub><code>/version</code> &middot; 25.7 KB</sub></td>
</tr>
</table>

## Measured, not estimated

These numbers were produced on this checkout by `pytest --cov` and by booting `wsgi.py` and issuing one real GET per documented path. The commands are in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Signal | Value |
| --- | --- |
| Tests | **22 / 22 passed** (1.9 s, exit 0) |
| Line coverage | **44.5%** — 446 of 907 statements |
| Source | 15 files / 1,820 lines |
| Test code | 4 files / 233 lines |
| Documented paths | 5 in the spec, 3 GET |
| Live probe | 12 GET requests to the booted app, **12 answered 200** |
| Median latency | **5.5 ms** (single uncached request, dev server) |
| Slowest / fastest | 112.9 ms `/` / 4.2 ms `/readyz` |
| Bytes served | 13.4 KB across 12 responses |
| Screenshots | 7 captured |

## Architecture

```
feedhive/
├── src/rssagg/
│   ├── http.py                         379  HTTP plumbing for rssagg: correlation ids, access lo
│   ├── cli.py                          307  rssagg CLI - manage feeds and entries from the termi
│   ├── _app.py                         262  
│   ├── config.py                       173  Environment-driven configuration for rssagg
│   ├── observability.py                169  Structured logging and request correlation for rssag
│   ├── agg/api.py                      131  
│   ├── app.py                          119  Application factory for rssagg
│   ├── errors.py                       108  Typed application errors and their HTTP mapping for 
│   ├── paths.py                         52  Filesystem layout for rssagg
│   ├── agg/search.py                    38  
│   ├── agg/fetcher.py                   32  
│   ├── models.py                        30  
├── openapi/feedhive.yaml                  the contract of record
├── schema/feedhive.sql                    the DDL
├── tests/                       the suite that has to stay green
├── docs/EVIDENCE.md             the recorded live route walk
├── Dockerfile                   multi-stage build
└── wsgi.py                      entry point
```

The package keeps one shape across the service: `config.py` reads the environment once, `observability.py` emits structured JSON logs carrying a request id, `errors.py` turns exceptions into a single JSON envelope, `models.py` holds the tables, and the `agg/` package holds the routes.

## Quality gates

| Gate | Command | Threshold |
| --- | --- | --- |
| Suite | `pytest -q` | all green |
| Coverage | `pytest --cov` | floor set in `pyproject.toml` from the measured value |
| Lint | `ruff check src tests` | zero findings |
| Format | `ruff format --check src tests` | zero reformats |
| Types | `mypy src` | zero errors |
| Security | `bandit -c pyproject.toml -r src` | reviewed skip list, no unreviewed finding |
| Live routes | boot `wsgi.py`, one GET per documented path | no 5xx, no undocumented guard |

CI runs the first six on Python 3.11, 3.12 and 3.13 for every push to `main`, plus a container build. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Deploy

```sh
docker build -t feedhive .
docker run --rm -p 8000:8000 --env-file .env.example feedhive
```

Configuration is environment-only — every variable is documented in [`.env.example`](.env.example), and the service refuses to start with a production secret missing.

## Limits, stated rather than hidden

- Fetches on demand or on a CLI poll; the scheduler is opt-in.
- Feed parsing depends on feedparser, which is vendored only for the offline test host.

## License

MIT — see [LICENSE](LICENSE).
