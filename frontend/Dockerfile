# Frontend Dockerfile - Multi-stage build optimized for Railway deployment

# Build stage - Optimize static assets
FROM alpine:3.18 AS builder

# Install tools for asset optimization
RUN apk add --no-cache \
    nodejs \
    npm \
    curl \
    gzip

# Create working directory
WORKDIR /app

# Copy source files
COPY index.html .
COPY inject-config.sh .

# Create optimized static assets
RUN mkdir -p dist && \
    # Copy HTML file to dist
    cp index.html dist/ && \
    # Pre-compress static assets for better performance
    gzip -k -9 dist/index.html && \
    # Ensure script is executable
    chmod +x inject-config.sh

# Production stage - Nginx runtime
FROM nginx:1.25-alpine

# Install required packages for runtime configuration
RUN apk add --no-cache bash curl && \
    # Remove default nginx files
    rm -rf /usr/share/nginx/html/* && \
    # Create necessary directories with proper permissions
    mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp && \
    chown -R nginx:nginx /var/cache/nginx \
                        /var/log/nginx \
                        /usr/share/nginx/html

# Copy optimized static files from builder stage
COPY --from=builder /app/dist/ /usr/share/nginx/html/

# Copy production-optimized nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy configuration injection script
COPY --from=builder /app/inject-config.sh /usr/local/bin/inject-config.sh

# Health check with improved configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Expose port 80
EXPOSE 80

# Use custom entrypoint to inject configuration and start nginx
ENTRYPOINT ["/usr/local/bin/inject-config.sh"]
