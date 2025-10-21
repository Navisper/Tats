# GitHub Repository Secrets Configuration

This document provides instructions for configuring GitHub repository secrets required for the Railway CI/CD deployment pipeline.

## Required Secrets

The following secrets must be configured in your GitHub repository settings (`Settings > Secrets and variables > Actions > Repository secrets`):

### Core Railway Configuration

| Secret Name | Description | Example Value | Required |
|-------------|-------------|---------------|----------|
| `RAILWAY_TOKEN` | Railway CLI authentication token | `railway_token_xxx...` | ✅ Yes |
| `RAILWAY_PROJECT_ID_PROD` | Railway project ID for production environment | `project-abc123...` | ✅ Yes |
| `RAILWAY_PROJECT_ID_STAGING` | Railway project ID for staging environment | `project-def456...` | ✅ Yes |

## How to Obtain Required Values

### 1. Railway Token

1. Log in to [Railway](https://railway.app)
2. Go to your account settings
3. Navigate to "Tokens" section
4. Create a new token with appropriate permissions
5. Copy the token value

**Required Permissions:**
- Project read/write access
- Service deployment permissions
- Environment variable management

### 2. Railway Project IDs

#### Option A: Using Railway Dashboard
1. Go to your Railway dashboard
2. Select your project
3. The project ID is visible in the URL: `https://railway.app/project/{PROJECT_ID}`

#### Option B: Using Railway CLI
```bash
# Install Railway CLI
curl -fsSL https://railway.app/install.sh | sh

# Login to Railway
railway login

# List your projects
railway projects

# Link to a specific project and get its ID
railway link
```

## Setting Up Secrets in GitHub

### Step 1: Access Repository Secrets
1. Navigate to your GitHub repository
2. Click on `Settings` tab
3. In the left sidebar, click `Secrets and variables` > `Actions`
4. Click `Repository secrets` tab

### Step 2: Add Each Secret
For each required secret:
1. Click `New repository secret`
2. Enter the secret name (exactly as shown in the table above)
3. Enter the secret value
4. Click `Add secret`

### Step 3: Verify Configuration
After adding all secrets, you should see:
- ✅ `RAILWAY_TOKEN`
- ✅ `RAILWAY_PROJECT_ID_PROD`
- ✅ `RAILWAY_PROJECT_ID_STAGING`

## Environment-Specific Configuration

### Production Environment
- **Triggered by**: Pushes to `main` branch
- **Uses secrets**: `RAILWAY_TOKEN`, `RAILWAY_PROJECT_ID_PROD`
- **Service naming**: `anime-{service}-production`

### Staging Environment
- **Triggered by**: Pushes to `develop` branch
- **Uses secrets**: `RAILWAY_TOKEN`, `RAILWAY_PROJECT_ID_STAGING`
- **Service naming**: `anime-{service}-staging`

## Security Best Practices

### Secret Management
- ✅ **Never commit secrets to code**: Use GitHub secrets exclusively
- ✅ **Use environment-specific secrets**: Separate production and staging
- ✅ **Rotate tokens regularly**: Update Railway tokens periodically
- ✅ **Limit token permissions**: Use minimal required permissions

### Access Control
- ✅ **Restrict repository access**: Only authorized team members
- ✅ **Use branch protection**: Require reviews for main branch
- ✅ **Monitor secret usage**: Review GitHub Actions logs regularly

## Troubleshooting

### Common Issues

#### 1. "RAILWAY_TOKEN secret is not configured"
**Solution**: Ensure the secret name is exactly `RAILWAY_TOKEN` (case-sensitive)

#### 2. "Railway authentication failed"
**Solutions**:
- Verify the token is valid and not expired
- Check token permissions include project access
- Regenerate token if necessary

#### 3. "Failed to link to Railway project"
**Solutions**:
- Verify project ID is correct
- Ensure the Railway token has access to the specified project
- Check if project exists and is accessible

#### 4. "Railway project ID not configured for environment"
**Solutions**:
- Verify secret names match exactly: `RAILWAY_PROJECT_ID_PROD` or `RAILWAY_PROJECT_ID_STAGING`
- Ensure both production and staging project IDs are configured
- Check project IDs are valid and accessible

### Validation Commands

You can validate your configuration by running the deployment workflow manually:

1. Go to `Actions` tab in your repository
2. Select `Deploy to Railway` workflow
3. Click `Run workflow`
4. Choose environment and run

## Support

If you encounter issues:
1. Check the GitHub Actions logs for detailed error messages
2. Verify all secrets are configured correctly
3. Test Railway CLI authentication locally
4. Contact the development team for assistance

## Related Documentation

- [Railway Documentation](https://docs.railway.app/)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Railway CLI Guide](https://docs.railway.app/develop/cli)