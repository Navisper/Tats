#!/usr/bin/env python3
"""
Environment Configuration Setup Script

This script helps set up environment-specific configuration for Railway deployment.
It reads environment templates and provides utilities for managing configuration.
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

def load_env_file(file_path: Path) -> Dict[str, str]:
    """Load environment variables from a .env file"""
    env_vars = {}
    
    if not file_path.exists():
        print(f"Warning: Environment file {file_path} does not exist")
        return env_vars
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                env_vars[key] = value
            else:
                print(f"Warning: Invalid line format at {file_path}:{line_num}: {line}")
    
    return env_vars

def validate_required_vars(env_vars: Dict[str, str], environment: str) -> List[str]:
    """Validate that required environment variables are set"""
    required_vars = [
        'RAILWAY_TOKEN',
        f'RAILWAY_PROJECT_ID_{environment.upper()}',
        'ENVIRONMENT',
        f'CORS_ORIGINS_{environment.upper()}',
    ]
    
    missing_vars = []
    for var in required_vars:
        if var not in env_vars or env_vars[var].startswith('your_') or not env_vars[var].strip():
            missing_vars.append(var)
    
    return missing_vars

def generate_cors_config(environment: str, frontend_url: str, additional_origins: List[str] = None) -> Dict[str, str]:
    """Generate CORS configuration for the specified environment"""
    cors_config = {}
    
    # Base CORS origins
    cors_origins = [frontend_url]
    
    # Add additional origins based on environment
    if environment == "staging":
        # More permissive for staging
        cors_origins.extend([
            "http://localhost:3000",
            "http://localhost:8080", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080"
        ])
        cors_config[f'CORS_ALLOWED_METHODS'] = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
        cors_config[f'CORS_ALLOWED_HEADERS'] = "Content-Type,Authorization,X-Requested-With,X-Debug-Mode"
        cors_config[f'CORS_MAX_AGE'] = "3600"
    else:  # production
        # Strict for production
        cors_config[f'CORS_ALLOWED_METHODS'] = "GET,POST,PUT,DELETE,OPTIONS"
        cors_config[f'CORS_ALLOWED_HEADERS'] = "Content-Type,Authorization,X-Requested-With"
        cors_config[f'CORS_MAX_AGE'] = "86400"
    
    # Add any additional origins
    if additional_origins:
        cors_origins.extend(additional_origins)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_origins = []
    for origin in cors_origins:
        if origin not in seen:
            seen.add(origin)
            unique_origins.append(origin)
    
    cors_config[f'CORS_ORIGINS_{environment.upper()}'] = ",".join(unique_origins)
    cors_config[f'CORS_ALLOW_CREDENTIALS'] = "true"
    
    return cors_config

def print_environment_summary(env_vars: Dict[str, str], environment: str):
    """Print a summary of the environment configuration"""
    print(f"\n=== {environment.upper()} Environment Configuration Summary ===")
    
    # Core configuration
    print(f"Environment: {env_vars.get('ENVIRONMENT', 'Not set')}")
    print(f"Debug Mode: {env_vars.get('DEBUG', 'Not set')}")
    print(f"Log Level: {env_vars.get('LOG_LEVEL', 'Not set')}")
    
    # Service URLs
    print(f"\nService URLs:")
    print(f"  Frontend: {env_vars.get(f'FRONTEND_URL_{environment.upper()}', 'Not set')}")
    print(f"  Backend: {env_vars.get(f'BACKEND_URL_{environment.upper()}', 'Not set')}")
    
    # CORS Configuration
    print(f"\nCORS Configuration:")
    cors_origins = env_vars.get(f'CORS_ORIGINS_{environment.upper()}', 'Not set')
    if cors_origins != 'Not set':
        origins_list = cors_origins.split(',')
        print(f"  Allowed Origins ({len(origins_list)}):")
        for origin in origins_list:
            print(f"    - {origin.strip()}")
    else:
        print(f"  Allowed Origins: Not set")
    
    print(f"  Allow Credentials: {env_vars.get('CORS_ALLOW_CREDENTIALS', 'Not set')}")
    print(f"  Allowed Methods: {env_vars.get('CORS_ALLOWED_METHODS', 'Not set')}")
    print(f"  Max Age: {env_vars.get('CORS_MAX_AGE', 'Not set')}")
    
    # Database Configuration
    print(f"\nDatabase Configuration:")
    print(f"  Database Name: {env_vars.get('DB_NAME', 'Not set')}")
    print(f"  Pool Size: {env_vars.get('DB_POOL_SIZE', 'Not set')}")
    
    # Security Configuration
    print(f"\nSecurity Configuration:")
    print(f"  Secure Headers: {env_vars.get('SECURE_HEADERS', 'Not set')}")
    print(f"  Force HTTPS: {env_vars.get('FORCE_HTTPS', 'Not set')}")

def export_github_secrets(env_vars: Dict[str, str], environment: str) -> Dict[str, str]:
    """Export environment variables that should be set as GitHub secrets"""
    github_secrets = {}
    
    # Core secrets that should be in GitHub
    secret_keys = [
        'RAILWAY_TOKEN',
        f'RAILWAY_PROJECT_ID_{environment.upper()}',
    ]
    
    for key in secret_keys:
        if key in env_vars and not env_vars[key].startswith('your_'):
            github_secrets[key] = env_vars[key]
    
    return github_secrets

def main():
    parser = argparse.ArgumentParser(description='Environment Configuration Setup')
    parser.add_argument('--environment', '-e', choices=['staging', 'production'], 
                       required=True, help='Environment to configure')
    parser.add_argument('--validate', '-v', action='store_true', 
                       help='Validate environment configuration')
    parser.add_argument('--summary', '-s', action='store_true', 
                       help='Show environment configuration summary')
    parser.add_argument('--export-secrets', action='store_true',
                       help='Export GitHub secrets configuration')
    parser.add_argument('--generate-cors', action='store_true',
                       help='Generate CORS configuration')
    parser.add_argument('--frontend-url', help='Frontend URL for CORS configuration')
    parser.add_argument('--additional-origins', nargs='*', 
                       help='Additional CORS origins')
    
    args = parser.parse_args()
    
    # Determine paths
    script_dir = Path(__file__).parent
    config_dir = script_dir / 'config'
    env_file = config_dir / f'{args.environment}.env'
    
    # Load environment configuration
    env_vars = load_env_file(env_file)
    
    if not env_vars:
        print(f"Error: Could not load environment configuration from {env_file}")
        sys.exit(1)
    
    # Validate configuration
    if args.validate:
        print(f"Validating {args.environment} environment configuration...")
        missing_vars = validate_required_vars(env_vars, args.environment)
        
        if missing_vars:
            print(f"❌ Missing or invalid required variables:")
            for var in missing_vars:
                print(f"  - {var}")
            print(f"\nPlease update {env_file} with the correct values.")
            sys.exit(1)
        else:
            print(f"✅ All required variables are configured for {args.environment}")
    
    # Show summary
    if args.summary:
        print_environment_summary(env_vars, args.environment)
    
    # Export GitHub secrets
    if args.export_secrets:
        secrets = export_github_secrets(env_vars, args.environment)
        print(f"\n=== GitHub Secrets for {args.environment.upper()} ===")
        if secrets:
            for key, value in secrets.items():
                # Mask the value for security
                masked_value = value[:8] + "..." if len(value) > 8 else "***"
                print(f"{key}={masked_value}")
            
            print(f"\nTo set these secrets in GitHub:")
            print(f"1. Go to your repository Settings > Secrets and variables > Actions")
            print(f"2. Add each secret with the exact name and value shown above")
        else:
            print("No secrets found to export (values may not be configured)")
    
    # Generate CORS configuration
    if args.generate_cors:
        if not args.frontend_url:
            print("Error: --frontend-url is required when generating CORS configuration")
            sys.exit(1)
        
        cors_config = generate_cors_config(
            args.environment, 
            args.frontend_url, 
            args.additional_origins
        )
        
        print(f"\n=== Generated CORS Configuration for {args.environment.upper()} ===")
        for key, value in cors_config.items():
            print(f"{key}={value}")

if __name__ == '__main__':
    main()