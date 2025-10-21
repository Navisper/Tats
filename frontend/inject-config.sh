#!/bin/bash

# Script to inject backend URL configuration at runtime
# This allows dynamic configuration based on Railway environment variables

set -e  # Exit on any error

# Default backend URL for local development
DEFAULT_BACKEND_URL="http://localhost:8000"

# Get backend URL from environment variable or use default
# Support multiple environment variable names for flexibility
BACKEND_URL=${BACKEND_URL:-${API_URL:-${BACKEND_API_URL:-$DEFAULT_BACKEND_URL}}}

echo "=== Frontend Configuration ==="
echo "Environment: ${ENVIRONMENT:-development}"
echo "Backend URL: $BACKEND_URL"

# Validate that the HTML file exists
HTML_FILE="/usr/share/nginx/html/index.html"
if [ ! -f "$HTML_FILE" ]; then
    echo "ERROR: HTML file not found at $HTML_FILE"
    exit 1
fi

# Create backup of original file
cp "$HTML_FILE" "${HTML_FILE}.backup"

# Replace the API_BASE configuration in the HTML file
# Use a more robust sed pattern that handles various quote styles
sed -i "s|const API_BASE = [\"'][^\"']*[\"']|const API_BASE = \"$BACKEND_URL\"|g" "$HTML_FILE"

# Verify the replacement was successful
if grep -q "const API_BASE = \"$BACKEND_URL\"" "$HTML_FILE"; then
    echo "✓ Frontend configuration completed successfully"
else
    echo "ERROR: Failed to update API_BASE configuration"
    # Restore backup
    mv "${HTML_FILE}.backup" "$HTML_FILE"
    exit 1
fi

# Clean up backup
rm -f "${HTML_FILE}.backup"

echo "=== Starting Nginx ==="

# Test nginx configuration before starting
nginx -t

# Execute nginx with proper signal handling
exec nginx -g "daemon off;"