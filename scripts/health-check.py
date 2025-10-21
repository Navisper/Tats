#!/usr/bin/env python3
"""
Comprehensive health check script for Railway deployed services
Verifies frontend, backend, and database connectivity after deployment
"""

import os
import sys
import json
import time
import argparse
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceHealthChecker:
    """Health checker for Railway deployed services"""
    
    def __init__(self, frontend_url: str, backend_url: str, timeout: int = 30):
        self.frontend_url = frontend_url.rstrip('/')
        self.backend_url = backend_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.timeout = timeout
    
    def check_frontend_health(self) -> Dict[str, Any]:
        """Check frontend service health and accessibility"""
        result = {
            "service": "frontend",
            "url": self.frontend_url,
            "healthy": False,
            "response_time": None,
            "status_code": None,
            "content_type": None,
            "error": None,
            "checks": {
                "accessible": False,
                "serves_html": False,
                "static_assets": False
            }
        }
        
        try:
            start_time = time.time()
            
            # Test basic accessibility
            logger.info(f"Checking frontend accessibility: {self.frontend_url}")
            response = self.session.get(self.frontend_url)
            
            result["response_time"] = round((time.time() - start_time) * 1000, 2)
            result["status_code"] = response.status_code
            result["content_type"] = response.headers.get('content-type', '')
            
            if response.status_code == 200:
                result["checks"]["accessible"] = True
                
                # Check if HTML content is served
                content = response.text.lower()
                if 'html' in content or 'doctype' in content:
                    result["checks"]["serves_html"] = True
                    logger.info("✓ Frontend serves HTML content")
                
                # Check for static assets (CSS, JS references)
                if any(asset in content for asset in ['.css', '.js', 'stylesheet', 'script']):
                    result["checks"]["static_assets"] = True
                    logger.info("✓ Frontend includes static assets")
                
                # Overall health check
                if result["checks"]["accessible"] and result["checks"]["serves_html"]:
                    result["healthy"] = True
                    logger.info("✓ Frontend health check passed")
                else:
                    logger.warning("⚠ Frontend accessible but content validation failed")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
                logger.error(f"✗ Frontend health check failed: {result['error']}")
        
        except requests.exceptions.Timeout:
            result["error"] = f"Request timeout after {self.timeout}s"
            logger.error(f"✗ Frontend health check failed: {result['error']}")
        except requests.exceptions.ConnectionError as e:
            result["error"] = f"Connection error: {str(e)}"
            logger.error(f"✗ Frontend health check failed: {result['error']}")
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"✗ Frontend health check failed: {result['error']}")
        
        return result
    
    def check_backend_health(self) -> Dict[str, Any]:
        """Check backend service health and API endpoints"""
        result = {
            "service": "backend",
            "url": self.backend_url,
            "healthy": False,
            "response_time": None,
            "status_code": None,
            "error": None,
            "checks": {
                "accessible": False,
                "health_endpoint": False,
                "database_connected": False,
                "api_endpoints": False
            },
            "health_data": {},
            "api_tests": {}
        }
        
        try:
            # Test health endpoint
            logger.info(f"Checking backend health endpoint: {self.backend_url}/health")
            start_time = time.time()
            
            health_response = self.session.get(f"{self.backend_url}/health")
            result["response_time"] = round((time.time() - start_time) * 1000, 2)
            result["status_code"] = health_response.status_code
            
            if health_response.status_code == 200:
                result["checks"]["accessible"] = True
                result["checks"]["health_endpoint"] = True
                
                # Parse health response
                try:
                    health_data = health_response.json()
                    result["health_data"] = health_data
                    
                    # Check database connectivity
                    if health_data.get("database") == "connected":
                        result["checks"]["database_connected"] = True
                        logger.info("✓ Backend database connection verified")
                    else:
                        logger.warning("⚠ Backend database connection issue")
                    
                    logger.info("✓ Backend health endpoint accessible")
                    
                except json.JSONDecodeError:
                    logger.warning("⚠ Health endpoint returned non-JSON response")
            
            # Test API endpoints
            logger.info("Testing backend API endpoints...")
            api_tests = self._test_backend_api_endpoints()
            result["api_tests"] = api_tests
            
            if api_tests.get("animes_list", {}).get("success", False):
                result["checks"]["api_endpoints"] = True
                logger.info("✓ Backend API endpoints working")
            
            # Overall health assessment
            if (result["checks"]["accessible"] and 
                result["checks"]["health_endpoint"] and 
                result["checks"]["database_connected"]):
                result["healthy"] = True
                logger.info("✓ Backend health check passed")
            else:
                logger.warning("⚠ Backend partially healthy - some checks failed")
        
        except requests.exceptions.Timeout:
            result["error"] = f"Request timeout after {self.timeout}s"
            logger.error(f"✗ Backend health check failed: {result['error']}")
        except requests.exceptions.ConnectionError as e:
            result["error"] = f"Connection error: {str(e)}"
            logger.error(f"✗ Backend health check failed: {result['error']}")
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"✗ Backend health check failed: {result['error']}")
        
        return result
    
    def _test_backend_api_endpoints(self) -> Dict[str, Any]:
        """Test backend API endpoints functionality"""
        api_tests = {}
        
        # Test GET /animes
        try:
            logger.debug("Testing GET /animes endpoint")
            response = self.session.get(f"{self.backend_url}/animes")
            api_tests["animes_list"] = {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds() * 1000
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    api_tests["animes_list"]["count"] = len(data) if isinstance(data, list) else 0
                except json.JSONDecodeError:
                    api_tests["animes_list"]["error"] = "Invalid JSON response"
        
        except Exception as e:
            api_tests["animes_list"] = {
                "success": False,
                "error": str(e)
            }
        
        # Test API documentation endpoint
        try:
            logger.debug("Testing API documentation endpoint")
            response = self.session.get(f"{self.backend_url}/docs")
            api_tests["documentation"] = {
                "success": response.status_code == 200,
                "status_code": response.status_code
            }
        except Exception as e:
            api_tests["documentation"] = {
                "success": False,
                "error": str(e)
            }
        
        return api_tests
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database health through backend health endpoint"""
        result = {
            "service": "database",
            "healthy": False,
            "error": None,
            "checks": {
                "backend_connection": False,
                "detailed_health": False
            },
            "database_info": {}
        }
        
        try:
            # Get detailed health information from backend
            logger.info("Checking database health through backend...")
            
            # Try detailed health endpoint first
            try:
                response = self.session.get(f"{self.backend_url}/health/detailed")
                if response.status_code == 200:
                    detailed_health = response.json()
                    result["checks"]["detailed_health"] = True
                    
                    db_info = detailed_health.get("database", {})
                    result["database_info"] = db_info
                    
                    if db_info.get("status") == "healthy":
                        result["checks"]["backend_connection"] = True
                        result["healthy"] = True
                        logger.info("✓ Database health verified through detailed endpoint")
                    else:
                        logger.warning("⚠ Database health check shows issues")
            
            except requests.exceptions.RequestException:
                logger.debug("Detailed health endpoint not available, trying basic health")
            
            # Fallback to basic health endpoint
            if not result["checks"]["detailed_health"]:
                response = self.session.get(f"{self.backend_url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    
                    if health_data.get("database") == "connected":
                        result["checks"]["backend_connection"] = True
                        result["healthy"] = True
                        result["database_info"] = {"status": "connected"}
                        logger.info("✓ Database connectivity verified through basic health endpoint")
                    else:
                        result["error"] = "Database not connected according to backend health check"
                        logger.error(f"✗ Database health check failed: {result['error']}")
                else:
                    result["error"] = f"Backend health endpoint returned {response.status_code}"
                    logger.error(f"✗ Database health check failed: {result['error']}")
        
        except Exception as e:
            result["error"] = f"Failed to check database health: {str(e)}"
            logger.error(f"✗ Database health check failed: {result['error']}")
        
        return result
    
    def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check on all services"""
        logger.info("Starting comprehensive health check...")
        
        start_time = time.time()
        
        # Check all services
        frontend_health = self.check_frontend_health()
        backend_health = self.check_backend_health()
        database_health = self.check_database_health()
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        # Compile overall results
        results = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_check_time": total_time,
            "overall_healthy": (
                frontend_health["healthy"] and 
                backend_health["healthy"] and 
                database_health["healthy"]
            ),
            "services": {
                "frontend": frontend_health,
                "backend": backend_health,
                "database": database_health
            },
            "summary": {
                "healthy_services": sum([
                    frontend_health["healthy"],
                    backend_health["healthy"],
                    database_health["healthy"]
                ]),
                "total_services": 3,
                "issues": []
            }
        }
        
        # Collect issues
        for service_name, service_result in results["services"].items():
            if not service_result["healthy"]:
                error_msg = service_result.get("error", "Unknown error")
                results["summary"]["issues"].append(f"{service_name}: {error_msg}")
        
        # Log summary
        if results["overall_healthy"]:
            logger.info("✅ All services are healthy!")
        else:
            logger.error(f"❌ {len(results['summary']['issues'])} service(s) have issues:")
            for issue in results["summary"]["issues"]:
                logger.error(f"  - {issue}")
        
        return results

def main():
    """Main health check script entry point"""
    parser = argparse.ArgumentParser(description="Railway Services Health Check")
    parser.add_argument(
        "--frontend-url",
        help="Frontend service URL (defaults to FRONTEND_URL environment variable)"
    )
    parser.add_argument(
        "--backend-url", 
        help="Backend service URL (defaults to BACKEND_URL environment variable)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (exit code indicates success/failure)"
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=1,
        help="Number of retry attempts (default: 1)"
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=10,
        help="Delay between retries in seconds (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Get service URLs
    frontend_url = args.frontend_url or os.getenv("FRONTEND_URL")
    backend_url = args.backend_url or os.getenv("BACKEND_URL")
    
    if not frontend_url:
        if not args.quiet:
            print("ERROR: Frontend URL not provided. Set FRONTEND_URL environment variable or use --frontend-url", file=sys.stderr)
        sys.exit(1)
    
    if not backend_url:
        if not args.quiet:
            print("ERROR: Backend URL not provided. Set BACKEND_URL environment variable or use --backend-url", file=sys.stderr)
        sys.exit(1)
    
    # Run health checks with retries
    checker = ServiceHealthChecker(frontend_url, backend_url, args.timeout)
    
    for attempt in range(args.retry):
        if attempt > 0:
            if not args.quiet:
                logger.info(f"Retry attempt {attempt + 1}/{args.retry} after {args.retry_delay}s delay...")
            time.sleep(args.retry_delay)
        
        results = checker.run_comprehensive_health_check()
        
        if args.json:
            print(json.dumps(results, indent=2))
        elif not args.quiet:
            # Human-readable output
            print(f"\n=== Health Check Results ===")
            print(f"Timestamp: {results['timestamp']}")
            print(f"Total check time: {results['total_check_time']}ms")
            print(f"Overall status: {'✅ HEALTHY' if results['overall_healthy'] else '❌ UNHEALTHY'}")
            print(f"Services: {results['summary']['healthy_services']}/{results['summary']['total_services']} healthy")
            
            if results["summary"]["issues"]:
                print("\nIssues found:")
                for issue in results["summary"]["issues"]:
                    print(f"  - {issue}")
        
        # Exit if successful or on last attempt
        if results["overall_healthy"] or attempt == args.retry - 1:
            sys.exit(0 if results["overall_healthy"] else 1)

if __name__ == "__main__":
    main()