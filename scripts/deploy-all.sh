#!/bin/bash

# Master Railway Deployment Script
# Orchestrates deployment of all services (database, backend, frontend)

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_header() {
    echo -e "${PURPLE}[DEPLOY]${NC} $1"
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Validate environment
validate_environment() {
    print_status "Validating deployment environment..."
    
    if [ -z "$ENVIRONMENT" ]; then
        print_error "ENVIRONMENT variable is required (staging/production)"
        exit 1
    fi
    
    if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
        print_error "ENVIRONMENT must be either 'staging' or 'production'"
        exit 1
    fi
    
    # Check if Railway CLI is installed
    if ! command -v railway &> /dev/null; then
        print_error "Railway CLI is not installed. Please install it first:"
        print_error "npm install -g @railway/cli"
        exit 1
    fi
    
    print_success "Environment validation passed: $ENVIRONMENT"
}

# Load environment configuration
load_environment_config() {
    print_status "Loading environment configuration..."
    
    local config_file="$SCRIPT_DIR/config/${ENVIRONMENT}.env"
    
    if [ -f "$config_file" ]; then
        print_status "Loading configuration from: $config_file"
        source "$config_file"
        print_success "Configuration loaded successfully"
    else
        print_warning "Configuration file not found: $config_file"
        print_warning "Using environment variables only"
    fi
}

# Deploy database service
deploy_database() {
    print_header "STEP 1/3: Deploying Database Service"
    
    if [ -f "$SCRIPT_DIR/deploy-database.sh" ]; then
        bash "$SCRIPT_DIR/deploy-database.sh"
        
        if [ $? -eq 0 ]; then
            print_success "Database deployment completed"
        else
            print_error "Database deployment failed"
            exit 1
        fi
    else
        print_error "Database deployment script not found"
        exit 1
    fi
}

# Deploy backend service
deploy_backend() {
    print_header "STEP 2/3: Deploying Backend Service"
    
    if [ -f "$SCRIPT_DIR/deploy-backend.sh" ]; then
        bash "$SCRIPT_DIR/deploy-backend.sh"
        
        if [ $? -eq 0 ]; then
            print_success "Backend deployment completed"
        else
            print_error "Backend deployment failed"
            exit 1
        fi
    else
        print_error "Backend deployment script not found"
        exit 1
    fi
}

# Deploy frontend service
deploy_frontend() {
    print_header "STEP 3/3: Deploying Frontend Service"
    
    if [ -f "$SCRIPT_DIR/deploy-frontend.sh" ]; then
        bash "$SCRIPT_DIR/deploy-frontend.sh"
        
        if [ $? -eq 0 ]; then
            print_success "Frontend deployment completed"
        else
            print_error "Frontend deployment failed"
            exit 1
        fi
    else
        print_error "Frontend deployment script not found"
        exit 1
    fi
}

# Perform post-deployment verification
post_deployment_verification() {
    print_header "POST-DEPLOYMENT VERIFICATION"
    
    print_status "Performing end-to-end health checks..."
    
    # Wait for services to be fully ready
    print_status "Waiting for services to stabilize..."
    sleep 30
    
    # Get service URLs
    local backend_url_var="BACKEND_URL_${ENVIRONMENT^^}"
    local frontend_url_var="FRONTEND_URL_${ENVIRONMENT^^}"
    
    local backend_url=$(eval echo \$${backend_url_var})
    local frontend_url=$(eval echo \$${frontend_url_var})
    
    # Test backend health
    if [ -n "$backend_url" ]; then
        print_status "Testing backend health: $backend_url/health"
        
        if curl -f -s "$backend_url/health" | grep -q "ok"; then
            print_success "✓ Backend health check passed"
        else
            print_warning "⚠ Backend health check failed"
        fi
        
        # Test API endpoints
        print_status "Testing API endpoints: $backend_url/animes"
        
        if curl -f -s "$backend_url/animes" > /dev/null; then
            print_success "✓ API endpoints accessible"
        else
            print_warning "⚠ API endpoints test failed"
        fi
    else
        print_warning "Backend URL not available for testing"
    fi
    
    # Test frontend
    if [ -n "$frontend_url" ]; then
        print_status "Testing frontend: $frontend_url"
        
        if curl -f -s "$frontend_url" > /dev/null; then
            print_success "✓ Frontend accessible"
        else
            print_warning "⚠ Frontend accessibility test failed"
        fi
    else
        print_warning "Frontend URL not available for testing"
    fi
}

# Print deployment summary
print_deployment_summary() {
    print_header "DEPLOYMENT SUMMARY"
    
    echo ""
    print_success "🚀 Deployment completed for environment: $ENVIRONMENT"
    echo ""
    
    # Service URLs
    local backend_url_var="BACKEND_URL_${ENVIRONMENT^^}"
    local frontend_url_var="FRONTEND_URL_${ENVIRONMENT^^}"
    
    local backend_url=$(eval echo \$${backend_url_var})
    local frontend_url=$(eval echo \$${frontend_url_var})
    
    if [ -n "$frontend_url" ]; then
        echo -e "${GREEN}Frontend:${NC} $frontend_url"
    fi
    
    if [ -n "$backend_url" ]; then
        echo -e "${GREEN}Backend API:${NC} $backend_url"
        echo -e "${GREEN}API Docs:${NC} $backend_url/docs"
        echo -e "${GREEN}Health Check:${NC} $backend_url/health"
    fi
    
    echo ""
    print_status "Deployment completed at: $(date)"
}

# Main deployment orchestration
main() {
    echo ""
    print_header "🚀 RAILWAY DEPLOYMENT ORCHESTRATION"
    print_header "Environment: ${ENVIRONMENT:-unknown}"
    print_header "Timestamp: $(date)"
    echo ""
    
    validate_environment
    load_environment_config
    
    # Deploy services in order: database -> backend -> frontend
    deploy_database
    echo ""
    
    deploy_backend
    echo ""
    
    deploy_frontend
    echo ""
    
    post_deployment_verification
    echo ""
    
    print_deployment_summary
    
    print_success "🎉 All services deployed successfully!"
}

# Handle script arguments
case "${1:-}" in
    "database"|"db")
        print_header "Deploying Database Only"
        validate_environment
        load_environment_config
        deploy_database
        ;;
    "backend"|"api")
        print_header "Deploying Backend Only"
        validate_environment
        load_environment_config
        deploy_backend
        ;;
    "frontend"|"web")
        print_header "Deploying Frontend Only"
        validate_environment
        load_environment_config
        deploy_frontend
        ;;
    "verify"|"test")
        print_header "Running Verification Only"
        validate_environment
        load_environment_config
        post_deployment_verification
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [service]"
        echo ""
        echo "Services:"
        echo "  database, db     Deploy database service only"
        echo "  backend, api     Deploy backend service only"
        echo "  frontend, web    Deploy frontend service only"
        echo "  verify, test     Run post-deployment verification only"
        echo "  (no argument)    Deploy all services"
        echo ""
        echo "Environment variables:"
        echo "  ENVIRONMENT      Required: 'staging' or 'production'"
        echo "  RAILWAY_TOKEN    Required: Railway authentication token"
        echo ""
        exit 0
        ;;
    "")
        # No argument provided, deploy all services
        main
        ;;
    *)
        print_error "Unknown service: $1"
        print_error "Use '$0 help' for usage information"
        exit 1
        ;;
esac