from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import logging

from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

# Import our database utilities
from .database import db_manager, get_db, verify_database_connection, database_health_check

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

class Anime(Base):
    __tablename__ = "animes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    genre: Mapped[Optional[str]] = mapped_column(String(100))
    episodes: Mapped[Optional[int]] = mapped_column(Integer)

def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=db_manager.engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise

class AnimeIn(BaseModel):
    title: str
    genre: Optional[str] = None
    episodes: Optional[int] = None

class AnimeOut(AnimeIn):
    id: int
    class Config:
        from_attributes = True

app = FastAPI(title="Anime API", version="1.0.0")

# CORS configuration for Railway deployment
def get_cors_origins():
    """Get CORS origins based on environment configuration"""
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Base origins from environment-specific configuration
    if environment == "production":
        base_origins = os.getenv("CORS_ORIGINS_PROD", os.getenv("CORS_ORIGINS", "")).split(",")
        additional_origins = os.getenv("CORS_ADDITIONAL_ORIGINS_PROD", "").split(",")
    elif environment == "staging":
        base_origins = os.getenv("CORS_ORIGINS_STAGING", os.getenv("CORS_ORIGINS", "")).split(",")
        additional_origins = os.getenv("CORS_ADDITIONAL_ORIGINS_STAGING", "").split(",")
    else:
        # Development environment - more permissive
        base_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080").split(",")
        additional_origins = ["*"]  # Allow all origins in development
    
    # Combine and filter empty strings
    all_origins = [origin.strip() for origin in base_origins + additional_origins if origin.strip()]
    
    # Remove duplicates while preserving order
    seen = set()
    cors_origins = []
    for origin in all_origins:
        if origin not in seen:
            seen.add(origin)
            cors_origins.append(origin)
    
    logger.info(f"CORS origins configured for {environment}: {cors_origins}")
    return cors_origins

def get_cors_methods():
    """Get allowed CORS methods"""
    methods = os.getenv("CORS_ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    return [method.strip() for method in methods if method.strip()]

def get_cors_headers():
    """Get allowed CORS headers"""
    headers = os.getenv("CORS_ALLOWED_HEADERS", "Content-Type,Authorization,X-Requested-With").split(",")
    return [header.strip() for header in headers if header.strip()]

# Configure CORS middleware
cors_origins = get_cors_origins()
cors_methods = get_cors_methods()
cors_headers = get_cors_headers()
cors_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
cors_max_age = int(os.getenv("CORS_MAX_AGE", "86400"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_credentials,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
    max_age=cors_max_age,
)

@app.on_event("startup")
def on_startup():
    """Application startup event handler"""
    logger.info("Starting up Anime API...")
    
    # Verify database connection
    connection_status = verify_database_connection()
    if not connection_status["connected"]:
        logger.error(f"Database connection failed: {connection_status['error']}")
        raise RuntimeError("Database connection failed during startup")
    
    logger.info("Database connection verified successfully")
    
    # Initialize database tables
    init_db()
    
    # Seed database if empty (only if not already seeded by init.sql)
    db = db_manager.get_session()
    try:
        count = db.query(Anime).count()
        if count == 0:
            logger.info("Database is empty, seeding with sample data...")
            sample = [
                Anime(title="Fullmetal Alchemist: Brotherhood", genre="Action, Adventure", episodes=64),
                Anime(title="Demon Slayer", genre="Action, Fantasy", episodes=26),
                Anime(title="Your Name", genre="Romance, Drama", episodes=1),
            ]
            db.add_all(sample)
            db.commit()
            logger.info(f"Seeded database with {len(sample)} sample animes")
        else:
            logger.info(f"Database already contains {count} animes")
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")
        db.rollback()
    finally:
        db.close()
    
    logger.info("Application startup completed successfully")

@app.get("/health")
def health() -> Dict[str, Any]:
    """Basic health check endpoint for Railway deployment"""
    try:
        # Quick database connection test
        connection_status = verify_database_connection()
        
        return {
            "status": "ok" if connection_status["connected"] else "error",
            "database": "connected" if connection_status["connected"] else "disconnected",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "database": "unavailable",
            "version": "1.0.0"
        }

@app.get("/health/detailed")
def detailed_health() -> Dict[str, Any]:
    """Detailed health check endpoint with comprehensive database verification"""
    try:
        health_result = database_health_check()
        
        return {
            "status": health_result["status"],
            "timestamp": "2024-01-01T00:00:00Z",  # Would use datetime.utcnow() in real implementation
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "database": health_result,
            "application": {
                "cors_origins": os.getenv("CORS_ORIGINS", "").split(","),
                "debug": os.getenv("DEBUG", "false").lower() == "true"
            }
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0"
        }

@app.get("/health/database")
def database_health() -> Dict[str, Any]:
    """Database-specific health check endpoint"""
    return database_health_check()

@app.get("/animes", response_model=List[AnimeOut])
def list_animes(db: Session = Depends(get_db)):
    """Get all animes"""
    try:
        items = db.query(Anime).order_by(Anime.id).all()
        return items
    except Exception as e:
        logger.error(f"Failed to list animes: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve animes")

@app.post("/animes", response_model=AnimeOut, status_code=201)
def create_anime(payload: AnimeIn, db: Session = Depends(get_db)):
    """Create a new anime"""
    try:
        obj = Anime(title=payload.title, genre=payload.genre, episodes=payload.episodes)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        logger.info(f"Created anime: {obj.title}")
        return obj
    except Exception as e:
        logger.error(f"Failed to create anime: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create anime")

@app.get("/animes/{anime_id}", response_model=AnimeOut)
def get_anime(anime_id: int, db: Session = Depends(get_db)):
    """Get a specific anime by ID"""
    try:
        obj = db.get(Anime, anime_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Anime not found")
        return obj
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get anime {anime_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve anime")

@app.put("/animes/{anime_id}", response_model=AnimeOut)
def update_anime(anime_id: int, payload: AnimeIn, db: Session = Depends(get_db)):
    """Update an existing anime"""
    try:
        obj = db.get(Anime, anime_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Anime not found")
        
        obj.title = payload.title
        obj.genre = payload.genre
        obj.episodes = payload.episodes
        db.commit()
        db.refresh(obj)
        logger.info(f"Updated anime: {obj.title}")
        return obj
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update anime {anime_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update anime")

@app.delete("/animes/{anime_id}", status_code=204)
def delete_anime(anime_id: int, db: Session = Depends(get_db)):
    """Delete an anime"""
    try:
        obj = db.get(Anime, anime_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Anime not found")
        
        title = obj.title
        db.delete(obj)
        db.commit()
        logger.info(f"Deleted anime: {title}")
        return
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete anime {anime_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete anime")
