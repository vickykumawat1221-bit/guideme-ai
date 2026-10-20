# Contributing Guide

## Prerequisites

- Python 3.12+
- Git
- pip

## Setup

1. Clone the repository.
2. Install dependencies:

   ```bash
   cd django-backend
   python3 -m pip install -r requirements.txt
   ```

3. Apply migrations:

   ```bash
   python3 manage.py migrate
   ```

4. Seed the demo data (idempotent):

   ```bash
   python3 manage.py seed_demo
   ```

5. Run the API and the frontend:

   ```bash
   # terminal 1
   python3 manage.py runserver 127.0.0.1:8000

   # terminal 2
   cd ../frontend && python3 -m http.server 5501 --bind 127.0.0.1
   ```

Open http://127.0.0.1:5501/index.html.

## Tests

```bash
cd django-backend
python3 manage.py test api
```

Please keep the suite green and add a test for every new endpoint or permission rule.

## Branch naming

- `feature/...`
- `bugfix/...`
- `docs/...`

## Commit messages

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `test: ...`
- `refactor: ...`

## Code style

- Backend: Django conventions, small view helpers, no business logic in templates.
- Frontend: keep `index.html` dependency-free; escape all user-provided text before
  inserting it into the DOM.
- Do not commit real secrets. `DJANGO_SECRET_KEY` is read from the environment.
