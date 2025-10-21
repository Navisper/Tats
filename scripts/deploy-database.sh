#!/bin/bash

# Railway Database Deployment Script
# Sets up PostgreSQL database service with initialization

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate required environment variables
validate_environment() {
    print_status "Validating environment variables..."
    
    if [ -z "$RAILWAY_TOKEN" ]; then
        print_error "RAILWAY_TOKEN environment variable is required"
        exit 1
    fi
    
    if [ -z "$ENVIRONMENT" ]; then
        print_error "ENVIRONMENT environment variable is required (staging/production)"
        exit 1
    fi
    
    if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
        print_error "ENVIRONMENT must be either 'staging' or 'production'"
        exit 1
    fi
    
    print_success "Environment validation passed"
}

# Set environment-specific configuration
configure_environment() {
    print_status "Configuring environment for: $ENVIRONMENT"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        export RAILWAY_PROJECT_ID="${RAILWAY_PROJECT_ID_PROD}"
        export SERVICE_NAME="anime-database-prod"
    else
        export RAILWAY_PROJECT_ID="${RAILWAY_PROJECT_ID_STAGING}"
        export SERVICE_NAME="anime-database-staging"
    fi
    
    if [ -z "$RAILWAY_PROJECT_ID" ]; then
        print_error "Railway project ID not found for environment: $ENVIRONMENT"
        exit 1
    fi
    
    print_success "Environment configured: $SERVICE_NAME in project $RAILWAY_PROJECT_ID"
}

# Login to Railway CLI
railway_login() {
    print_status "Authenticating with Railway..."
    
    # Set Railway token
    railway login --token "$RAILWAY_TOKEN"
    
    if [ $? -eq 0 ]; then
        print_success "Railway authentication successful"
    else
        print_error "Railway authentication failed"
        exit 1
    fi
}

# Link to Railway project
railway_link() {
    print_status "Linking to Railway project..."
    
    railway link "$RAILWAY_PROJECT_ID"
    
    if [ $? -eq 0 ]; then
        print_success "Successfully linked to Railway project"
    else
        print_error "Failed to link to Railway project"
        exit 1
    fi
}

# Create or verify PostgreSQL service
setup_database_service() {
    print_status "Setting up PostgreSQL database service..."
    
    # Check if service already exists
    if railway service list | grep -q "$SERVICE_NAME"; then
        print_status "Database service '$SERVICE_NAME' already exists"
    else
        print_status "Creating new PostgreSQL service: $SERVICE_NAME"
        
        # Create PostgreSQL service
        railway service create --name "$SERVICE_NAME"
        
        if [ $? -eq 0 ]; then
            print_success "Database service created successfully"
        else
            print_error "Failed to create database service"
            exit 1
        fi
    fi
}

# Add PostgreSQL plugin to service
add_postgresql_plugin() {
    print_status "Adding PostgreSQL plugin to service..."
    
    # Add PostgreSQL plugin
    railway plugin add postgresql --service "$SERVICE_NAME"
    
    if [ $? -eq 0 ]; then
        print_success "PostgreSQL plugin added successfully"
    else
        print_warning "PostgreSQL plugin may already exist or failed to add"
    fi
}

# Wait for database to be ready
wait_for_database() {
    print_status "Waiting for database to be ready..."
    
    local max_attempts=20
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_status "Checking database status (attempt $attempt/$max_attempts)..."
        
        # Check if DATABASE_URL is available
        DATABASE_URL=$(railway variables get DATABASE_URL --service "$SERVICE_NAME" 2>/dev/null)
        
        if [ -n "$DATABASE_URL" ]; then
            print_success "Database is ready with connection URL"
            export DATABASE_URL
            return 0
        fi
        
        sleep 15
        attempt=$((attempt + 1))
    done
    
    print_error "Database setup timed out"
    exit 1
}

# Initialize database with schema
initialize_database() {
    print_status "Initializing database schema..."
    
    # Check if init.sql exists
    if [ ! -f "db/init.sql" ]; then
        print_error "Database initialization script not found at db/init.sql"
        exit 1
    fi
    
    print_status "Reading initialization script..."
    
    # Create a temporary script to run the initialization
    cat > /tmp/init_db.py << 'EOF'
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found")
        sys.exit(1)
    
    print(f"Connecting to database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Read and execute init.sql
        with open('db/init.sql', 'r') as f:
            sql_commands = f.read()
        
        print("Executing database initialization script...")
        cursor.execute(sql_commands)
        
        # Verify table creation
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = cursor.fetchall()
        
        print(f"Database initialized successfully. Tables created: {[t[0] for t in tables]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF
    
    # Install psycopg2 and run initialization
    pip install psycopg2-binary > /dev/null 2>&1 || {
        print_warning "Failed to install psycopg2, trying alternative method..."
        
        # Alternative: use railway run to execute SQL
        print_status "Using Railway CLI to execute initialization script..."
        railway run --service "$SERVICE_NAME" -- psql \$DATABASE_URL -f db/init.sql
        
        if [ $? -eq 0 ]; then
            print_success "Database initialized using Railway CLI"
        else
            print_warning "Database initialization may have failed, but continuing..."
        fi
        
        return 0
    }
    
    # Run the initialization script
    python /tmp/init_db.py
    
    if [ $? -eq 0 ]; then
        print_success "Database schema initialized successfully"
    else
        print_error "Database initialization failed"
        exit 1
    fi
    
    # Clean up
    rm -f /tmp/init_db.py
}

# Verify database connection and schema
verify_database() {
    print_status "Verifying database setup..."
    
    # Create verification script
    cat > /tmp/verify_db.py << 'EOF'
import os
import sys
import psycopg2

def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check if animes table exists and has correct structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'animes' 
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        
        if not columns:
            print("ERROR: animes table not found")
            sys.exit(1)
        
        expected_columns = ['id', 'title', 'genre', 'episodes']
        actual_columns = [col[0] for col in columns]
        
        for expected in expected_columns:
            if expected not in actual_columns:
                print(f"ERROR: Column '{expected}' not found in animes table")
                sys.exit(1)
        
        print(f"✓ Database verification successful. Columns: {actual_columns}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Database verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF
    
    python /tmp/verify_db.py
    
    if [ $? -eq 0 ]; then
        print_success "Database verification completed successfully"
    else
        print_error "Database verification failed"
        exit 1
    fi
    
    # Clean up
    rm -f /tmp/verify_db.py
}

# Export database connection information
export_database_info() {
    print_status "Exporting database connection information..."
    
    if [ -n "$DATABASE_URL" ]; then
        print_success "Database URL: $DATABASE_URL"
        echo "DATABASE_URL=$DATABASE_URL" >> "$GITHUB_OUTPUT" 2>/dev/null || true
        
        # Export environment-specific variable
        if [ "$ENVIRONMENT" = "production" ]; then
            echo "DATABASE_URL_PROD=$DATABASE_URL" >> "$GITHUB_OUTPUT" 2>/dev/null || true
        else
            echo "DATABASE_URL_STAGING=$DATABASE_URL" >> "$GITHUB_OUTPUT" 2>/dev/null || true
        fi
    else
        print_warning "Could not retrieve database URL"
    fi
}

# Main deployment function
main() {
    print_status "Starting database setup for environment: ${ENVIRONMENT:-unknown}"
    
    validate_environment
    configure_environment
    railway_login
    railway_link
    setup_database_service
    add_postgresql_plugin
    wait_for_database
    initialize_database
    verify_database
    export_database_info
    
    print_success "Database setup completed successfully!"
}

# Run main function
main "$@"