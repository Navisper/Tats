from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

from sqlalchemy import create_engine, Integer, String
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/anime_db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Anime(Base):
    __tablename__ = "animes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    genre: Mapped[Optional[str]] = mapped_column(String(100))
    episodes: Mapped[Optional[int]] = mapped_column(Integer)

def init_db():
    Base.metadata.create_all(bind=engine)

class AnimeIn(BaseModel):
    title: str
    genre: Optional[str] = None
    episodes: Optional[int] = None

class AnimeOut(AnimeIn):
    id: int
    class Config:
        from_attributes = True

app = FastAPI(title="Anime API", version="1.0.0")

# CORS: allow local frontend on 8080
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()
    # Seed if empty
    db = SessionLocal()
    try:
        count = db.query(Anime).count()
        if count == 0:
            sample = [
                Anime(title="Fullmetal Alchemist: Brotherhood", genre="Action, Adventure", episodes=64),
                Anime(title="Demon Slayer", genre="Action, Fantasy", episodes=26),
                Anime(title="Your Name", genre="Romance, Drama", episodes=1),
            ]
            db.add_all(sample)
            db.commit()
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/animes", response_model=List[AnimeOut])
def list_animes():
    db = SessionLocal()
    try:
        items = db.query(Anime).order_by(Anime.id).all()
        return items
    finally:
        db.close()

@app.post("/animes", response_model=AnimeOut, status_code=201)
def create_anime(payload: AnimeIn):
    db = SessionLocal()
    try:
        obj = Anime(title=payload.title, genre=payload.genre, episodes=payload.episodes)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    finally:
        db.close()

@app.get("/animes/{anime_id}", response_model=AnimeOut)
def get_anime(anime_id: int):
    db = SessionLocal()
    try:
        obj = db.get(Anime, anime_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        return obj
    finally:
        db.close()

@app.put("/animes/{anime_id}", response_model=AnimeOut)
def update_anime(anime_id: int, payload: AnimeIn):
    db = SessionLocal()
    try:
        obj = db.get(Anime, anime_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        obj.title = payload.title
        obj.genre = payload.genre
        obj.episodes = payload.episodes
        db.commit()
        db.refresh(obj)
        return obj
    finally:
        db.close()

@app.delete("/animes/{anime_id}", status_code=204)
def delete_anime(anime_id: int):
    db = SessionLocal()
    try:
        obj = db.get(Anime, anime_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(obj)
        db.commit()
        return
    finally:
        db.close()
