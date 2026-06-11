"""
Tests for main.py — the FastAPI users CRUD endpoints.

Same goal as Lesson 24's test_api.py: a "test client" that sends requests to our
app IN MEMORY (no real server, no network), asserting on status codes and JSON
bodies. FastAPI's TestClient (from Starlette, backed by httpx) plays the role
Flask's test_client did in Lesson 24.

THE PART THAT GOT EASY — an isolated database
---------------------------------------------
In Lesson 24 this was the hard, hacky bit. Flask-SQLAlchemy built its engine the
moment api.py was imported and refused to be re-pointed, so that test file had to
reach into a PRIVATE internal (db._app_engines[app][None]) to swap in a throwaway
database. (See Lesson24/test_api.py's docstring.)

Here it is one clean, supported line:

    app.dependency_overrides[get_db] = override_get_db

That is the entire payoff of dependency injection. Because every route asks for
its session via Depends(get_db) instead of grabbing a global, we just tell the
app "for the tests, hand them THIS session instead" — pointed at a private
in-memory database. main.py is never touched.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app, Base, get_db

# A throwaway in-memory database, separate from the real database.db.
# StaticPool keeps a single shared connection so the in-memory db survives across
# requests within a test (otherwise each new connection gets its own blank db).
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# The one line Lesson 24 needed an internal-poke for: swap the dependency.
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    # Fresh, empty tables for THIS test; dropped afterward so tests don't leak
    # state into each other.
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def make_user(client, name="Ada", email="ada@example.com"):
    """Helper: POST a user and return the response."""
    return client.post("/api/users/", json={"name": name, "email": email})


# ---------- the home page ----------

def test_home_route(client):
    resp = client.get("/")
    assert resp.status_code == 200
    # FastAPI route returns a dict; TestClient parses JSON via resp.json().
    assert resp.json() == {"message": "FastAPI REST API"}


# ---------- the collection: /api/users/ ----------

def test_get_users_empty_to_start(client):
    resp = client.get("/api/users/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_post_creates_a_user(client):
    resp = make_user(client, "Ada", "ada@example.com")

    # Unlike Lesson 24 (which returned the whole list), create_user returns the
    # single created user. 201 = "Created".
    assert resp.status_code == 201
    user = resp.json()
    assert user["name"] == "Ada"
    assert user["email"] == "ada@example.com"
    assert user["id"] == 1          # first row, autoincrement primary key


def test_post_then_get_round_trip(client):
    make_user(client, "Ada", "ada@example.com")
    make_user(client, "Lin", "lin@example.com")

    resp = client.get("/api/users/")
    assert resp.status_code == 200
    names = [u["name"] for u in resp.json()]
    assert names == ["Ada", "Lin"]


def test_post_missing_field_is_rejected(client):
    # email is required by the UserCreate Pydantic model. Leaving it out is a
    # 422 (Unprocessable Entity) BEFORE anything touches the database.
    # (Lesson 24's reqparse returned 400 here — different framework, different code.)
    resp = client.post("/api/users/", json={"name": "NoEmail"})
    assert resp.status_code == 422

    # Nothing should have been saved.
    assert client.get("/api/users/").json() == []


# ---------- a single item: /api/users/{id} ----------

def test_get_single_user(client):
    make_user(client, "Ada", "ada@example.com")

    resp = client.get("/api/users/1")
    assert resp.status_code == 200
    user = resp.json()
    assert user["id"] == 1
    assert user["name"] == "Ada"


def test_get_missing_user_404s(client):
    # main.py raises HTTPException(404, "User not found!") when the id is absent.
    resp = client.get("/api/users/999")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "User not found!"}


def test_patch_updates_a_user(client):
    make_user(client, "Ada", "ada@example.com")

    resp = client.patch(
        "/api/users/1",
        json={"name": "Ada Lovelace", "email": "ada.l@example.com"},
    )
    assert resp.status_code == 200
    user = resp.json()
    assert user["name"] == "Ada Lovelace"
    assert user["email"] == "ada.l@example.com"

    # And the change persisted, not just echoed back.
    again = client.get("/api/users/1").json()
    assert again["name"] == "Ada Lovelace"


def test_patch_missing_user_404s(client):
    resp = client.patch(
        "/api/users/999",
        json={"name": "Ghost", "email": "ghost@example.com"},
    )
    assert resp.status_code == 404


def test_delete_removes_a_user(client):
    make_user(client, "Ada", "ada@example.com")
    make_user(client, "Lin", "lin@example.com")

    resp = client.delete("/api/users/1")
    assert resp.status_code == 200
    # delete returns the REMAINING users; Ada (id 1) should be gone.
    remaining = [u["name"] for u in resp.json()]
    assert remaining == ["Lin"]

    # Confirm Ada is really gone.
    assert client.get("/api/users/1").status_code == 404


def test_delete_missing_user_404s(client):
    resp = client.delete("/api/users/999")
    assert resp.status_code == 404
