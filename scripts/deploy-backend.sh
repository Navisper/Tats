#!/bin/bash

# Railway Backend Deployment Script
# Deploys the backend service with database connection setup

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
        export SERVICE_NAME="anime-backend-prod"
        export DATABASE_SERVICE="anime-database-prod"
        export FRONTEND_URL_VAR="FRONTEND_URL_PROD"
    else
        export RAILWAY_PROJECT_ID="${RAILWAY_PROJECT_ID_STAGING}"
        export SERVICE_NAME="anime-backend-staging"
        export DATABASE_SERVICE="anime-database-staging"
        export FRONTEND_URL_VAR="FRONTEND_URL_STAGING"
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

# Get database connection URL
get_database_url() {
    print_status "Retrieving database connection URL..."
    
    # Get DATABASE_URL from the database service
    DATABASE_URL=$(railway variables get DATABASE_URL --service "$DATABASE_SERVICE" 2>/dev/null)
    
    if [ -z "$DATABASE_URL" ]; then
        print_warning "DATABASE_URL not found from database service, checking environment variables..."
        
        # Try to get from environment-specific variable
        if [ "$ENVIRONMENT" = "production" ]; then
            DATABASE_URL="$DATABASE_URL_PROD"
        else
            DATABASE_URL="$DATABASE_URL_STAGING"
        fi
    fi
    
    if [ -z "$DATABASE_URL" ]; then
        print_error "DATABASE_URL could not be determined"
        exit 1
    fi
    
    print_success "Database URL configured"
    export DATABASE_URL
}

# Configure environment variables
configure_service_variables() {
    print_status "Configuring service environment variables..."
    
    # Set DATABASE_URL
    print_status "Setting DATABASE_URL for database connection"
    railway variables set DATABASE_URL="$DATABASE_URL" --service "$SERVICE_NAME"
    
    # Set ENVIRONMENT
    print_status "Setting ENVIRONMENT to: $ENVIRONMENT"
    railway variables set ENVIRONMENT="$ENVIRONMENT" --service "$SERVICE_NAME"
    
    # Configure CORS origins
    FRONTEND_URL=$(eval echo \$${FRONTEND_URL_VAR})
    if [ -z "$FRONTEND_URL" ]; then
        print_warning "Frontend URL not found for $FRONTEND_URL_VAR, using default"
        if [ "$ENVIRONMENT" = "production" ]; then
            FRONTEND_URL="https://anime-frontend-prod.railway.app"
        else
            FRONTEND_URL="https://anime-frontend-staging.railway.app"
        fi
    fi
    
    print_status "Setting CORS_ORIGINS to: $FRONTEND_URL"
    railway variables set CORS_ORIGINS="$FRONTEND_URL" --service "$SERVICE_NAME"
    
    # Set PORT for Railway
    railway variables set PORT="8000" --service "$SERVICE_NAME"
    
    # Set Python-specific environment variables
    railway variables set PYTHONDONTWRITEBYTECODE="1" --service "$SERVICE_NAME"
    railway variables set PYTHONUNBUFFERED="1" --service "$SERVICE_NAME"
    railway variables set PYTHONPATH="/app" --service "$SERVICE_NAME"
    
    print_success "Environment variables configured"
}

# Deploy backend service
deploy_backend() {
    print_status "Deploying backend service: $SERVICE_NAME"
    
    # Change to backend directory
    cd backend
    
    # Deploy the service
    railway up --service "$SERVICE_NAME" --detach
    
    if [ $? -eq 0 ]; then
        print_success "Backend deployment initiated successfully"
    else
        print_error "Backend deployment failed"
        exit 1
    fi
    
    # Return to root directory
    cd ..
}

# Wait for deployment to complete
wait_for_deployment() {
    print_status "Waiting for deployment to complete..."
    
    # Wait for deployment (Railway CLI doesn't have a built-in wait, so we'll check status)
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_status "Checking deployment status (attempt $attempt/$max_attempts)..."
        
        # Get service status
        if railway status --service "$SERVICE_NAME" | grep -q "deployed"; then
            print_success "Deployment completed successfully"
            return 0
        fi
        
        sleep 10
        attempt=$((attempt + 1))
    done
    
    print_warning "Deployment status check timed out, but deployment may still be in progress"
    return 0
}

# Verify database connection
verify_database_connection() {
    print_status "Verifying database connection..."
    
    # Get service URL for health check
    SERVICE_URL=$(railway domain --service "$SERVICE_NAME" 2>/dev/null | head -n1)
    
    if [ -n "$SERVICE_URL" ]; then
        print_status "Testing database connection via health endpoint..."
        
        # Wait a bit for service to be ready
        sleep 15
        
        # Test health endpoint with retry logic
        local max_attempts=5
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if curl -f -s "https://$SERVICE_URL/health" | grep -q "connected"; then
                print_success "Database connection verified successfully"
                return 0
            fi
            
            print_status "Database connection test attempt $attempt/$max_attempts failed, retrying..."
            sleep 10
            attempt=$((attempt + 1))
        done
        
        print_warning "Database connection verification timed out, but service may still be starting"
    else
        print_warning "Could not retrieve service URL for database verification"
    fi
}

# Get service URL
get_service_url() {
    print_status "Retrieving service URL..."
    
    # Get the service URL
    SERVICE_URL=$(railway domain --service "$SERVICE_NAME" 2>/dev/null | head -n1)
    
    if [ -n "$SERVICE_URL" ]; then
        print_success "Backend service deployed at: https://$SERVICE_URL"
        print_status "API endpoints available at: https://$SERVICE_URL/animes"
        print_status "Health check available at: https://$SERVICE_URL/health"
        echo "BACKEND_URL=https://$SERVICE_URL" >> "$GITHUB_OUTPUT" 2>/dev/null || true
    else
        print_warning "Could not retrieve service URL"
    fi
}

# Main deployment function
main() {
    print_status "Starting backend deployment for environment: ${ENVIRONMENT:-unknown}"
    
    validate_environment
    configure_environment
    railway_login
    railway_link
    get_database_url
    configure_service_variables
    deploy_backend
    wait_for_deployment
    verify_database_connection
    get_service_url
    
    print_success "Backend deployment completed successfully!"
}

# Run main function
main "$@"