"""
Tests for api.py — the Flask-RESTful CRUD endpoints.

Same idea as Lesson23: Flask gives us a "test client", a fake browser that
sends requests to our app IN MEMORY (no real server, no network). We assert
on the response's .status_code and its JSON body (resp.get_json()).

THE ONE TRICKY PART — an isolated database
------------------------------------------
api.py hard-codes 'sqlite:///database.db', and Flask-SQLAlchemy builds that
engine ONCE, the moment api.py is imported. After that it refuses to let you
re-point it (init_app raises). So we can't just override the config string in
a fixture the way Lesson23 flipped TESTING=True.

If we did nothing, every test would read and WRITE your real instance/database.db
— polluting your data and making tests depend on each other's leftovers. Bad.

In a production app the clean fix is the "application factory" pattern
(a create_app() function you call with a test config). Dave didn't teach that
here, and I didn't want to rewrite your finished api.py. So instead, for the
test run only, we swap in a brand-new engine pointed at a THROWAWAY temp file.
Each test gets its own empty database; the temp file is deleted afterward.
The swap line reaches into a Flask-SQLAlchemy internal (db._app_engines) — the
one slightly hacky thing in this file — so it's commented where it happens.
"""
import os
import tempfile

import pytest
from sqlalchemy import create_engine

from api import app, db


@pytest.fixture
def client():
    # TESTING=True makes Flask surface errors to us instead of hiding them.
    app.config["TESTING"] = True

    # A fresh, empty temp-file database for THIS test only.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    test_engine = create_engine(f"sqlite:///{path}")

    # Remember the real engine so we can put it back when the test ends...
    original_engine = db._app_engines[app][None]
    # ...then redirect the app at our throwaway db. This is the internal-poke
    # that stands in for the app-factory pattern (see the module docstring).
    db._app_engines[app][None] = test_engine

    with app.app_context():
        db.create_all()              # build the user_model table in the temp db
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()

    # Teardown: restore the real engine and delete the temp file.
    db._app_engines[app][None] = original_engine
    test_engine.dispose()
    os.unlink(path)


def make_user(client, name="Ada", email="ada@example.com"):
    """Helper: POST a user and return the response."""
    return client.post("/api/users/", json={"name": name, "email": email})


# ---------- the home page ----------

def test_home_route(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Flask REST API" in resp.data


# ---------- the collection: /api/users/ ----------

def test_get_users_empty_to_start(client):
    # A fresh temp db has no users, so GET should return an empty JSON list.
    resp = client.get("/api/users/")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_post_creates_a_user(client):
    resp = make_user(client, "Ada", "ada@example.com")

    # Users.post returns (all_users, 201). 201 = "Created".
    assert resp.status_code == 201
    users = resp.get_json()
    assert len(users) == 1
    assert users[0]["name"] == "Ada"
    assert users[0]["email"] == "ada@example.com"
    assert users[0]["id"] == 1          # first row, autoincrement primary key


def test_post_then_get_round_trip(client):
    make_user(client, "Ada", "ada@example.com")
    make_user(client, "Lin", "lin@example.com")

    resp = client.get("/api/users/")
    assert resp.status_code == 200
    names = [u["name"] for u in resp.get_json()]
    assert names == ["Ada", "Lin"]


def test_post_missing_field_is_rejected(client):
    # reqparse marks name & email required=True. Leaving one out should be a
    # 400 (Bad Request) BEFORE anything touches the database.
    resp = client.post("/api/users/", json={"name": "NoEmail"})
    assert resp.status_code == 400

    # Nothing should have been saved.
    assert client.get("/api/users/").get_json() == []


# ---------- a single item: /api/users/<id> ----------

def test_get_single_user(client):
    make_user(client, "Ada", "ada@example.com")

    resp = client.get("/api/users/1")
    assert resp.status_code == 200
    user = resp.get_json()
    assert user["id"] == 1
    assert user["name"] == "Ada"


def test_get_missing_user_404s(client):
    # api.py calls abort(404, "User not found!") when the id doesn't exist.
    resp = client.get("/api/users/999")
    assert resp.status_code == 404


def test_patch_updates_a_user(client):
    make_user(client, "Ada", "ada@example.com")

    resp = client.patch(
        "/api/users/1",
        json={"name": "Ada Lovelace", "email": "ada.l@example.com"},
    )
    assert resp.status_code == 200
    user = resp.get_json()
    assert user["name"] == "Ada Lovelace"
    assert user["email"] == "ada.l@example.com"

    # And the change persisted, not just echoed back.
    again = client.get("/api/users/1").get_json()
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
    remaining = [u["name"] for u in resp.get_json()]
    assert remaining == ["Lin"]

    # Confirm Ada is really gone.
    assert client.get("/api/users/1").status_code == 404


def test_delete_missing_user_404s(client):
    resp = client.delete("/api/users/999")
    assert resp.status_code == 404
