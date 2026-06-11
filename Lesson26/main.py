from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Integer, String
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column

# --- Database setup ---
# In Lesson 24, Flask-SQLAlchemy did all of this for you behind `db = SQLAlchemy(app)`.
# Here we wire it by hand so you can see the moving parts.
engine = create_engine("sqlite:///database.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)

class Base(DeclarativeBase):
    pass

# This is the same UserModel as Lesson 24, just SQLAlchemy 2.0 style.
class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)

# get_db is a DEPENDENCY. FastAPI calls it for each request, hands your route
# a fresh session, then runs the code after `yield` to clean up. This replaces
# Lesson 24's global `db.session`.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic schemas ---
# UserOut replaces Lesson 24's `userFields` + @marshal_with (OUTPUT shaping).
# UserCreate replaces Lesson 24's reqparse RequestParser (INPUT validation).
# The type hints ARE the rules. No add_argument lines. Missing/wrong field -> auto 422.
class UserCreate(BaseModel):
    name: str
    email: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    model_config = {"from_attributes": True}  # lets it read a SQLAlchemy object

# --- App ---
app = FastAPI()
Base.metadata.create_all(bind=engine)  # creates the table (Lesson 24's create_db.py)

@app.get("/")
def home():
    return {"message": "FastAPI REST API"}

# Lesson 24: class Users(Resource).get + api.add_resource(Users, '/api/users/')
# FastAPI: a decorated function. response_model does what @marshal_with did.
@app.get("/api/users/", response_model=list[UserOut])
def get_users(db: Session = Depends(get_db)):
    return db.query(UserModel).all()

# Lesson 24: class Users(Resource).post + reqparse.parse_args()
# A Pydantic model as a parameter tells FastAPI "read this from the JSON body and
# validate it." status_code=201 replaces Lesson 24's `return users, 201`.
@app.post("/api/users/", response_model=UserOut, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    new_user = UserModel(name=user.name, email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # reloads the row so we get the DB-generated id
    return new_user

# Lesson 24: class User(Resource), path '/api/users/<int:id>'.
# In FastAPI, `{id}` in the path + `id: int` in the signature = a typed path param.
# The int conversion Flask did with `<int:id>` is done here by the type hint.
@app.get("/api/users/{id}", response_model=UserOut)
def get_user(id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")  # was abort(404, ...)
    return user

@app.patch("/api/users/{id}", response_model=UserOut)
def update_user(id: int, updates: UserCreate, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")
    user.name = updates.name
    user.email = updates.email
    db.commit()
    db.refresh(user)
    return user

# Like Lesson 24's delete, this returns the remaining list of users.
@app.delete("/api/users/{id}", response_model=list[UserOut])
def delete_user(id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")
    db.delete(user)
    db.commit()
    return db.query(UserModel).all()
