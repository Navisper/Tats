"""
Database connection and health check utilities for Railway deployment
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import psycopg2
from psycopg2 import OperationalError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection manager with health checks and verification"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", 
            "postgresql+psycopg2://postgres:postgres@db:5432/anime_db"
        )
        self.engine = None
        self.SessionLocal = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize database connection with proper configuration"""
        try:
            # Create engine with Railway-optimized settings
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=300,    # Recycle connections every 5 minutes
                pool_size=5,         # Connection pool size
                max_overflow=10,     # Maximum overflow connections
                echo=os.getenv("DB_ECHO", "false").lower() == "true"  # SQL logging
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autoflush=False,
                autocommit=False
            )
            
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def verify_connection(self) -> Dict[str, Any]:
        """
        Verify database connection and return detailed status
        
        Returns:
            Dict containing connection status, database info, and any errors
        """
        result = {
            "connected": False,
            "database_url": self.database_url.split('@')[1] if '@' in self.database_url else "hidden",
            "error": None,
            "database_info": {},
            "tables": [],
            "version": None
        }
        
        try:
            # Test basic connection
            with self.engine.connect() as connection:
                # Get PostgreSQL version
                version_result = connection.execute(text("SELECT version()"))
                result["version"] = version_result.scalar()
                
                # Get database name
                db_name_result = connection.execute(text("SELECT current_database()"))
                result["database_info"]["name"] = db_name_result.scalar()
                
                # Get current user
                user_result = connection.execute(text("SELECT current_user"))
                result["database_info"]["user"] = user_result.scalar()
                
                # Get table list
                inspector = inspect(self.engine)
                result["tables"] = inspector.get_table_names()
                
                # Test a simple query on animes table if it exists
                if "animes" in result["tables"]:
                    count_result = connection.execute(text("SELECT COUNT(*) FROM animes"))
                    result["database_info"]["anime_count"] = count_result.scalar()
                
                result["connected"] = True
                logger.info("Database connection verification successful")
                
        except SQLAlchemyError as e:
            result["error"] = f"SQLAlchemy error: {str(e)}"
            logger.error(f"Database connection verification failed: {e}")
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error during database verification: {e}")
        
        return result
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check of the database
        
        Returns:
            Dict containing health status and performance metrics
        """
        health_result = {
            "status": "unhealthy",
            "checks": {
                "connection": False,
                "tables_exist": False,
                "can_query": False,
                "can_write": False
            },
            "metrics": {},
            "error": None
        }
        
        try:
            # Check 1: Basic connection
            connection_info = self.verify_connection()
            health_result["checks"]["connection"] = connection_info["connected"]
            
            if not connection_info["connected"]:
                health_result["error"] = connection_info["error"]
                return health_result
            
            # Check 2: Required tables exist
            required_tables = ["animes"]
            existing_tables = connection_info["tables"]
            health_result["checks"]["tables_exist"] = all(
                table in existing_tables for table in required_tables
            )
            
            if not health_result["checks"]["tables_exist"]:
                health_result["error"] = f"Missing required tables. Found: {existing_tables}"
                return health_result
            
            # Check 3: Can perform read operations
            with self.engine.connect() as connection:
                try:
                    result = connection.execute(text("SELECT COUNT(*) FROM animes"))
                    count = result.scalar()
                    health_result["checks"]["can_query"] = True
                    health_result["metrics"]["anime_count"] = count
                except Exception as e:
                    health_result["error"] = f"Query test failed: {str(e)}"
                    return health_result
                
                # Check 4: Can perform write operations (test transaction)
                try:
                    with connection.begin():
                        # Test insert and rollback
                        connection.execute(text("""
                            INSERT INTO animes (title, genre, episodes) 
                            VALUES ('__health_check__', 'test', 1)
                        """))
                        connection.execute(text("""
                            DELETE FROM animes WHERE title = '__health_check__'
                        """))
                    
                    health_result["checks"]["can_write"] = True
                except Exception as e:
                    health_result["error"] = f"Write test failed: {str(e)}"
                    return health_result
            
            # All checks passed
            health_result["status"] = "healthy"
            logger.info("Database health check passed")
            
        except Exception as e:
            health_result["error"] = f"Health check failed: {str(e)}"
            logger.error(f"Database health check failed: {e}")
        
        return health_result
    
    def get_session(self):
        """Get a database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

# Global database manager instance
db_manager = DatabaseManager()

def get_db():
    """Dependency to get database session"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()

def verify_database_connection() -> Dict[str, Any]:
    """Standalone function to verify database connection"""
    return db_manager.verify_connection()

def database_health_check() -> Dict[str, Any]:
    """Standalone function for database health check"""
    return db_manager.health_check()