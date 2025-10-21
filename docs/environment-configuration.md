# Environment Configuration Guide

This document provides comprehensive guidance for configuring environment-specific settings for the Railway CI/CD deployment pipeline.

## Overview

The application supports multiple deployment environments with different configuration requirements:

- **Production**: Strict security, optimized performance, minimal logging
- **Staging**: Balanced security, debugging enabled, comprehensive logging
- **Development**: Permissive settings, full debugging, local development support

## Configuration Files

### Environment Templates

| File | Purpose | Usage |
|------|---------|-------|
| `scripts/config/production.env` | Production environment template | Copy and customize for production |
| `scripts/config/staging.env` | Staging environment template | Copy and customize for staging |

### Configuration Management

| File | Purpose |
|------|---------|
| `scripts/setup-environment.py` | Environment configuration utility |
| `docs/github-secrets-setup.md` | GitHub secrets configuration guide |

## Environment-Specific Configuration

### Production Environment

#### Service Configuration
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
WORKERS=4
```

#### CORS Configuration
```bash
# Strict CORS policy for production
CORS_ORIGINS_PROD=https://anime-frontend-production.railway.app
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOWED_HEADERS=Content-Type,Authorization,X-Requested-With
CORS_MAX_AGE=86400
```

#### Security Configuration
```bash
SECURE_HEADERS=true
FORCE_HTTPS=true
ENABLE_DOCS=false
ENABLE_REDOC=false
```

### Staging Environment

#### Service Configuration
```bash
ENVIRONMENT=staging
DEBUG=true
LOG_LEVEL=debug
WORKERS=2
```

#### CORS Configuration
```bash
# More permissive CORS for staging and testing
CORS_ORIGINS_STAGING=https://anime-frontend-staging.railway.app
CORS_ADDITIONAL_ORIGINS_STAGING=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS,PATCH
CORS_ALLOWED_HEADERS=Content-Type,Authorization,X-Requested-With,X-Debug-Mode
CORS_MAX_AGE=3600
```

#### Development Features
```bash
ENABLE_DOCS=true
ENABLE_REDOC=true
ENABLE_DEBUG_ENDPOINTS=true
ENABLE_MOCK_DATA=true
```

## CORS Configuration Details

### Frontend-Backend Communication

The CORS configuration ensures secure communication between frontend and backend services across different environments.

#### Production CORS Policy
- **Strict origin validation**: Only production frontend URL allowed
- **Limited methods**: Standard REST methods only
- **Secure headers**: Minimal required headers
- **Long cache**: 24-hour preflight cache

#### Staging CORS Policy
- **Flexible origins**: Staging URL + localhost for testing
- **Extended methods**: Includes PATCH for testing
- **Debug headers**: Additional headers for debugging
- **Short cache**: 1-hour preflight cache

#### Development CORS Policy
- **Permissive origins**: Wildcard allowed for local development
- **All methods**: No method restrictions
- **All headers**: No header restrictions
- **No cache**: Immediate preflight expiration

### CORS Configuration Examples

#### Basic Production Setup
```bash
# Frontend service URL
CORS_ORIGINS_PROD=https://anime-frontend-production.railway.app

# Standard configuration
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOWED_HEADERS=Content-Type,Authorization,X-Requested-With
CORS_MAX_AGE=86400
```

#### Staging with Local Development
```bash
# Multiple origins for testing
CORS_ORIGINS_STAGING=https://anime-frontend-staging.railway.app
CORS_ADDITIONAL_ORIGINS_STAGING=http://localhost:3000,http://localhost:8080

# Extended configuration for testing
CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS,PATCH
CORS_ALLOWED_HEADERS=Content-Type,Authorization,X-Requested-With,X-Debug-Mode
CORS_MAX_AGE=3600
```

#### Custom Domain Configuration
```bash
# Production with custom domain
CORS_ORIGINS_PROD=https://myapp.com,https://www.myapp.com
CORS_ADDITIONAL_ORIGINS_PROD=https://cdn.myapp.com

# Staging with preview domains
CORS_ORIGINS_STAGING=https://staging.myapp.com
CORS_ADDITIONAL_ORIGINS_STAGING=https://preview-*.myapp.com
```

## Configuration Management

### Using the Setup Script

The `scripts/setup-environment.py` script provides utilities for managing environment configuration:

#### Validate Configuration
```bash
python scripts/setup-environment.py --environment production --validate
```

#### Show Configuration Summary
```bash
python scripts/setup-environment.py --environment staging --summary
```

#### Generate CORS Configuration
```bash
python scripts/setup-environment.py \
  --environment production \
  --generate-cors \
  --frontend-url https://myapp.com \
  --additional-origins https://cdn.myapp.com
```

#### Export GitHub Secrets
```bash
python scripts/setup-environment.py --environment production --export-secrets
```

### Manual Configuration Steps

#### 1. Copy Environment Template
```bash
# For production
cp scripts/config/production.env scripts/config/production.local.env

# For staging  
cp scripts/config/staging.env scripts/config/staging.local.env
```

#### 2. Update Configuration Values
Edit the copied file and replace template values:
- `your_railway_token_here` → Your actual Railway token
- `your_production_project_id_here` → Your Railway project ID
- Service URLs → Your actual Railway service URLs

#### 3. Configure GitHub Secrets
Set the following secrets in your GitHub repository:
- `RAILWAY_TOKEN`
- `RAILWAY_PROJECT_ID_PROD`
- `RAILWAY_PROJECT_ID_STAGING`

## Environment Variables Reference

### Core Configuration

| Variable | Production | Staging | Description |
|----------|------------|---------|-------------|
| `ENVIRONMENT` | `production` | `staging` | Environment identifier |
| `DEBUG` | `false` | `true` | Debug mode |
| `LOG_LEVEL` | `info` | `debug` | Logging level |
| `WORKERS` | `4` | `2` | Uvicorn workers |

### CORS Configuration

| Variable | Description | Production Example | Staging Example |
|----------|-------------|-------------------|-----------------|
| `CORS_ORIGINS_{ENV}` | Allowed origins | `https://app.com` | `https://staging.app.com` |
| `CORS_ADDITIONAL_ORIGINS_{ENV}` | Additional origins | `` | `http://localhost:3000` |
| `CORS_ALLOW_CREDENTIALS` | Allow credentials | `true` | `true` |
| `CORS_ALLOWED_METHODS` | Allowed methods | `GET,POST,PUT,DELETE,OPTIONS` | `GET,POST,PUT,DELETE,OPTIONS,PATCH` |
| `CORS_ALLOWED_HEADERS` | Allowed headers | `Content-Type,Authorization` | `Content-Type,Authorization,X-Debug-Mode` |
| `CORS_MAX_AGE` | Preflight cache | `86400` | `3600` |

### Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | Auto-configured by Railway |
| `DB_POOL_SIZE` | Connection pool size | `5` (prod), `3` (staging) |
| `DB_MAX_OVERFLOW` | Max overflow connections | `10` (prod), `5` (staging) |
| `DB_POOL_RECYCLE` | Connection recycle time | `300` |

### Security Configuration

| Variable | Description | Production | Staging |
|----------|-------------|------------|---------|
| `SECURE_HEADERS` | Enable security headers | `true` | `true` |
| `FORCE_HTTPS` | Force HTTPS redirects | `true` | `false` |
| `ENABLE_DOCS` | Enable API docs | `false` | `true` |
| `ENABLE_REDOC` | Enable ReDoc | `false` | `true` |

## Troubleshooting

### Common CORS Issues

#### 1. "CORS policy: No 'Access-Control-Allow-Origin' header"
**Cause**: Frontend URL not in CORS origins
**Solution**: Add frontend URL to `CORS_ORIGINS_{ENV}` or `CORS_ADDITIONAL_ORIGINS_{ENV}`

#### 2. "CORS policy: Method not allowed"
**Cause**: HTTP method not in allowed methods
**Solution**: Add method to `CORS_ALLOWED_METHODS`

#### 3. "CORS policy: Request header not allowed"
**Cause**: Custom header not in allowed headers
**Solution**: Add header to `CORS_ALLOWED_HEADERS`

### Configuration Validation

#### Check Current Configuration
```bash
# In backend container or local environment
python -c "
import os
from app.main import get_cors_origins
print('CORS Origins:', get_cors_origins())
print('Environment:', os.getenv('ENVIRONMENT'))
"
```

#### Test CORS Configuration
```bash
# Test preflight request
curl -X OPTIONS \
  -H "Origin: https://your-frontend-url.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  https://your-backend-url.com/animes
```

### Environment-Specific Issues

#### Production Issues
- Verify all URLs use HTTPS
- Check that only production frontend URL is in CORS origins
- Ensure debug mode is disabled

#### Staging Issues
- Verify localhost origins are included for local testing
- Check that debug endpoints are enabled
- Ensure staging URLs are correct

## Best Practices

### Security
- ✅ Use environment-specific CORS origins
- ✅ Disable debug mode in production
- ✅ Use HTTPS for all production URLs
- ✅ Limit CORS methods and headers in production
- ❌ Never use wildcard CORS origins in production

### Configuration Management
- ✅ Use environment templates as starting points
- ✅ Validate configuration before deployment
- ✅ Keep sensitive values in GitHub secrets
- ✅ Document custom configuration changes
- ❌ Never commit real secrets to version control

### Testing
- ✅ Test CORS configuration with actual frontend
- ✅ Verify health checks work in all environments
- ✅ Test service communication between environments
- ✅ Validate environment-specific features

## Related Documentation

- [GitHub Secrets Setup](./github-secrets-setup.md)
- [Railway Documentation](https://docs.railway.app/)
- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [MDN CORS Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)