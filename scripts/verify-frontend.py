#!/usr/bin/env python3
"""
Frontend service health verification script for Railway deployment
Focuses specifically on frontend accessibility and static file serving
"""

import os
import sys
import json
import time
import argparse
import requests
from typing import Dict, Any, List
from urllib.parse import urljoin, urlparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FrontendHealthChecker:
    """Specialized health checker for frontend service"""
    
    def __init__(self, frontend_url: str, timeout: int = 30):
        self.frontend_url = frontend_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.timeout = timeout
        
        # Set user agent to simulate browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Railway-HealthCheck/1.0)'
        })
    
    def check_basic_accessibility(self) -> Dict[str, Any]:
        """Check basic frontend accessibility"""
        result = {
            "test": "basic_accessibility",
            "success": False,
            "response_time": None,
            "status_code": None,
            "content_length": None,
            "content_type": None,
            "error": None
        }
        
        try:
            logger.info(f"Testing basic accessibility: {self.frontend_url}")
            start_time = time.time()
            
            response = self.session.get(self.frontend_url)
            
            result["response_time"] = round((time.time() - start_time) * 1000, 2)
            result["status_code"] = response.status_code
            result["content_length"] = len(response.content)
            result["content_type"] = response.headers.get('content-type', '')
            
            if response.status_code == 200:
                result["success"] = True
                logger.info(f"✓ Frontend accessible (HTTP {response.status_code})")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
                logger.error(f"✗ Frontend not accessible: {result['error']}")
        
        except requests.exceptions.Timeout:
            result["error"] = f"Request timeout after {self.timeout}s"
            logger.error(f"✗ Frontend accessibility test failed: {result['error']}")
        except requests.exceptions.ConnectionError as e:
            result["error"] = f"Connection error: {str(e)}"
            logger.error(f"✗ Frontend accessibility test failed: {result['error']}")
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"✗ Frontend accessibility test failed: {result['error']}")
        
        return result
    
    def check_html_content(self) -> Dict[str, Any]:
        """Check if frontend serves valid HTML content"""
        result = {
            "test": "html_content",
            "success": False,
            "has_doctype": False,
            "has_html_tag": False,
            "has_head": False,
            "has_body": False,
            "has_title": False,
            "title": None,
            "error": None
        }
        
        try:
            logger.info("Testing HTML content structure...")
            response = self.session.get(self.frontend_url)
            
            if response.status_code == 200:
                content = response.text.lower()
                
                # Check HTML structure
                result["has_doctype"] = 'doctype' in content
                result["has_html_tag"] = '<html' in content
                result["has_head"] = '<head' in content
                result["has_body"] = '<body' in content
                result["has_title"] = '<title' in content
                
                # Extract title if present
                if result["has_title"]:
                    try:
                        title_start = response.text.find('<title>') + 7
                        title_end = response.text.find('</title>')
                        if title_start > 6 and title_end > title_start:
                            result["title"] = response.text[title_start:title_end].strip()
                    except Exception:
                        pass
                
                # Overall success if basic HTML structure is present
                if result["has_html_tag"] and (result["has_head"] or result["has_body"]):
                    result["success"] = True
                    logger.info("✓ Frontend serves valid HTML content")
                else:
                    result["error"] = "Content does not appear to be valid HTML"
                    logger.warning("⚠ Frontend content validation failed")
            else:
                result["error"] = f"HTTP {response.status_code}: Cannot retrieve content"
                logger.error(f"✗ HTML content test failed: {result['error']}")
        
        except Exception as e:
            result["error"] = f"Failed to check HTML content: {str(e)}"
            logger.error(f"✗ HTML content test failed: {result['error']}")
        
        return result
    
    def check_static_assets(self) -> Dict[str, Any]:
        """Check for static assets and their accessibility"""
        result = {
            "test": "static_assets",
            "success": False,
            "assets_found": [],
            "assets_tested": [],
            "accessible_assets": 0,
            "total_assets": 0,
            "error": None
        }
        
        try:
            logger.info("Testing static assets...")
            response = self.session.get(self.frontend_url)
            
            if response.status_code == 200:
                content = response.text
                
                # Look for common static asset references
                import re
                
                # Find CSS files
                css_matches = re.findall(r'href=["\']([^"\']*\.css[^"\']*)["\']', content, re.IGNORECASE)
                js_matches = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', content, re.IGNORECASE)
                img_matches = re.findall(r'src=["\']([^"\']*\.(png|jpg|jpeg|gif|svg|ico)[^"\']*)["\']', content, re.IGNORECASE)
                
                # Collect all assets
                all_assets = css_matches + js_matches + [match[0] for match in img_matches]
                result["assets_found"] = list(set(all_assets))  # Remove duplicates
                result["total_assets"] = len(result["assets_found"])
                
                if result["total_assets"] > 0:
                    logger.info(f"Found {result['total_assets']} static asset references")
                    
                    # Test accessibility of a few key assets (limit to avoid too many requests)
                    assets_to_test = result["assets_found"][:5]  # Test first 5 assets
                    
                    for asset_path in assets_to_test:
                        try:
                            # Handle relative URLs
                            if asset_path.startswith('//'):
                                asset_url = f"https:{asset_path}"
                            elif asset_path.startswith('/'):
                                asset_url = f"{self.frontend_url}{asset_path}"
                            elif not asset_path.startswith('http'):
                                asset_url = urljoin(self.frontend_url + '/', asset_path)
                            else:
                                asset_url = asset_path
                            
                            # Test asset accessibility
                            asset_response = self.session.head(asset_url, timeout=10)
                            
                            asset_result = {
                                "path": asset_path,
                                "url": asset_url,
                                "accessible": asset_response.status_code == 200,
                                "status_code": asset_response.status_code,
                                "content_type": asset_response.headers.get('content-type', '')
                            }
                            
                            result["assets_tested"].append(asset_result)
                            
                            if asset_result["accessible"]:
                                result["accessible_assets"] += 1
                        
                        except Exception as e:
                            result["assets_tested"].append({
                                "path": asset_path,
                                "accessible": False,
                                "error": str(e)
                            })
                    
                    # Success if we found assets and at least some are accessible
                    if result["accessible_assets"] > 0:
                        result["success"] = True
                        logger.info(f"✓ Static assets found and accessible ({result['accessible_assets']}/{len(result['assets_tested'])} tested)")
                    else:
                        result["error"] = "Static assets found but none are accessible"
                        logger.warning("⚠ Static assets not accessible")
                else:
                    # No assets found, but this might be okay for simple HTML pages
                    result["success"] = True
                    logger.info("ℹ No static assets found (simple HTML page)")
            else:
                result["error"] = f"HTTP {response.status_code}: Cannot retrieve content"
                logger.error(f"✗ Static assets test failed: {result['error']}")
        
        except Exception as e:
            result["error"] = f"Failed to check static assets: {str(e)}"
            logger.error(f"✗ Static assets test failed: {result['error']}")
        
        return result
    
    def check_backend_communication(self, backend_url: str) -> Dict[str, Any]:
        """Check if frontend can communicate with backend (CORS test)"""
        result = {
            "test": "backend_communication",
            "success": False,
            "backend_url": backend_url,
            "cors_headers": {},
            "api_accessible": False,
            "error": None
        }
        
        try:
            logger.info(f"Testing backend communication: {backend_url}")
            
            # Test CORS preflight request
            headers = {
                'Origin': self.frontend_url,
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            preflight_response = self.session.options(f"{backend_url}/animes", headers=headers)
            
            # Extract CORS headers
            cors_headers = {
                key: value for key, value in preflight_response.headers.items()
                if key.lower().startswith('access-control-')
            }
            result["cors_headers"] = cors_headers
            
            # Test actual API request
            api_response = self.session.get(f"{backend_url}/animes", headers={'Origin': self.frontend_url})
            result["api_accessible"] = api_response.status_code == 200
            
            # Check if CORS is properly configured
            allowed_origins = cors_headers.get('access-control-allow-origin', '')
            if allowed_origins == '*' or self.frontend_url in allowed_origins:
                result["success"] = True
                logger.info("✓ Backend communication and CORS configured correctly")
            else:
                result["error"] = f"CORS not configured for frontend origin: {self.frontend_url}"
                logger.warning(f"⚠ Backend communication test failed: {result['error']}")
        
        except Exception as e:
            result["error"] = f"Failed to test backend communication: {str(e)}"
            logger.error(f"✗ Backend communication test failed: {result['error']}")
        
        return result
    
    def run_comprehensive_frontend_check(self, backend_url: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive frontend health check"""
        logger.info("Starting comprehensive frontend health check...")
        
        start_time = time.time()
        
        # Run all tests
        tests = [
            self.check_basic_accessibility(),
            self.check_html_content(),
            self.check_static_assets()
        ]
        
        # Add backend communication test if backend URL provided
        if backend_url:
            tests.append(self.check_backend_communication(backend_url))
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        # Compile results
        successful_tests = sum(1 for test in tests if test["success"])
        total_tests = len(tests)
        
        results = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "frontend_url": self.frontend_url,
            "total_check_time": total_time,
            "overall_healthy": successful_tests == total_tests,
            "tests_passed": successful_tests,
            "total_tests": total_tests,
            "tests": tests,
            "summary": {
                "accessible": any(test["test"] == "basic_accessibility" and test["success"] for test in tests),
                "serves_html": any(test["test"] == "html_content" and test["success"] for test in tests),
                "static_assets_ok": any(test["test"] == "static_assets" and test["success"] for test in tests),
                "backend_communication_ok": any(test["test"] == "backend_communication" and test["success"] for test in tests) if backend_url else None
            }
        }
        
        # Log summary
        if results["overall_healthy"]:
            logger.info("✅ Frontend health check passed!")
        else:
            failed_tests = [test["test"] for test in tests if not test["success"]]
            logger.error(f"❌ Frontend health check failed. Failed tests: {', '.join(failed_tests)}")
        
        return results

def main():
    """Main frontend health check script entry point"""
    parser = argparse.ArgumentParser(description="Frontend Service Health Check")
    parser.add_argument(
        "--frontend-url",
        required=True,
        help="Frontend service URL"
    )
    parser.add_argument(
        "--backend-url",
        help="Backend service URL (for CORS testing)"
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
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    # Run frontend health check
    checker = FrontendHealthChecker(args.frontend_url, args.timeout)
    results = checker.run_comprehensive_frontend_check(args.backend_url)
    
    if args.json:
        print(json.dumps(results, indent=2))
    elif not args.quiet:
        # Human-readable output
        print(f"\n=== Frontend Health Check Results ===")
        print(f"Frontend URL: {results['frontend_url']}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Total check time: {results['total_check_time']}ms")
        print(f"Overall status: {'✅ HEALTHY' if results['overall_healthy'] else '❌ UNHEALTHY'}")
        print(f"Tests: {results['tests_passed']}/{results['total_tests']} passed")
        
        print(f"\nTest Results:")
        for test in results["tests"]:
            status = "✅ PASS" if test["success"] else "❌ FAIL"
            print(f"  {test['test']}: {status}")
            if not test["success"] and test.get("error"):
                print(f"    Error: {test['error']}")
    
    sys.exit(0 if results["overall_healthy"] else 1)

if __name__ == "__main__":
    main()