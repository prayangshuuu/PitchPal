# PitchPal Testing Guide

## 1. Current implementation status

Before using this guide, know what actually exists in the codebase today so expectations
match reality:

| Layer | Status |
|---|---|
| Models (`api/models.py`) | Implemented: `User`, `Session`, `Question`, `Answer`, `Evaluation`, `ProgressMetric` |
| Admin (`api/admin.py`) | Implemented |
| Gemini service (`api/services/gemini_service.py`) | Implemented: `generate_interview_questions`, `evaluate_answer`, `generate_pitch_feedback`, with fallback behavior when `GEMINI_API_KEY` is missing or the API call fails |
| Cache service (`api/services/cache_service.py`) | Implemented: `cache_response`, `get_cached_response`, `clear_cache` |
| REST API (serializers/ViewSets) | **Not implemented.** `djangorestframework` is installed but unused — no serializers, no ViewSets. |
| URL routing | **Not implemented.** `pitchpal/urls.py` only registers `admin/`. There is no `api/urls.py`. |
| Views (`api/views.py`) | **Empty** — placeholder file only. |
| Authentication views | **Not implemented.** Templates reference `/auth/login/`, `/auth/signup/` but nothing serves those routes. |
| Frontend templates (`api/templates/api/*.html`) | Present (login, signup, home, session start/practice/results, progress dashboard) but **unwired** — no view renders them, untracked in git. |
| Demo data | **Not implemented.** No seed command or fixture. |

**Consequence:** this guide covers automated tests for models and the two service modules,
since that's the only code that currently exists to test. Section 7 is a punch list for
everything else, so the guide can be extended in place once those layers are built.

## 2. Environment setup verification

Checked while setting this up:

- **Python**: `pyproject.toml` requires `>=3.11`; the project venv runs 3.11.15. OK.
- **Postgres**: `.env` defines `DATABASE_URL=postgresql://postgres:hackathon@localhost:5432/pitchpal`.
  On this machine, no `postgres` role or `pitchpal` database existed locally (only a superuser
  role matching the OS username). Created both to match `.env`:
  ```sql
  CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'hackathon';
  CREATE DATABASE pitchpal OWNER postgres;
  ```
  If you're setting this up on a fresh machine, you'll need to do the same (or point
  `DATABASE_URL` at credentials that already exist).
- **Cache backend**: no `CACHES` setting in `pitchpal/settings.py`, so Django falls back to
  its default in-process `LocMemCache`. No Redis/Memcached needed for tests or local dev.
- **Secret found hardcoded**: `pitchpal/settings.py:28` hardcodes `SECRET_KEY =
  'django-insecure-...'` instead of reading `DJANGO_SECRET_KEY` from `.env` (which is defined
  there but never read). Not fixed here since this task was scoped to testing, not
  remediation — flagging it because "no hardcoded secrets" was an explicit requirement.
- **Deprecation warning**: `STATICFILES_STORAGE` is deprecated in Django 5.0 in favor of
  `STORAGES`. Tests still pass; noted for future cleanup.

## 3. Pytest setup

Three files were added/updated:

- **`pytest.ini`** — points pytest-django at `pitchpal.settings`, shows `print()` output
  (`-s`), and defines `unit` / `integration` / `e2e` / `slow` markers.
- **`conftest.py`** (repo root) — shared fixtures: `user`, `other_user`, `session`,
  `question`, `answer`, `evaluation` (a fully linked chain of DB fixtures), plus `api_client`
  (DRF `APIClient`) and `authenticated_client` (same, pre-authenticated as `user`). An
  autouse fixture clears the Django cache before/after every test so `cache_service` tests
  can't leak state into each other.
- **`pyproject.toml`** — added `faker==20.0.0` to the `dev` dependency group (alongside the
  existing `pytest==7.4.3` and `pytest-django==4.7.0`).

`api_client` / `authenticated_client` don't have anything to hit yet (see Section 1), but
they're ready for when the API layer exists.

### Running tests

```bash
uv sync --dev              # install pytest, pytest-django, faker
uv run pytest              # run everything
uv run pytest -v           # verbose, one line per test
uv run pytest -m unit      # only fast/isolated tests
uv run pytest -m "not slow"  # skip the TTL-expiration test (real ~1.5s sleep)
uv run pytest api/tests/test_models.py -k TestEvaluationModel  # scope to one class
```

Current result: **63 passed**, 0 failed.

## 4. Database model tests — `api/tests/test_models.py`

Covers every model in `api/models.py`:

- **User**: creation with email/password, email
  uniqueness (`IntegrityError` on duplicate), `__str__` returns email, timestamps auto-set,
  password is hashed (`check_password` round-trips, raw password never stored).
- **Session**: creation with all fields, FK to `User` and reverse `user.sessions`, choice
  validation via `full_clean()` (choices aren't DB-enforced — only checked on `full_clean`/
  forms, so tests exercise that explicitly), `overall_score` nullable, timestamps, `-created_at`
  ordering.
- **Question**: creation linked to `Session`, `question_number` 1–5 (documented via test, not
  DB-enforced — there's no upper/lower bound validator on the field), category choice
  validation, `related_name='questions'`, `__str__` format (`"Q{number}: {text[:50]}"`).
- **Answer**: creation linked to `Question`, `user_text`, `submitted_at` auto-set,
  `related_name='answers'`.
- **Evaluation**: creation linked to `Answer`, one-to-one enforcement (`IntegrityError` on a
  second `Evaluation` for the same `Answer`), score fields, feedback text, and a round-trip
  test for `strengths`/`improvements` — these are plain `TextField`s in the schema, not JSON
  fields, so the app is responsible for `json.dumps`/`json.loads` on the way in/out; the test
  exercises that pattern rather than assuming DB-level JSON support.
- **ProgressMetric**: creation, `unique_together=('user','role','mode')` enforcement
  (`IntegrityError` on duplicate, but same role with a different mode is allowed),
  `sessions_completed` counter increments, `average_score` calculation, `best_score`/
  `worst_score`, `last_practiced` timestamp.

## 5. Gemini service tests — `api/tests/test_gemini_service.py`

No real network calls are made — `google.generativeai.GenerativeModel` is monkeypatched with
a `MagicMock` per test, and `GEMINI_API_KEY` is set/unset via `monkeypatch.setenv`/`delenv`.

- **`generate_interview_questions`**: returns a list of `{id, text, category}` dicts on
  success; count is respected when the mocked response honors it, and the prompt is asserted
  to contain the requested count; falls back to `_get_fallback_questions` when the API key is
  missing, when the SDK call raises, and when the response isn't valid JSON; fallback
  question sets are verified to exist (5 questions each, correct shape) for every
  `{sde,pm,designer} × {junior,mid,senior}` combination, plus the generic fallback for an
  unrecognized role.
- **`evaluate_answer`**: verifies the full response shape (`score`, `clarity_score`,
  `depth_score`, `communication_score`, `feedback`, `strengths`, `improvements`) on success,
  each score within 0–100, `feedback` a string, `strengths`/`improvements` lists; on missing
  key or SDK exception, asserts the exact generic fallback (`score: 50`, empty lists) with all
  fields still present.
- **`generate_pitch_feedback`**: same pattern — shape and score-range check on success,
  `score: 50` generic fallback on missing key or SDK exception.

## 6. Cache service tests — `api/tests/test_cache_service.py`

- `cache_response` → `get_cached_response` round-trip returns the same value.
- Missing key returns `None`.
- `clear_cache` removes an entry (and doesn't raise on a key that was never set).
- TTL expiration (marked `@pytest.mark.slow`, real `time.sleep(1.5)` against a 1s TTL) —
  confirms an expired key returns `None`. Skip with `-m "not slow"` for a fast local loop.

## 7. What's not testable yet, and why

These were in the original test spec but have no implementation to test against. Each entry
lists what needs to exist first.

### REST API (`SessionViewSet` etc.)
Needs: DRF serializers for `Session`/`Question`/`Answer`/`Evaluation`/`ProgressMetric`, a
`SessionViewSet` (or equivalent view), and `api/urls.py` wired into `pitchpal/urls.py` under
e.g. `/api/`. Once that exists, `api_client`/`authenticated_client` from `conftest.py` are
ready to drive `POST /api/sessions/`, assert `201` + response shape, and confirm DB rows were
created — mirroring the model-fixture chain already in `conftest.py`.

### Authentication
Needs: login/signup/logout views handling `/auth/login/`, `/auth/signup/`, `/auth/logout/`
(the templates already `POST` to these paths) and routes registered in `pitchpal/urls.py`.
Once built, tests should cover: successful login sets a session, wrong password rejected,
duplicate-email signup rejected, logout clears the session, and that session/auth state
gates `/dashboard/` and `/sessions/start/`.

### Frontend templates
Needs: views that render `home.html`, `session_start.html`, `session_practice.html`,
`session_results.html`, `progress_dashboard.html` with real context, plus the routes above.
Once wired, use Django's test `Client` to assert `200` responses, correct template used
(`assertTemplateUsed`), and that context variables (`recent_sessions`, `avg_score`,
`top_role`) render as expected. Manual browser verification (golden path + HTMX partial
swaps in `session_practice.html`) should follow per this project's usual UI-testing practice
before calling any frontend work done.

### Demo data
Needs: a management command (e.g. `seed_demo_data`) or fixture file that creates a demo user
with a few completed sessions/questions/answers/evaluations across roles. Once it exists, a
test should run the command against a test DB and assert the expected row counts and that
`ProgressMetric` aggregates come out consistent with the seeded `Evaluation` scores.

### Manual testing (curl/Postman, browser)
Not usable yet — there's no server route to hit beyond `/admin/`. Once the above are wired
up, this section should get concrete `curl` examples per endpoint and a browser checklist
(signup → login → start session → answer questions → view results → check dashboard).

## 8. What you can manually verify today

- `uv run python manage.py check` — Django system check, no errors.
- `uv run python manage.py makemigrations --check` — confirms no drifted model state.
- `uv run python manage.py createsuperuser` then `uv run python manage.py runserver` and
  visit `/admin/` — confirms the admin site renders and all six models
  (User/Session/Question/Answer/Evaluation/ProgressMetric) are registered and browsable, with
  the search/filter/readonly configuration from `api/admin.py`.
- `uv run python manage.py shell` — exercise `gemini_service.generate_interview_questions(...)`
  live against the real Gemini API if `GEMINI_API_KEY` is set in `.env`, to sanity-check the
  fallback path matches the automated tests.
