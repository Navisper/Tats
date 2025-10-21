#!/bin/bash

# Railway Frontend Deployment Script
# Deploys the frontend service with environment-specific configuration

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
        export SERVICE_NAME="anime-frontend-prod"
        export BACKEND_URL_VAR="BACKEND_URL_PROD"
    else
        export RAILWAY_PROJECT_ID="${RAILWAY_PROJECT_ID_STAGING}"
        export SERVICE_NAME="anime-frontend-staging"
        export BACKEND_URL_VAR="BACKEND_URL_STAGING"
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

# Deploy frontend service
deploy_frontend() {
    print_status "Deploying frontend service: $SERVICE_NAME"
    
    # Change to frontend directory
    cd frontend
    
    # Deploy the service
    railway up --service "$SERVICE_NAME" --detach
    
    if [ $? -eq 0 ]; then
        print_success "Frontend deployment initiated successfully"
    else
        print_error "Frontend deployment failed"
        exit 1
    fi
    
    # Return to root directory
    cd ..
}

# Configure environment variables
configure_service_variables() {
    print_status "Configuring service environment variables..."
    
    # Get backend URL from environment variable
    BACKEND_URL=$(eval echo \$${BACKEND_URL_VAR})
    
    if [ -z "$BACKEND_URL" ]; then
        print_warning "Backend URL not found for $BACKEND_URL_VAR, using default"
        if [ "$ENVIRONMENT" = "production" ]; then
            BACKEND_URL="https://anime-backend-prod.railway.app"
        else
            BACKEND_URL="https://anime-backend-staging.railway.app"
        fi
    fi
    
    print_status "Setting BACKEND_URL to: $BACKEND_URL"
    railway variables set BACKEND_URL="$BACKEND_URL" --service "$SERVICE_NAME"
    
    print_status "Setting ENVIRONMENT to: $ENVIRONMENT"
    railway variables set ENVIRONMENT="$ENVIRONMENT" --service "$SERVICE_NAME"
    
    # Set PORT for Railway (Railway will override this, but good to have)
    railway variables set PORT="80" --service "$SERVICE_NAME"
    
    print_success "Environment variables configured"
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

# Get service URL
get_service_url() {
    print_status "Retrieving service URL..."
    
    # Get the service URL
    SERVICE_URL=$(railway domain --service "$SERVICE_NAME" 2>/dev/null | head -n1)
    
    if [ -n "$SERVICE_URL" ]; then
        print_success "Frontend service deployed at: https://$SERVICE_URL"
        echo "FRONTEND_URL=https://$SERVICE_URL" >> "$GITHUB_OUTPUT" 2>/dev/null || true
    else
        print_warning "Could not retrieve service URL"
    fi
}

# Main deployment function
main() {
    print_status "Starting frontend deployment for environment: ${ENVIRONMENT:-unknown}"
    
    validate_environment
    configure_environment
    railway_login
    railway_link
    configure_service_variables
    deploy_frontend
    wait_for_deployment
    get_service_url
    
    print_success "Frontend deployment completed successfully!"
}

# Run main function
main "$@"