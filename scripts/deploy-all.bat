@echo off
REM Master Railway Deployment Script for Windows
REM Orchestrates deployment of all services (database, backend, frontend)

setlocal enabledelayedexpansion

REM Color codes (limited in batch)
set "INFO=[INFO]"
set "SUCCESS=[SUCCESS]"
set "WARNING=[WARNING]"
set "ERROR=[ERROR]"
set "DEPLOY=[DEPLOY]"

REM Get script directory
set "SCRIPT_DIR=%~dp0"

REM Validate environment
if "%ENVIRONMENT%"=="" (
    echo %ERROR% ENVIRONMENT variable is required ^(staging/production^)
    exit /b 1
)

if not "%ENVIRONMENT%"=="staging" if not "%ENVIRONMENT%"=="production" (
    echo %ERROR% ENVIRONMENT must be either 'staging' or 'production'
    exit /b 1
)

REM Check if Railway CLI is installed
railway --version >nul 2>&1
if errorlevel 1 (
    echo %ERROR% Railway CLI is not installed. Please install it first:
    echo %ERROR% npm install -g @railway/cli
    exit /b 1
)

echo %INFO% Environment validation passed: %ENVIRONMENT%

REM Load environment configuration
set "CONFIG_FILE=%SCRIPT_DIR%config\%ENVIRONMENT%.env"
if exist "%CONFIG_FILE%" (
    echo %INFO% Loading configuration from: %CONFIG_FILE%
    REM Note: Batch doesn't have source equivalent, would need PowerShell for full env loading
    echo %SUCCESS% Configuration file found
) else (
    echo %WARNING% Configuration file not found: %CONFIG_FILE%
    echo %WARNING% Using environment variables only
)

REM Handle arguments
if "%1"=="database" goto deploy_database
if "%1"=="db" goto deploy_database
if "%1"=="backend" goto deploy_backend
if "%1"=="api" goto deploy_backend
if "%1"=="frontend" goto deploy_frontend
if "%1"=="web" goto deploy_frontend
if "%1"=="help" goto show_help
if "%1"=="-h" goto show_help
if "%1"=="--help" goto show_help
if not "%1"=="" (
    echo %ERROR% Unknown service: %1
    echo %ERROR% Use '%0 help' for usage information
    exit /b 1
)

REM Deploy all services
echo.
echo %DEPLOY% RAILWAY DEPLOYMENT ORCHESTRATION
echo %DEPLOY% Environment: %ENVIRONMENT%
echo %DEPLOY% Timestamp: %date% %time%
echo.

:deploy_all
echo %DEPLOY% STEP 1/3: Deploying Database Service
call "%SCRIPT_DIR%deploy-database.bat"
if errorlevel 1 (
    echo %ERROR% Database deployment failed
    exit /b 1
)
echo %SUCCESS% Database deployment completed
echo.

echo %DEPLOY% STEP 2/3: Deploying Backend Service
call "%SCRIPT_DIR%deploy-backend.bat"
if errorlevel 1 (
    echo %ERROR% Backend deployment failed
    exit /b 1
)
echo %SUCCESS% Backend deployment completed
echo.

echo %DEPLOY% STEP 3/3: Deploying Frontend Service
call "%SCRIPT_DIR%deploy-frontend.bat"
if errorlevel 1 (
    echo %ERROR% Frontend deployment failed
    exit /b 1
)
echo %SUCCESS% Frontend deployment completed
echo.

echo %SUCCESS% All services deployed successfully!
goto end

:deploy_database
echo %DEPLOY% Deploying Database Only
call "%SCRIPT_DIR%deploy-database.bat"
goto end

:deploy_backend
echo %DEPLOY% Deploying Backend Only
call "%SCRIPT_DIR%deploy-backend.bat"
goto end

:deploy_frontend
echo %DEPLOY% Deploying Frontend Only
call "%SCRIPT_DIR%deploy-frontend.bat"
goto end

:show_help
echo Usage: %0 [service]
echo.
echo Services:
echo   database, db     Deploy database service only
echo   backend, api     Deploy backend service only
echo   frontend, web    Deploy frontend service only
echo   ^(no argument^)    Deploy all services
echo.
echo Environment variables:
echo   ENVIRONMENT      Required: 'staging' or 'production'
echo   RAILWAY_TOKEN    Required: Railway authentication token
echo.
goto end

:end
endlocal