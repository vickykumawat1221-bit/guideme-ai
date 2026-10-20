# 🤖 GuideMeAI

**GuideMeAI** is an AI-powered expert consultation platform. Users describe a problem in
plain language, and GuideMe ranks real experts using a hybrid of semantic search,
category detection, keyword overlap, community ratings and experience — then explains
*why* each expert was matched. Users can read reviews, book a consultation and track it
from request to completion.

Built for a hackathon, engineered like a product.

---

## ✨ Features

### For users
- 🔐 **Accounts** — register / sign in with token auth (guest browsing still works).
- 🧠 **Explainable AI matching** — every recommendation carries a 0–100 match score and a
  "why this match" reason (category, experience, rating, matched keywords, languages).
- 🗂️ **Category detection** — the ranker infers Health, Career, Fitness, Beauty, Education,
  Finance, Legal, Technology or Wellness from free text.
- 🤖 **Guided assistant** — a chat widget that classifies intent, suggests experts and asks
  a useful follow-up question.
- 🔍 **Search, filter and sort** experts by category, rating, experience, price or name.
- ⭐ **Reviews & ratings** — real aggregated ratings, rating distribution and one-review-per-user
  updates.
- 📅 **Bookings 2.0** — communication method, urgency, preferred slot, status lifecycle
  (`pending → confirmed → completed / cancelled`) and a shareable reference such as `GM-261020-A1B2`.
- 📊 **Live insights** — bookings per day, status donut, top-rated experts and category mix.

### For experts and admins
- 👤 **Publish an expert profile** (auth required; the creator becomes the owner).
- 🛠️ **Manage profiles** — owners and staff can edit or delete profiles; nobody else can.
- ✅ **Booking workflow** — staff/expert owners can confirm and complete bookings; users can cancel.

### Engineering
- 🧪 **17 Django tests** covering auth, permissions, reviews, ranking, bookings and analytics.
- 🛡️ **Graceful AI fallback** — if the embedding model cannot load (offline venue Wi-Fi,
  missing torch), ranking degrades to keyword/category signals instead of failing.
- 🌐 **Zero-build frontend** — one `index.html`, no npm step, responsive and accessible.
- 🔌 **API-first** — every screen is backed by a JSON endpoint; no client-side business logic.

---

## 🛠️ Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12+, Django 6 |
| AI/ML | sentence-transformers (`all-MiniLM-L6-v2`), scikit-learn, NumPy |
| Database | SQLite (dev) — swap `DATABASES` for Postgres in production |
| Frontend | HTML, CSS, vanilla JavaScript (no build step) |
| Auth | Bearer tokens stored in `AuthToken` |

> The original README mentioned Flask and MySQL. The actual, current implementation is
> Django + SQLite; this document reflects the code.

---

## 🚀 Run it

```bash
./start.sh
```

Then open **http://127.0.0.1:5501/index.html**.

The script installs dependencies on a fresh checkout, runs migrations, seeds demo data,
starts the Django API on `:8000` and serves the frontend on `:5501`.

Override ports if needed:

```bash
BACKEND_PORT=9000 FRONTEND_PORT=5181 ./start.sh
```

### Manual setup

```bash
cd django-backend
python3 -m pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py seed_demo
python3 manage.py runserver 127.0.0.1:8000

# in another terminal
cd frontend
python3 -m http.server 5501 --bind 127.0.0.1
```

### Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Staff / demo admin | `demo@guideme.ai` | `demo12345` |

The sign-in modal has a **Use demo account** button that fills these in.

---

## 🧠 How the ranking works

`api/ai.py` builds a text profile for each expert (name, profession, category, bio,
languages) and scores the query with:

| Signal | Weight (semantic available) | Weight (fallback) |
| --- | --- | --- |
| Sentence-embedding cosine similarity | 45% | — |
| Keyword overlap | 25% | 50% |
| Category match | 15% | 20% |
| Average rating | 10% | 20% |
| Experience (capped at 15 yrs) | 5% | 10% |

Scores are returned as `match_score` (0–100) with a human-readable `match_reason`.
Set `GUIDEME_DISABLE_EMBEDDINGS=1` to force the keyword/category fallback.

---

## 🔌 API reference

Base URL: `http://127.0.0.1:8000/api/`

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health/` | — | API + AI mode status |
| `POST` | `/auth/register/` | — | Create account, returns bearer token |
| `POST` | `/auth/login/` | — | Sign in, returns bearer token |
| `GET` | `/auth/me/` | ✅ | Current user and activity counts |
| `POST` | `/auth/logout/` | ✅ | Revoke token |
| `GET` | `/experts/` | — | List experts (`q`, `category`, `sort`) |
| `POST` | `/experts/` | ✅ | Publish an expert profile |
| `GET` | `/experts/<id>/` | — | Expert detail + recent reviews |
| `PATCH` / `DELETE` | `/experts/<id>/` | ✅ owner/staff | Edit or delete a profile |
| `GET` | `/experts/<id>/reviews/` | — | Reviews, average and distribution |
| `POST` | `/experts/<id>/reviews/` | optional | Create or update your review |
| `POST` | `/recommend/` | optional | Hybrid AI ranking |
| `POST` | `/assistant/` | optional | Guided chat response + suggestions |
| `GET` | `/bookings/` | ✅ | Your bookings (staff sees all) |
| `POST` | `/bookings/` | optional | Request a booking, returns reference |
| `PATCH` / `DELETE` | `/bookings/<id>/` | ✅ | Update status / remove booking |
| `GET` | `/analytics/` | — | Aggregated platform insights |

Authenticate with either header:

```http
Authorization: Bearer <token>
X-Auth-Token: <token>
```

### Example

```bash
curl -s http://127.0.0.1:8000/api/recommend/ \
  -H 'Content-Type: application/json' \
  -d '{"question": "I feel burnt out and cannot sleep"}' | python3 -m json.tool
```

---

## 🧪 Tests

```bash
cd django-backend
python3 manage.py test api
```

The suite uses an in-memory test database and mocks the embedding model, so it runs in
about a second and does not need network access.

---

## 📁 Project structure

```
guideme-ai/
├── start.sh                     # one-command demo runner
├── django-backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── db.sqlite3               # committed demo data (seeded)
│   ├── guideme_backend/         # settings, root URLs, WSGI/ASGI
│   └── api/
│       ├── ai.py                # hybrid ranker + category detection
│       ├── models.py            # Expert, Review, Booking, AuthToken
│       ├── views.py             # JSON API
│       ├── urls.py
│       ├── admin.py
│       ├── tests.py
│       ├── migrations/
│       └── management/commands/seed_demo.py
└── frontend/
    ├── index.html               # the app
    ├── newwwwww.html            # legacy filename → redirects to index.html
    └── images/
```

---

## 🔒 Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | dev-only value | Set a real secret in production |
| `DJANGO_DEBUG` | `True` | Set `False` in production |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost,0.0.0.0,testserver` | Comma-separated hosts |
| `GUIDEME_DISABLE_EMBEDDINGS` | unset | `1` forces keyword-only ranking |
| `BACKEND_PORT` / `FRONTEND_PORT` | `8000` / `5501` | `start.sh` ports |

The frontend API origin can be overridden in the browser console with
`localStorage.setItem("gm_api", "https://your-api.example.com")`.

---

## 🗺️ Roadmap

- [ ] Video consultations (WebRTC)
- [ ] Payments and invoicing
- [ ] Email/SMS notifications for booking status
- [ ] Multi-language UI
- [ ] Postgres + object storage for production
- [ ] LLM-backed assistant with retrieval over expert bios

---

## 👨‍💻 Team

- Vikash Kumawat
- Yashaswi
- Varun Choudhary
- Vidhi Chatterjee
