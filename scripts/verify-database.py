#!/usr/bin/env python3
"""
Simple database connection verification script for Railway deployment
Can be used as a standalone health check or in CI/CD pipelines
"""

import os
import sys
import json
import argparse
from typing import Dict, Any
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def verify_database_connection(database_url: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Verify database connection and return status information
    
    Args:
        database_url: PostgreSQL connection URL
        verbose: Whether to include detailed information
    
    Returns:
        Dictionary with connection status and details
    """
    result = {
        "connected": False,
        "error": None,
        "database_info": {},
        "tables": [],
        "version": None,
        "test_results": {}
    }
    
    connection = None
    cursor = None
    
    try:
        # Establish connection
        connection = psycopg2.connect(database_url)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        
        result["connected"] = True
        
        if verbose:
            # Get PostgreSQL version
            cursor.execute("SELECT version();")
            result["version"] = cursor.fetchone()[0]
            
            # Get database name and user
            cursor.execute("SELECT current_database(), current_user;")
            db_info = cursor.fetchone()
            result["database_info"] = {
                "name": db_info[0],
                "user": db_info[1]
            }
            
            # Get table list
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            result["tables"] = [row[0] for row in cursor.fetchall()]
            
            # Test basic operations if animes table exists
            if "animes" in result["tables"]:
                try:
                    # Test SELECT
                    cursor.execute("SELECT COUNT(*) FROM animes;")
                    count = cursor.fetchone()[0]
                    result["test_results"]["select"] = {"success": True, "count": count}
                    
                    # Test INSERT/DELETE (transaction)
                    cursor.execute("BEGIN;")
                    cursor.execute("""
                        INSERT INTO animes (title, genre, episodes) 
                        VALUES ('__test__', 'test', 1) 
                        RETURNING id;
                    """)
                    test_id = cursor.fetchone()[0]
                    
                    cursor.execute("DELETE FROM animes WHERE id = %s;", (test_id,))
                    cursor.execute("ROLLBACK;")
                    
                    result["test_results"]["write"] = {"success": True}
                    
                except Exception as e:
                    result["test_results"]["write"] = {"success": False, "error": str(e)}
            
    except psycopg2.OperationalError as e:
        result["error"] = f"Connection failed: {str(e)}"
    except psycopg2.Error as e:
        result["error"] = f"Database error: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    
    return result

def main():
    """Main script entry point"""
    parser = argparse.ArgumentParser(description="Verify Railway Database Connection")
    parser.add_argument(
        "--database-url",
        help="Database URL (defaults to DATABASE_URL environment variable)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed information"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output errors (exit code indicates success/failure)"
    )
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        if not args.quiet:
            print("ERROR: Database URL not provided. Set DATABASE_URL environment variable or use --database-url", file=sys.stderr)
        sys.exit(1)
    
    # Verify connection
    result = verify_database_connection(database_url, args.verbose)
    
    if args.json:
        # Output JSON
        print(json.dumps(result, indent=2))
    elif not args.quiet:
        # Human-readable output
        if result["connected"]:
            print("✓ Database connection successful")
            
            if args.verbose and result["database_info"]:
                print(f"  Database: {result['database_info']['name']}")
                print(f"  User: {result['database_info']['user']}")
                
                if result["tables"]:
                    print(f"  Tables: {', '.join(result['tables'])}")
                
                if result["test_results"]:
                    if result["test_results"].get("select", {}).get("success"):
                        count = result["test_results"]["select"]["count"]
                        print(f"  Anime records: {count}")
                    
                    if result["test_results"].get("write", {}).get("success"):
                        print("  ✓ Write operations working")
                    elif "write" in result["test_results"]:
                        print("  ⚠ Write operations failed")
        else:
            print(f"✗ Database connection failed: {result['error']}")
    
    # Exit with appropriate code
    sys.exit(0 if result["connected"] else 1)

if __name__ == "__main__":
    main()