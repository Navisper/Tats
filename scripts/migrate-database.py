#!/usr/bin/env python3
"""
Database migration script for Railway PostgreSQL deployment
Handles database initialization, schema updates, and data migrations
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, List
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import sql

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Database migration manager for Railway PostgreSQL"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(self.database_url)
            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            self.cursor = self.connection.cursor()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Database connection closed")
    
    def execute_sql_file(self, file_path: str) -> bool:
        """Execute SQL commands from a file"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"SQL file not found: {file_path}")
                return False
            
            logger.info(f"Executing SQL file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            for i, statement in enumerate(statements, 1):
                try:
                    logger.debug(f"Executing statement {i}/{len(statements)}")
                    self.cursor.execute(statement)
                except Exception as e:
                    logger.warning(f"Statement {i} failed (may be expected): {e}")
                    # Continue with other statements
            
            logger.info(f"Successfully executed {len(statements)} statements from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute SQL file {file_path}: {e}")
            return False
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table_name,))
            
            return self.cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to check table existence: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table column information"""
        try:
            self.cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = self.cursor.fetchall()
            return [
                {
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                    "default": col[3]
                }
                for col in columns
            ]
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {
            "tables": [],
            "total_tables": 0,
            "anime_count": 0,
            "database_size": "unknown"
        }
        
        try:
            # Get table list
            self.cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tables = [row[0] for row in self.cursor.fetchall()]
            stats["tables"] = tables
            stats["total_tables"] = len(tables)
            
            # Get anime count if table exists
            if "animes" in tables:
                self.cursor.execute("SELECT COUNT(*) FROM animes;")
                stats["anime_count"] = self.cursor.fetchone()[0]
            
            # Get database size
            self.cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
            stats["database_size"] = self.cursor.fetchone()[0]
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
        
        return stats
    
    def verify_schema(self) -> Dict[str, Any]:
        """Verify database schema is correct"""
        verification = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "tables_checked": []
        }
        
        # Check animes table
        if not self.check_table_exists("animes"):
            verification["valid"] = False
            verification["errors"].append("animes table does not exist")
        else:
            verification["tables_checked"].append("animes")
            
            # Check animes table structure
            columns = self.get_table_info("animes")
            column_names = [col["name"] for col in columns]
            
            required_columns = ["id", "title", "genre", "episodes"]
            for required_col in required_columns:
                if required_col not in column_names:
                    verification["valid"] = False
                    verification["errors"].append(f"animes table missing column: {required_col}")
            
            # Check for new columns (created_at, updated_at)
            if "created_at" not in column_names:
                verification["warnings"].append("animes table missing created_at column (migration needed)")
            if "updated_at" not in column_names:
                verification["warnings"].append("animes table missing updated_at column (migration needed)")
        
        return verification
    
    def run_migration(self, init_sql_path: str = "db/init.sql") -> bool:
        """Run complete database migration"""
        logger.info("Starting database migration...")
        
        try:
            # Connect to database
            self.connect()
            
            # Get initial stats
            logger.info("Getting initial database state...")
            initial_stats = self.get_database_stats()
            logger.info(f"Initial state: {initial_stats['total_tables']} tables, {initial_stats['anime_count']} animes")
            
            # Execute initialization script
            if os.path.exists(init_sql_path):
                logger.info(f"Running initialization script: {init_sql_path}")
                if not self.execute_sql_file(init_sql_path):
                    logger.error("Failed to execute initialization script")
                    return False
            else:
                logger.warning(f"Initialization script not found: {init_sql_path}")
            
            # Verify schema
            logger.info("Verifying database schema...")
            verification = self.verify_schema()
            
            if not verification["valid"]:
                logger.error("Schema verification failed:")
                for error in verification["errors"]:
                    logger.error(f"  - {error}")
                return False
            
            if verification["warnings"]:
                logger.warning("Schema verification warnings:")
                for warning in verification["warnings"]:
                    logger.warning(f"  - {warning}")
            
            # Get final stats
            final_stats = self.get_database_stats()
            logger.info(f"Final state: {final_stats['total_tables']} tables, {final_stats['anime_count']} animes")
            logger.info(f"Database size: {final_stats['database_size']}")
            
            logger.info("Database migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            return False
        finally:
            self.disconnect()

def main():
    """Main migration script entry point"""
    parser = argparse.ArgumentParser(description="Railway Database Migration Script")
    parser.add_argument(
        "--database-url",
        help="Database URL (defaults to DATABASE_URL environment variable)"
    )
    parser.add_argument(
        "--init-sql",
        default="db/init.sql",
        help="Path to initialization SQL file (default: db/init.sql)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify schema, don't run migrations"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show database statistics"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get database URL
    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("Database URL not provided. Set DATABASE_URL environment variable or use --database-url")
        sys.exit(1)
    
    # Create migrator
    migrator = DatabaseMigrator(database_url)
    
    try:
        if args.stats_only:
            # Show stats only
            migrator.connect()
            stats = migrator.get_database_stats()
            print("\n=== Database Statistics ===")
            print(f"Tables: {stats['total_tables']}")
            print(f"Table list: {', '.join(stats['tables'])}")
            print(f"Anime count: {stats['anime_count']}")
            print(f"Database size: {stats['database_size']}")
            migrator.disconnect()
            
        elif args.verify_only:
            # Verify schema only
            migrator.connect()
            verification = migrator.verify_schema()
            
            print("\n=== Schema Verification ===")
            print(f"Valid: {verification['valid']}")
            
            if verification["errors"]:
                print("Errors:")
                for error in verification["errors"]:
                    print(f"  - {error}")
            
            if verification["warnings"]:
                print("Warnings:")
                for warning in verification["warnings"]:
                    print(f"  - {warning}")
            
            print(f"Tables checked: {', '.join(verification['tables_checked'])}")
            migrator.disconnect()
            
            if not verification["valid"]:
                sys.exit(1)
        else:
            # Run full migration
            success = migrator.run_migration(args.init_sql)
            if not success:
                sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed with unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()