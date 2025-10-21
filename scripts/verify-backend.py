#!/usr/bin/env python3
"""
Backend API service health verification script for Railway deployment
Focuses specifically on API endpoints, database connectivity, and service health
"""

import os
import sys
import json
import time
import argparse
import requests
from typing import Dict, Any, List, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BackendHealthChecker:
    """Specialized health checker for backend API service"""
    
    def __init__(self, backend_url: str, timeout: int = 30):
        self.backend_url = backend_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.timeout = timeout
        
        # Set headers for API requests
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Railway-HealthCheck/1.0'
        })
    
    def check_basic_health_endpoint(self) -> Dict[str, Any]:
        """Check basic /health endpoint"""
        result = {
            "test": "basic_health_endpoint",
            "success": False,
            "response_time": None,
            "status_code": None,
            "health_data": {},
            "error": None
        }
        
        try:
            logger.info(f"Testing basic health endpoint: {self.backend_url}/health")
            start_time = time.time()
            
            response = self.session.get(f"{self.backend_url}/health")
            
            result["response_time"] = round((time.time() - start_time) * 1000, 2)
            result["status_code"] = response.status_code
            
            if response.status_code == 200:
                try:
                    health_data = response.json()
                    result["health_data"] = health_data
                    result["success"] = True
                    logger.info("✓ Basic health endpoint accessible")
                    
                    # Log key health information
                    if "status" in health_data:
                        logger.info(f"  Status: {health_data['status']}")
                    if "database" in health_data:
                        logger.info(f"  Database: {health_data['database']}")
                    if "version" in health_data:
                        logger.info(f"  Version: {health_data['version']}")
                
                except json.JSONDecodeError:
                    result["error"] = "Health endpoint returned non-JSON response"
                    logger.error(f"✗ Health endpoint test failed: {result['error']}")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
                logger.error(f"✗ Health endpoint test failed: {result['error']}")
        
        except requests.exceptions.Timeout:
            result["error"] = f"Request timeout after {self.timeout}s"
            logger.error(f"✗ Health endpoint test failed: {result['error']}")
        except requests.exceptions.ConnectionError as e:
            result["error"] = f"Connection error: {str(e)}"
            logger.error(f"✗ Health endpoint test failed: {result['error']}")
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"✗ Health endpoint test failed: {result['error']}")
        
        return result
    
    def check_detailed_health_endpoint(self) -> Dict[str, Any]:
        """Check detailed /health/detailed endpoint"""
        result = {
            "test": "detailed_health_endpoint",
            "success": False,
            "response_time": None,
            "status_code": None,
            "detailed_health": {},
            "database_health": {},
            "error": None
        }
        
        try:
            logger.info(f"Testing detailed health endpoint: {self.backend_url}/health/detailed")
            start_time = time.time()
            
            response = self.session.get(f"{self.backend_url}/health/detailed")
            
            result["response_time"] = round((time.time() - start_time) * 1000, 2)
            result["status_code"] = response.status_code
            
            if response.status_code == 200:
                try:
                    detailed_health = response.json()
                    result["detailed_health"] = detailed_health
                    result["success"] = True
                    logger.info("✓ Detailed health endpoint accessible")
                    
                    # Extract database health information
                    if "database" in detailed_health:
                        result["database_health"] = detailed_health["database"]
                        db_status = detailed_health["database"].get("status", "unknown")
                        logger.info(f"  Database status: {db_status}")
                
                except json.JSONDecodeError:
                    result["error"] = "Detailed health endpoint returned non-JSON response"
                    logger.error(f"✗ Detailed health endpoint test failed: {result['error']}")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
                logger.warning(f"⚠ Detailed health endpoint not available: {result['error']}")
        
        except requests.exceptions.RequestException as e:
            result["error"] = f"Request failed: {str(e)}"
            logger.warning(f"⚠ Detailed health endpoint not available: {result['error']}")
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"✗ Detailed health endpoint test failed: {result['error']}")
        
        return result
    
    def check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity through health endpoints"""
        result = {
            "test": "database_connectivity",
            "success": False,
            "connection_verified": False,
            "database_info": {},
            "error": None
        }
        
        try:
            logger.info("Testing database connectivity...")
            
            # Try database-specific health endpoint first
            try:
                response = self.session.get(f"{self.backend_url}/health/database")
                if response.status_code == 200:
                    db_health = response.json()
                    result["database_info"] = db_health
                    
                    if db_health.get("status") == "healthy":
                        result["connection_verified"] = True
                        result["success"] = True
                        logger.info("✓ Database connectivity verified through dedicated endpoint")
                    else:
                        result["error"] = f"Database health check failed: {db_health.get('status', 'unknown')}"
                        logger.error(f"✗ Database connectivity test failed: {result['error']}")
                else:
                    logger.debug("Database-specific health endpoint not available")
            
            except requests.exceptions.RequestException:
                logger.debug("Database-specific health endpoint not accessible")
            
            # Fallback to basic health endpoint
            if not result["success"]:
                response = self.session.get(f"{self.backend_url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    
                    if health_data.get("database") == "connected":
                        result["connection_verified"] = True
                        result["success"] = True
                        result["database_info"] = {"status": "connected"}
                        logger.info("✓ Database connectivity verified through basic health endpoint")
                    else:
                        result["error"] = "Database not connected according to health check"
                        logger.error(f"✗ Database connectivity test failed: {result['error']}")
                else:
                    result["error"] = f"Health endpoint returned {response.status_code}"
                    logger.error(f"✗ Database connectivity test failed: {result['error']}")
        
        except Exception as e:
            result["error"] = f"Failed to check database connectivity: {str(e)}"
            logger.error(f"✗ Database connectivity test failed: {result['error']}")
        
        return result
    
    def check_api_endpoints(self) -> Dict[str, Any]:
        """Check core API endpoints functionality"""
        result = {
            "test": "api_endpoints",
            "success": False,
            "endpoints_tested": 0,
            "endpoints_working": 0,
            "endpoint_results": {},
            "error": None
        }
        
        # Define endpoints to test
        endpoints_to_test = [
            {"path": "/animes", "method": "GET", "description": "List animes"},
            {"path": "/docs", "method": "GET", "description": "API documentation"},
            {"path": "/openapi.json", "method": "GET", "description": "OpenAPI schema"}
        ]
        
        try:
            logger.info("Testing API endpoints...")
            
            for endpoint in endpoints_to_test:
                endpoint_result = self._test_single_endpoint(
                    endpoint["path"], 
                    endpoint["method"], 
                    endpoint["description"]
                )
                
                result["endpoint_results"][endpoint["path"]] = endpoint_result
                result["endpoints_tested"] += 1
                
                if endpoint_result["success"]:
                    result["endpoints_working"] += 1
            
            # Success if at least core endpoints are working
            core_endpoints = ["/animes", "/docs"]
            core_working = sum(
                1 for path in core_endpoints 
                if result["endpoint_results"].get(path, {}).get("success", False)
            )
            
            if core_working >= 1:  # At least one core endpoint working
                result["success"] = True
                logger.info(f"✓ API endpoints working ({result['endpoints_working']}/{result['endpoints_tested']})")
            else:
                result["error"] = "No core API endpoints are working"
                logger.error(f"✗ API endpoints test failed: {result['error']}")
        
        except Exception as e:
            result["error"] = f"Failed to test API endpoints: {str(e)}"
            logger.error(f"✗ API endpoints test failed: {result['error']}")
        
        return result
    
    def _test_single_endpoint(self, path: str, method: str, description: str) -> Dict[str, Any]:
        """Test a single API endpoint"""
        endpoint_result = {
            "path": path,
            "method": method,
            "description": description,
            "success": False,
            "status_code": None,
            "response_time": None,
            "content_type": None,
            "error": None
        }
        
        try:
            logger.debug(f"Testing {method} {path} - {description}")
            start_time = time.time()
            
            url = f"{self.backend_url}{path}"
            
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url)
            else:
                response = self.session.request(method, url)
            
            endpoint_result["response_time"] = round((time.time() - start_time) * 1000, 2)
            endpoint_result["status_code"] = response.status_code
            endpoint_result["content_type"] = response.headers.get('content-type', '')
            
            # Consider 200-299 as success, 404 for optional endpoints as acceptable
            if 200 <= response.status_code < 300:
                endpoint_result["success"] = True
            elif response.status_code == 404 and path in ["/docs", "/openapi.json"]:
                # Optional endpoints - 404 is acceptable
                endpoint_result["success"] = True
                endpoint_result["error"] = "Endpoint not available (optional)"
            else:
                endpoint_result["error"] = f"HTTP {response.status_code}: {response.reason}"
        
        except requests.exceptions.Timeout:
            endpoint_result["error"] = f"Request timeout after {self.timeout}s"
        except requests.exceptions.RequestException as e:
            endpoint_result["error"] = f"Request failed: {str(e)}"
        except Exception as e:
            endpoint_result["error"] = f"Unexpected error: {str(e)}"
        
        return endpoint_result
    
    def check_crud_operations(self) -> Dict[str, Any]:
        """Test CRUD operations on the animes endpoint"""
        result = {
            "test": "crud_operations",
            "success": False,
            "operations_tested": 0,
            "operations_working": 0,
            "operation_results": {},
            "test_anime_id": None,
            "error": None
        }
        
        try:
            logger.info("Testing CRUD operations...")
            
            # Test CREATE (POST)
            create_result = self._test_create_anime()
            result["operation_results"]["create"] = create_result
            result["operations_tested"] += 1
            
            if create_result["success"]:
                result["operations_working"] += 1
                result["test_anime_id"] = create_result.get("anime_id")
                
                # Test READ (GET specific)
                if result["test_anime_id"]:
                    read_result = self._test_read_anime(result["test_anime_id"])
                    result["operation_results"]["read"] = read_result
                    result["operations_tested"] += 1
                    
                    if read_result["success"]:
                        result["operations_working"] += 1
                    
                    # Test UPDATE (PUT)
                    update_result = self._test_update_anime(result["test_anime_id"])
                    result["operation_results"]["update"] = update_result
                    result["operations_tested"] += 1
                    
                    if update_result["success"]:
                        result["operations_working"] += 1
                    
                    # Test DELETE
                    delete_result = self._test_delete_anime(result["test_anime_id"])
                    result["operation_results"]["delete"] = delete_result
                    result["operations_tested"] += 1
                    
                    if delete_result["success"]:
                        result["operations_working"] += 1
            
            # Success if at least read operations work
            if result["operations_working"] >= 1:
                result["success"] = True
                logger.info(f"✓ CRUD operations working ({result['operations_working']}/{result['operations_tested']})")
            else:
                result["error"] = "No CRUD operations are working"
                logger.error(f"✗ CRUD operations test failed: {result['error']}")
        
        except Exception as e:
            result["error"] = f"Failed to test CRUD operations: {str(e)}"
            logger.error(f"✗ CRUD operations test failed: {result['error']}")
        
        return result
    
    def _test_create_anime(self) -> Dict[str, Any]:
        """Test creating an anime"""
        result = {
            "operation": "create",
            "success": False,
            "anime_id": None,
            "status_code": None,
            "error": None
        }
        
        try:
            test_anime = {
                "title": "__health_check_test__",
                "genre": "Test",
                "episodes": 1
            }
            
            response = self.session.post(f"{self.backend_url}/animes", json=test_anime)
            result["status_code"] = response.status_code
            
            if response.status_code == 201:
                created_anime = response.json()
                result["anime_id"] = created_anime.get("id")
                result["success"] = True
                logger.debug(f"✓ Created test anime with ID: {result['anime_id']}")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
        
        except Exception as e:
            result["error"] = f"Create operation failed: {str(e)}"
        
        return result
    
    def _test_read_anime(self, anime_id: int) -> Dict[str, Any]:
        """Test reading a specific anime"""
        result = {
            "operation": "read",
            "success": False,
            "status_code": None,
            "error": None
        }
        
        try:
            response = self.session.get(f"{self.backend_url}/animes/{anime_id}")
            result["status_code"] = response.status_code
            
            if response.status_code == 200:
                anime_data = response.json()
                if anime_data.get("id") == anime_id:
                    result["success"] = True
                    logger.debug(f"✓ Read test anime with ID: {anime_id}")
                else:
                    result["error"] = "Returned anime ID doesn't match requested ID"
            else:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
        
        except Exception as e:
            result["error"] = f"Read operation failed: {str(e)}"
        
        return result
    
    def _test_update_anime(self, anime_id: int) -> Dict[str, Any]:
        """Test updating an anime"""
        result = {
            "operation": "update",
            "success": False,
            "status_code": None,
            "error": None
        }
        
        try:
            updated_anime = {
                "title": "__health_check_test_updated__",
                "genre": "Test Updated",
                "episodes": 2
            }
            
            response = self.session.put(f"{self.backend_url}/animes/{anime_id}", json=updated_anime)
            result["status_code"] = response.status_code
            
            if response.status_code == 200:
                result["success"] = True
                logger.debug(f"✓ Updated test anime with ID: {anime_id}")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
        
        except Exception as e:
            result["error"] = f"Update operation failed: {str(e)}"
        
        return result
    
    def _test_delete_anime(self, anime_id: int) -> Dict[str, Any]:
        """Test deleting an anime"""
        result = {
            "operation": "delete",
            "success": False,
            "status_code": None,
            "error": None
        }
        
        try:
            response = self.session.delete(f"{self.backend_url}/animes/{anime_id}")
            result["status_code"] = response.status_code
            
            if response.status_code == 204:
                result["success"] = True
                logger.debug(f"✓ Deleted test anime with ID: {anime_id}")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
        
        except Exception as e:
            result["error"] = f"Delete operation failed: {str(e)}"
        
        return result
    
    def run_comprehensive_backend_check(self, include_crud: bool = False) -> Dict[str, Any]:
        """Run comprehensive backend health check"""
        logger.info("Starting comprehensive backend health check...")
        
        start_time = time.time()
        
        # Run all tests
        tests = [
            self.check_basic_health_endpoint(),
            self.check_detailed_health_endpoint(),
            self.check_database_connectivity(),
            self.check_api_endpoints()
        ]
        
        # Add CRUD test if requested
        if include_crud:
            tests.append(self.check_crud_operations())
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        # Compile results
        successful_tests = sum(1 for test in tests if test["success"])
        total_tests = len(tests)
        
        # Critical tests that must pass
        critical_tests = ["basic_health_endpoint", "database_connectivity", "api_endpoints"]
        critical_passed = sum(
            1 for test in tests 
            if test["test"] in critical_tests and test["success"]
        )
        
        results = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "backend_url": self.backend_url,
            "total_check_time": total_time,
            "overall_healthy": critical_passed == len(critical_tests),
            "tests_passed": successful_tests,
            "total_tests": total_tests,
            "critical_tests_passed": critical_passed,
            "critical_tests_total": len(critical_tests),
            "tests": tests,
            "summary": {
                "health_endpoint_ok": any(test["test"] == "basic_health_endpoint" and test["success"] for test in tests),
                "database_connected": any(test["test"] == "database_connectivity" and test["success"] for test in tests),
                "api_endpoints_ok": any(test["test"] == "api_endpoints" and test["success"] for test in tests),
                "crud_operations_ok": any(test["test"] == "crud_operations" and test["success"] for test in tests) if include_crud else None
            }
        }
        
        # Log summary
        if results["overall_healthy"]:
            logger.info("✅ Backend health check passed!")
        else:
            failed_critical = [
                test["test"] for test in tests 
                if test["test"] in critical_tests and not test["success"]
            ]
            logger.error(f"❌ Backend health check failed. Failed critical tests: {', '.join(failed_critical)}")
        
        return results

def main():
    """Main backend health check script entry point"""
    parser = argparse.ArgumentParser(description="Backend API Service Health Check")
    parser.add_argument(
        "--backend-url",
        required=True,
        help="Backend service URL"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--include-crud",
        action="store_true",
        help="Include CRUD operations testing (may modify data)"
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
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    # Run backend health check
    checker = BackendHealthChecker(args.backend_url, args.timeout)
    results = checker.run_comprehensive_backend_check(args.include_crud)
    
    if args.json:
        print(json.dumps(results, indent=2))
    elif not args.quiet:
        # Human-readable output
        print(f"\n=== Backend Health Check Results ===")
        print(f"Backend URL: {results['backend_url']}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Total check time: {results['total_check_time']}ms")
        print(f"Overall status: {'✅ HEALTHY' if results['overall_healthy'] else '❌ UNHEALTHY'}")
        print(f"Tests: {results['tests_passed']}/{results['total_tests']} passed")
        print(f"Critical tests: {results['critical_tests_passed']}/{results['critical_tests_total']} passed")
        
        print(f"\nTest Results:")
        for test in results["tests"]:
            status = "✅ PASS" if test["success"] else "❌ FAIL"
            print(f"  {test['test']}: {status}")
            if not test["success"] and test.get("error"):
                print(f"    Error: {test['error']}")
    
    sys.exit(0 if results["overall_healthy"] else 1)

if __name__ == "__main__":
    main()