# Lesson 26 — Users REST API (FastAPI)

A small CRUD REST API for managing users, built with **FastAPI** and **SQLAlchemy**. It is a deliberate, feature-for-feature port of the Lesson 24 Flask-RESTful API to FastAPI, so the differences between the two frameworks are easy to see. The domain (users) is held constant on purpose; only the framework changes.

For the deeper Flask-vs-FastAPI walkthrough and concept notes (dependency injection, Pydantic, the auto docs), see [LEARNING_NOTES.md](./LEARNING_NOTES.md).

## What it does

Stores users (`id`, `name`, `email`) in a local SQLite database and exposes full create/read/update/delete over HTTP. Input is validated by Pydantic; output is shaped by Pydantic response models; missing records return `404`.

## Endpoints

| Method | Path | Description | Success | Notes |
|--------|------|-------------|---------|-------|
| GET | `/` | Health/home message | 200 | Returns `{"message": "FastAPI REST API"}` |
| GET | `/api/users/` | List all users | 200 | Returns `[]` when empty |
| POST | `/api/users/` | Create a user | 201 | JSON body `{ "name", "email" }`; returns the created user |
| GET | `/api/users/{id}` | Get one user by id | 200 | `404` if the id doesn't exist |
| PATCH | `/api/users/{id}` | Update a user | 200 | Requires both `name` and `email`; `404` if not found |
| DELETE | `/api/users/{id}` | Delete a user | 200 | Returns the remaining users; `404` if not found |

`name` and `email` are required and unique. A request body missing a required field returns `422` with a Pydantic validation error (no hand-written validation code).

## Tech stack

- **FastAPI** — routing, request/response handling
- **SQLAlchemy 2.0** — ORM and SQLite engine (wired by hand, not via Flask-SQLAlchemy)
- **Pydantic 2** — input validation (`UserCreate`) and output shaping (`UserOut`)
- **Uvicorn** — ASGI server
- **pytest** + **httpx** — tests via FastAPI's `TestClient`
- Python 3.12, SQLite

## Setup

From the `Lesson26/` directory, create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Running

```bash
.venv/bin/uvicorn main:app --reload
```

- `main` is the file (`main.py`), `app` is the `FastAPI()` instance, `--reload` restarts on code changes.
- The SQLite file `database.db` is created automatically on startup (it is gitignored).

Then open:

- `http://localhost:8000/api/users/` — the API
- `http://localhost:8000/docs` — interactive Swagger UI, generated automatically from the type hints
- `http://localhost:8000/redoc` — the same API documented in an alternate layout

You can create, read, update, and delete users directly from the `/docs` page using "Try it out."

## Testing

```bash
.venv/bin/python -m pytest test_main.py -v
```

11 tests cover the home route and full CRUD, including the `422` validation case and the `404` not-found cases. The tests use a throwaway in-memory SQLite database via FastAPI's dependency override (`app.dependency_overrides[get_db]`), so they never touch `database.db`.

## Project layout

```
Lesson26/
  main.py            # the FastAPI app: models, schemas, routes
  test_main.py       # pytest suite (FastAPI TestClient)
  requirements.txt   # pinned dependencies
  LEARNING_NOTES.md  # Flask-vs-FastAPI concept notes
  README.md          # this file
```

## Scope

This is a learning project. It intentionally has no authentication, pagination, or migrations — it exists to demonstrate a clean FastAPI CRUD API and how it compares to the Flask version in Lesson 24.

---

*AI Masterclass artifact — Class 2. This README was delegated to an AI agent (Claude Code) as the Class 1 "delegate one task" homework, then reviewed by a human accuracy pass before publishing.*
