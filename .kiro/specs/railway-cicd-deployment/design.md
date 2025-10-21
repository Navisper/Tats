# Design Document - Railway CI/CD Deployment

## Overview

Este documento describe el diseño de un sistema de CI/CD usando GitHub Actions para desplegar automáticamente una aplicación de microservicios en Railway. El sistema automatizará la construcción, pruebas y despliegue de tres servicios: frontend (Nginx), backend (FastAPI) y base de datos (PostgreSQL).

La arquitectura seguirá un enfoque de despliegue por servicios independientes en Railway, donde cada componente se desplegará como un servicio separado pero interconectado, aprovechando las capacidades nativas de Railway para el manejo de variables de entorno y networking interno.

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "GitHub Repository"
        A[Source Code]
        B[GitHub Actions Workflow]
    end
    
    subgraph "CI/CD Pipeline"
        C[Build Frontend]
        D[Build Backend]
        E[Run Tests]
        F[Deploy to Railway]
    end
    
    subgraph "Railway Platform"
        G[Frontend Service<br/>Nginx]
        H[Backend Service<br/>FastAPI]
        I[Database Service<br/>PostgreSQL]
    end
    
    A --> B
    B --> C
    B --> D
    C --> E
    D --> E
    E --> F
    F --> G
    F --> H
    F --> I
    
    G --> H
    H --> I
```

### Deployment Strategy

**Multi-Service Deployment**: Cada componente (frontend, backend, database) se desplegará como un servicio independiente en Railway, permitiendo escalado y mantenimiento individual.

**Environment-Based Branching**: 
- `develop` branch → Staging environment
- `main` branch → Production environment

**Railway Service Configuration**:
- **Frontend Service**: Dockerfile deployment con Nginx
- **Backend Service**: Dockerfile deployment con FastAPI + Uvicorn
- **Database Service**: Railway PostgreSQL managed service

## Components and Interfaces

### 1. GitHub Actions Workflow

**File**: `.github/workflows/deploy.yml`

**Triggers**:
- Push to `main` branch (production deployment)
- Push to `develop` branch (staging deployment)
- Manual workflow dispatch

**Jobs Structure**:
```yaml
jobs:
  build-and-test:
    - Checkout code
    - Set up Docker Buildx
    - Build frontend image
    - Build backend image
    - Run basic validation tests
    
  deploy-to-railway:
    needs: build-and-test
    - Install Railway CLI
    - Login to Railway
    - Deploy frontend service
    - Deploy backend service
    - Configure environment variables
    - Verify deployment health
```

### 2. Railway Service Definitions

**Frontend Service Configuration**:
- **Source**: `frontend/` directory
- **Build**: Dockerfile-based deployment
- **Port**: 80 (Nginx default)
- **Environment Variables**: 
  - `BACKEND_URL`: Internal Railway service URL

**Backend Service Configuration**:
- **Source**: `backend/` directory  
- **Build**: Dockerfile-based deployment
- **Port**: 8000 (FastAPI default)
- **Environment Variables**:
  - `DATABASE_URL`: Railway PostgreSQL connection string
  - `ENVIRONMENT`: production/staging

**Database Service Configuration**:
- **Type**: Railway PostgreSQL managed service
- **Version**: PostgreSQL 16
- **Initialization**: Custom init script from `db/init.sql`

### 3. Docker Configuration Updates

**Frontend Dockerfile Enhancements**:
```dockerfile
# Multi-stage build for optimization
FROM node:18-alpine AS builder
# Build static assets if needed

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

**Backend Dockerfile Enhancements**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4. Environment Configuration Management

**GitHub Secrets Required**:
- `RAILWAY_TOKEN`: Railway CLI authentication token
- `RAILWAY_PROJECT_ID_PROD`: Production project ID
- `RAILWAY_PROJECT_ID_STAGING`: Staging project ID

**Railway Environment Variables**:
- **Frontend**: `BACKEND_URL`, `ENVIRONMENT`
- **Backend**: `DATABASE_URL`, `CORS_ORIGINS`, `ENVIRONMENT`
- **Database**: Managed by Railway with automatic connection strings

## Data Models

### Railway Project Structure

```yaml
Production Project:
  services:
    - anime-frontend-prod
    - anime-backend-prod  
    - anime-database-prod

Staging Project:
  services:
    - anime-frontend-staging
    - anime-backend-staging
    - anime-database-staging
```

### Environment Variables Schema

```yaml
Frontend Service:
  BACKEND_URL: "https://anime-backend-prod.railway.app"
  ENVIRONMENT: "production"

Backend Service:
  DATABASE_URL: "postgresql://user:pass@host:port/db"
  CORS_ORIGINS: "https://anime-frontend-prod.railway.app"
  ENVIRONMENT: "production"
```

### Deployment Metadata

```yaml
deployment_info:
  commit_sha: string
  branch: string
  environment: "production" | "staging"
  services:
    frontend:
      url: string
      status: "deployed" | "failed"
    backend:
      url: string
      status: "deployed" | "failed"
    database:
      status: "ready" | "initializing"
```

## Error Handling

### Build Failures

**Docker Build Errors**:
- **Detection**: Exit code != 0 during docker build
- **Response**: Fail pipeline, log detailed error, notify team
- **Recovery**: Manual intervention required, check Dockerfile syntax

**Dependency Installation Errors**:
- **Detection**: pip install or npm install failures
- **Response**: Fail pipeline, cache cleanup, retry once
- **Recovery**: Update requirements.txt or package.json

### Deployment Failures

**Railway Service Deployment Errors**:
- **Detection**: Railway CLI deployment command fails
- **Response**: Rollback to previous version, maintain service availability
- **Recovery**: Investigate Railway logs, fix configuration issues

**Database Connection Errors**:
- **Detection**: Backend health check fails to connect to database
- **Response**: Retry deployment with exponential backoff
- **Recovery**: Verify DATABASE_URL, check Railway database service status

**Service Communication Errors**:
- **Detection**: Frontend cannot reach backend API
- **Response**: Verify internal Railway networking, check CORS configuration
- **Recovery**: Update environment variables, redeploy affected services

### Runtime Monitoring

**Health Check Endpoints**:
- **Backend**: `GET /health` - Database connectivity and service status
- **Frontend**: HTTP 200 response from Nginx
- **Database**: Railway managed monitoring

**Failure Notifications**:
- **GitHub Status Checks**: Commit status updates
- **Deployment Logs**: Detailed error information in GitHub Actions logs
- **Railway Dashboard**: Service status and logs

## Testing Strategy

### Pre-Deployment Validation

**Docker Image Validation**:
```bash
# Frontend validation
docker run --rm frontend-image nginx -t

# Backend validation  
docker run --rm backend-image python -c "import main; print('OK')"
```

**API Health Checks**:
```bash
# Backend API validation
curl -f http://localhost:8000/health || exit 1

# Database connection test
python -c "from main import engine; engine.connect()" || exit 1
```

### Post-Deployment Verification

**Service Availability Tests**:
- **Frontend**: HTTP GET to Railway frontend URL, expect 200
- **Backend**: HTTP GET to `/health` endpoint, expect 200 with valid JSON
- **Database**: Backend health check includes database connectivity test

**Integration Tests**:
- **API Endpoints**: Test CRUD operations on `/animes` endpoints
- **Frontend-Backend Communication**: Verify frontend can fetch data from backend
- **Database Persistence**: Verify data survives service restarts

### Rollback Strategy

**Automatic Rollback Triggers**:
- Health checks fail for more than 5 minutes
- Service deployment fails during Railway deployment phase
- Critical API endpoints return 5xx errors consistently

**Rollback Process**:
1. Identify last known good deployment
2. Redeploy previous version using Railway CLI
3. Verify service health after rollback
4. Notify team of rollback action and investigation needed

**Manual Rollback**:
- GitHub Actions workflow with manual trigger
- Specify commit SHA or tag to rollback to
- Execute same deployment process with previous version