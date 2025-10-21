# Environment Configuration

This directory contains environment-specific configuration templates for Railway deployment.

## Quick Start

### 1. Choose Your Environment
- **Production**: Use `production.env` for live deployment
- **Staging**: Use `staging.env` for testing and development

### 2. Configure GitHub Secrets
Set these secrets in your GitHub repository (`Settings > Secrets and variables > Actions`):

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `RAILWAY_TOKEN` | Railway CLI authentication token | ✅ |
| `RAILWAY_PROJECT_ID_PROD` | Railway project ID for production | ✅ |
| `RAILWAY_PROJECT_ID_STAGING` | Railway project ID for staging | ✅ |

### 3. Validate Configuration
```bash
# Validate production configuration
python ../setup-environment.py --environment production --validate --summary

# Validate staging configuration  
python ../setup-environment.py --environment staging --validate --summary
```

## Configuration Files

### `production.env`
- **Purpose**: Production environment template
- **Security**: Strict CORS, HTTPS enforced, minimal logging
- **Performance**: Optimized for production workloads
- **Features**: API docs disabled, debug mode off

### `staging.env`
- **Purpose**: Staging/testing environment template
- **Security**: Permissive CORS for testing, debug features enabled
- **Performance**: Balanced for testing and debugging
- **Features**: API docs enabled, debug endpoints available

## Key Configuration Differences

| Setting | Production | Staging | Notes |
|---------|------------|---------|-------|
| **Debug Mode** | `false` | `true` | Affects error reporting |
| **CORS Origins** | Frontend URL only | Frontend + localhost | Testing flexibility |
| **API Docs** | Disabled | Enabled | Security vs. convenience |
| **Workers** | 4 | 2 | Performance optimization |
| **Log Level** | `info` | `debug` | Debugging detail |

## CORS Configuration

### Production CORS
```bash
CORS_ORIGINS_PROD=https://anime-frontend-production.railway.app
CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_MAX_AGE=86400  # 24 hours
```

### Staging CORS
```bash
CORS_ORIGINS_STAGING=https://anime-frontend-staging.railway.app
CORS_ADDITIONAL_ORIGINS_STAGING=http://localhost:3000,http://localhost:8080
CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS,PATCH
CORS_MAX_AGE=3600  # 1 hour
```

## Common Tasks

### Update Service URLs
When Railway assigns new URLs, update these variables:
```bash
# Production
FRONTEND_URL_PROD=https://your-new-frontend-url.railway.app
BACKEND_URL_PROD=https://your-new-backend-url.railway.app

# Staging
FRONTEND_URL_STAGING=https://your-new-staging-frontend-url.railway.app
BACKEND_URL_STAGING=https://your-new-staging-backend-url.railway.app
```

### Add Custom Domain
For production with custom domain:
```bash
CORS_ORIGINS_PROD=https://yourdomain.com,https://www.yourdomain.com
FRONTEND_URL_PROD=https://yourdomain.com
```

### Enable Local Development Testing
For staging environment to work with local development:
```bash
CORS_ADDITIONAL_ORIGINS_STAGING=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080
```

## Troubleshooting

### CORS Errors
If you see CORS errors in the browser:
1. Check that frontend URL is in `CORS_ORIGINS_{ENV}`
2. Verify the HTTP method is in `CORS_ALLOWED_METHODS`
3. Ensure custom headers are in `CORS_ALLOWED_HEADERS`

### Deployment Failures
If deployment fails with environment errors:
1. Run validation: `python ../setup-environment.py --environment {env} --validate`
2. Check GitHub secrets are set correctly
3. Verify Railway project IDs are correct

### Service Communication Issues
If frontend can't reach backend:
1. Check `BACKEND_URL` in frontend service
2. Verify CORS configuration allows frontend origin
3. Test backend health endpoint directly

## Security Notes

⚠️ **Important Security Practices**:
- Never commit real secrets to version control
- Use different Railway projects for production and staging
- Regularly rotate Railway tokens
- Keep production CORS origins restrictive
- Disable debug features in production

## Getting Help

- 📖 [Full Environment Configuration Guide](../../docs/environment-configuration.md)
- 🔐 [GitHub Secrets Setup Guide](../../docs/github-secrets-setup.md)
- 🚂 [Railway Documentation](https://docs.railway.app/)

## Validation Commands

```bash
# Quick validation
python ../setup-environment.py -e production -v

# Full summary
python ../setup-environment.py -e staging -s

# Export secrets format
python ../setup-environment.py -e production --export-secrets

# Generate CORS config
python ../setup-environment.py -e production --generate-cors --frontend-url https://myapp.com
```