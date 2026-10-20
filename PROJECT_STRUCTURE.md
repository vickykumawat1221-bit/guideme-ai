# Project Structure

```
guideme-ai/
├── .vscode/settings.json
├── .gitignore
├── CONTRIBUTING.md
├── PROJECT_STRUCTURE.md
├── README.md
├── start.sh                       # Django API + static frontend
├── django-backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── db.sqlite3                 # seeded demo database
│   ├── guideme_backend/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── settings.py            # env-driven settings
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── api/
│       ├── __init__.py
│       ├── admin.py               # admin registrations
│       ├── ai.py                  # hybrid semantic + keyword ranker
│       ├── apps.py
│       ├── migrations/
│       │   ├── 0001_initial.py
│       │   └── 0002_*.py
│       ├── models.py              # Expert, Review, Booking, AuthToken
│       ├── tests.py               # 17 API tests
│       ├── urls.py
│       ├── views.py
│       └── management/
│           └── commands/
│               └── seed_demo.py   # idempotent demo data
└── frontend/
    ├── index.html                 # single-page app (no build step)
    ├── newwwwww.html              # legacy entry point → redirects
    └── images/
        └── README.md
```

## Layers

- **Frontend** (`frontend/index.html`) — HTML/CSS/vanilla JS. Talks to the API over
  `fetch`; all business logic lives server-side.
- **API** (`django-backend/api/`) — Django views returning JSON, with manual CORS headers
  so the static frontend can be served from any origin.
- **AI** (`api/ai.py`) — sentence-transformer embeddings when available, with a
  keyword/category/rating fallback.
- **Data** (`api/models.py`) — SQLite in development. `Booking` references `Expert`
  (nullable so historic rows stay valid) and `Review` rolls up to an average rating.

## Request flow

```
browser → index.html
        → POST /api/recommend/  → ai.rank_experts() → Expert + Review rows
        → POST /api/bookings/   → Booking row + reference
        → GET  /api/analytics/  → aggregates over Booking/Review/Expert
```
