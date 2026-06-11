# Lesson 26 — Flask vs FastAPI (porting the Lesson 24 users API)

Living notes. The goal of this lesson: rebuild the **exact same** users CRUD API from
Lesson 24, but in FastAPI instead of Flask, so that every difference I see is a
*framework* difference and nothing else. Same domain (users), controlled comparison.

These notes get added to as we build each stage.

---

## The core mapping (Lesson 24 Flask -> Lesson 26 FastAPI)

Every piece of the Lesson 24 Flask API has a direct FastAPI counterpart:

| Lesson 24 (Flask)                                    | FastAPI equivalent                          | What changed |
|------------------------------------------------------|---------------------------------------------|--------------|
| `class Users(Resource)` + `api.add_resource(...)`    | `@app.get("/api/users/")` on a plain function | No Resource classes — routes are decorated functions |
| `reqparse.RequestParser()` (**input** validation)    | a **Pydantic** model (`UserCreate`)         | Validation is driven by type hints; auto 422 on bad input |
| `userFields` + `@marshal_with` (**output** shaping)  | `response_model=UserOut`                     | Output filtering via a Pydantic model |
| `abort(404, message=...)`                            | `raise HTTPException(404, detail=...)`       | |
| `UserModel(db.Model)` (Flask-SQLAlchemy)             | SQLAlchemy model + manual engine/session    | Flask-SQLAlchemy's magic gets unhidden |
| global `db.session`                                  | `Depends(get_db)` per request               | **Dependency injection** — the signature FastAPI idea |
| `app.run(debug=True)`                                | `uvicorn main:app --reload`                  | External ASGI server |
| *(nothing)*                                          | auto docs at **`/docs`**                     | Live Swagger UI for free |

### Packages
Lesson 24 needed three Flask packages: **Flask + Flask-RESTful + Flask-SQLAlchemy**.
Lesson 26 needs essentially **FastAPI + SQLAlchemy** (Pydantic and Starlette come bundled
with FastAPI; uvicorn is the server).

---

## Running it: `uvicorn main:app --reload`

```bash
cd Lesson26
.venv/bin/uvicorn main:app --reload
```

- `main` = the file (`main.py`)
- `app` = the `FastAPI()` object inside it
- `--reload` = auto-restart on code change (the equivalent of Flask's `debug=True`)

This replaces `app.run(debug=True)`. FastAPI doesn't run itself — it's an ASGI app, and
uvicorn is the ASGI server that serves it.

URLs to know:
- `http://localhost:8000/api/users/` — the actual endpoint (`localhost` == `127.0.0.1`)
- `http://localhost:8000/docs` — auto-generated **Swagger UI** (the big selling point)
- `http://localhost:8000/redoc` — same docs, alternate layout

**Why this is the killer feature:** the interactive Swagger doc is generated from your
type hints, continuously, for free. The Lesson 24 Flask API had nothing like it. You can
click "Try it out" -> "Execute" and call your own endpoints from the browser.

---

## Concept 1: Dependency Injection (DI)

**The principle:** a function declares *what it needs*, and the framework *supplies it*,
instead of the function constructing the thing itself. The underlying idea is "inversion
of control" — you don't call the dependency, it gets handed to you.

**Angular version (constructor injection):**
```typescript
constructor(private userService: UserService) {}
// never wrote `new UserService()` — Angular's injector supplied one
```

**FastAPI version (parameter injection):**
```python
def get_users(db: Session = Depends(get_db)):
    # never wrote `SessionLocal()` in the route — FastAPI called get_db() and passed it in
```

Same contract: declare the need, the framework fulfills it.

**Why anyone bothers:** the route has no idea *how* the session is made. So in a test you
can tell FastAPI "when something asks for `get_db`, give them a throwaway in-memory DB
instead" — without touching the route. That swappability is the whole payoff, and it's
why Lesson 24's global `db.session` was harder to test than this. (Angular sold DI on the
same promise; the testing payoff is where it actually shows up.)

`get_db` in `main.py` is a **generator dependency** — it `yield`s a session, and the code
after `yield` (the `db.close()`) runs as cleanup after the request finishes.

---

## Concept 2: Pydantic

**What it is:** a data-validation library. Declare a class with typed fields, and Pydantic
enforces those types *at runtime* — parsing incoming JSON, coercing what it can, and
rejecting what it can't with a precise error.

```python
class UserOut(BaseModel):
    id: int
    name: str
    email: str
```

- Used as `response_model=...` it shapes **output** (the `@marshal_with(userFields)` job).
- Used as a request body parameter it validates **input** (the `reqparse` job) — see Stage 2.

The type hints *are* the validation rules. No `add_argument` lines. Send a request missing
a required field and FastAPI auto-returns a **422** with exactly what's wrong.

**One-line mental model:**
> Pydantic = Lesson 24's `reqparse` + `fields` rolled into one typed class.
> DI = Angular's injector, minus the boilerplate.

`model_config = {"from_attributes": True}` on `UserOut` is what lets Pydantic read a
SQLAlchemy object directly (instead of requiring a plain dict).

---

## Build log (stages)

### Stage 1 — DB setup + read endpoint  [done]
- Wired SQLAlchemy by hand: `engine`, `SessionLocal`, `Base`, `UserModel`.
  (Flask-SQLAlchemy hid all of this behind `db = SQLAlchemy(app)`.)
- `get_db` dependency.
- `UserOut` Pydantic schema (output shaping).
- `GET /` home, `GET /api/users/` list (returns `[]` until we add users).
- Confirmed the live Swagger UI at `/docs`.

### Stage 2 — POST (create) + Pydantic input validation  [done]
- Added `UserCreate` (input schema) — replaces `reqparse.RequestParser()`.
- `POST /api/users/` with `user: UserCreate` param = "read + validate the JSON body."
- `status_code=201` replaces `return users, 201`.
- `db.refresh(new_user)` reloads the row to pick up the DB-generated id.
- Deviation from Lesson 24: returns the **created user**, not the whole list (more
  conventional REST; Lesson 24 returned the full list).
- Validation has TWO layers, both return 422:
  - `type: json_invalid` — the body isn't even valid JSON (e.g. trailing comma). Syntax.
  - `type: missing` / `string_type` / etc. — valid JSON, but breaks the `UserCreate` schema.
    Pydantic names the exact field in `loc` and echoes your `input` back.
- All of this validation + error messaging is generated from the Pydantic model. Zero
  hand-written error handling.

### Stage 3 — single-user GET / PATCH / DELETE + HTTPException  [done]
- `@app.get/patch/delete("/api/users/{id}")` with `id: int` in the signature.
  - Flask's `'/api/users/<int:id>'` -> `"{id}"` in the path + `id: int` type hint.
    The `<int:...>` conversion is now just the type hint.
- `raise HTTPException(status_code=404, detail="User not found!")` replaces
  `abort(404, message="User not found!")`. `detail` replaces `message`; you `raise`
  instead of `call`.
- PATCH reuses `UserCreate`, so (like Lesson 24) it requires BOTH fields.
  - Footnote: a "true" partial PATCH would use a schema with Optional fields
    (e.g. `name: str | None = None`) so you can update just one field. Lesson 24
    didn't do that either, so we matched it for parity.
- DELETE returns the remaining list of users (matches Lesson 24).

### Stage 4 — tests with FastAPI TestClient  [pending]
- (to be filled in)
