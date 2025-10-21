#!/usr/bin/env python3
"""
Deployment status reporting and logging script for Railway CI/CD
Provides structured logging and status reporting for deployment processes
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentStatusReporter:
    """Deployment status reporter for Railway CI/CD pipeline"""
    
    def __init__(self, environment: str, commit_sha: str, branch: str):
        self.environment = environment
        self.commit_sha = commit_sha
        self.branch = branch
        self.start_time = time.time()
        self.deployment_log = []
        
    def log_event(self, event_type: str, message: str, status: str = "info", details: Optional[Dict[str, Any]] = None):
        """Log a deployment event"""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "message": message,
            "status": status,
            "details": details or {}
        }
        
        self.deployment_log.append(event)
        
        # Also log to console
        if status == "error":
            logger.error(f"[{event_type}] {message}")
        elif status == "warning":
            logger.warning(f"[{event_type}] {message}")
        else:
            logger.info(f"[{event_type}] {message}")
    
    def log_service_deployment(self, service_name: str, status: str, url: Optional[str] = None, error: Optional[str] = None):
        """Log service deployment status"""
        details = {
            "service": service_name,
            "url": url,
            "error": error
        }
        
        if status == "success":
            message = f"Service {service_name} deployed successfully"
            if url:
                message += f" at {url}"
        elif status == "failed":
            message = f"Service {service_name} deployment failed"
            if error:
                message += f": {error}"
        else:
            message = f"Service {service_name} deployment {status}"
        
        self.log_event("service_deployment", message, status, details)
    
    def log_health_check(self, service_name: str, status: str, response_time: Optional[float] = None, error: Optional[str] = None):
        """Log health check result"""
        details = {
            "service": service_name,
            "response_time": response_time,
            "error": error
        }
        
        if status == "success":
            message = f"Health check passed for {service_name}"
            if response_time:
                message += f" ({response_time}ms)"
        elif status == "failed":
            message = f"Health check failed for {service_name}"
            if error:
                message += f": {error}"
        else:
            message = f"Health check {status} for {service_name}"
        
        self.log_event("health_check", message, status, details)
    
    def generate_deployment_summary(self) -> Dict[str, Any]:
        """Generate comprehensive deployment summary"""
        total_time = round((time.time() - self.start_time) * 1000, 2)
        
        # Analyze deployment log
        events_by_type = {}
        events_by_status = {"success": 0, "failed": 0, "warning": 0, "info": 0}
        
        for event in self.deployment_log:
            event_type = event["event_type"]
            status = event["status"]
            
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
            
            if status in events_by_status:
                events_by_status[status] += 1
        
        # Determine overall status
        overall_status = "success"
        if events_by_status["failed"] > 0:
            overall_status = "failed"
        elif events_by_status["warning"] > 0:
            overall_status = "warning"
        
        # Extract service information
        services = {}
        for event in self.deployment_log:
            if event["event_type"] == "service_deployment":
                service_name = event["details"].get("service", "unknown")
                services[service_name] = {
                    "status": event["status"],
                    "url": event["details"].get("url"),
                    "error": event["details"].get("error")
                }
        
        # Extract health check information
        health_checks = {}
        for event in self.deployment_log:
            if event["event_type"] == "health_check":
                service_name = event["details"].get("service", "unknown")
                health_checks[service_name] = {
                    "status": event["status"],
                    "response_time": event["details"].get("response_time"),
                    "error": event["details"].get("error")
                }
        
        summary = {
            "deployment_info": {
                "environment": self.environment,
                "commit_sha": self.commit_sha,
                "branch": self.branch,
                "start_time": datetime.fromtimestamp(self.start_time, timezone.utc).isoformat(),
                "total_time_ms": total_time
            },
            "overall_status": overall_status,
            "events_summary": events_by_status,
            "services": services,
            "health_checks": health_checks,
            "deployment_log": self.deployment_log
        }
        
        return summary
    
    def generate_markdown_report(self) -> str:
        """Generate markdown deployment report"""
        summary = self.generate_deployment_summary()
        
        # Status emoji mapping
        status_emoji = {
            "success": "✅",
            "failed": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        
        overall_emoji = status_emoji.get(summary["overall_status"], "❓")
        
        report = f"""# 🚀 Railway Deployment Report

## Overall Status: {overall_emoji} {summary["overall_status"].upper()}

### Deployment Information
- **Environment**: {summary["deployment_info"]["environment"]}
- **Commit**: {summary["deployment_info"]["commit_sha"][:8]}
- **Branch**: {summary["deployment_info"]["branch"]}
- **Duration**: {summary["deployment_info"]["total_time_ms"]}ms
- **Started**: {summary["deployment_info"]["start_time"]}

### Event Summary
- **Success**: {summary["events_summary"]["success"]} events
- **Failed**: {summary["events_summary"]["failed"]} events
- **Warnings**: {summary["events_summary"]["warning"]} events
- **Info**: {summary["events_summary"]["info"]} events

### Services Deployed
"""
        
        for service_name, service_info in summary["services"].items():
            status_icon = status_emoji.get(service_info["status"], "❓")
            report += f"- **{service_name}**: {status_icon} {service_info['status']}"
            
            if service_info["url"]:
                report += f" - [{service_info['url']}]({service_info['url']})"
            
            if service_info["error"]:
                report += f"\n  - Error: {service_info['error']}"
            
            report += "\n"
        
        if summary["health_checks"]:
            report += "\n### Health Check Results\n"
            
            for service_name, health_info in summary["health_checks"].items():
                status_icon = status_emoji.get(health_info["status"], "❓")
                report += f"- **{service_name}**: {status_icon} {health_info['status']}"
                
                if health_info["response_time"]:
                    report += f" ({health_info['response_time']}ms)"
                
                if health_info["error"]:
                    report += f"\n  - Error: {health_info['error']}"
                
                report += "\n"
        
        # Add recent events
        if summary["deployment_log"]:
            report += "\n### Recent Events\n"
            
            # Show last 10 events
            recent_events = summary["deployment_log"][-10:]
            
            for event in recent_events:
                timestamp = event["timestamp"][:19]  # Remove timezone info for brevity
                status_icon = status_emoji.get(event["status"], "❓")
                report += f"- `{timestamp}` {status_icon} **{event['event_type']}**: {event['message']}\n"
        
        return report
    
    def save_report(self, filename: str, format: str = "json"):
        """Save deployment report to file"""
        if format == "json":
            summary = self.generate_deployment_summary()
            with open(filename, 'w') as f:
                json.dump(summary, f, indent=2)
        elif format == "markdown":
            report = self.generate_markdown_report()
            with open(filename, 'w') as f:
                f.write(report)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Deployment report saved to {filename}")

def main():
    """Main deployment status script entry point"""
    parser = argparse.ArgumentParser(description="Deployment Status Reporter")
    parser.add_argument("--environment", required=True, help="Deployment environment")
    parser.add_argument("--commit-sha", required=True, help="Git commit SHA")
    parser.add_argument("--branch", required=True, help="Git branch name")
    parser.add_argument("--action", required=True, choices=["log-event", "log-service", "log-health", "generate-report"])
    
    # Event logging arguments
    parser.add_argument("--event-type", help="Event type for log-event action")
    parser.add_argument("--message", help="Event message")
    parser.add_argument("--status", default="info", choices=["success", "failed", "warning", "info"], help="Event status")
    
    # Service logging arguments
    parser.add_argument("--service-name", help="Service name")
    parser.add_argument("--service-url", help="Service URL")
    parser.add_argument("--error", help="Error message")
    
    # Health check arguments
    parser.add_argument("--response-time", type=float, help="Response time in milliseconds")
    
    # Report generation arguments
    parser.add_argument("--output-file", help="Output file for report")
    parser.add_argument("--format", default="json", choices=["json", "markdown"], help="Report format")
    parser.add_argument("--load-log", help="Load existing deployment log file")
    
    args = parser.parse_args()
    
    # Create reporter
    reporter = DeploymentStatusReporter(args.environment, args.commit_sha, args.branch)
    
    # Load existing log if specified
    if args.load_log and os.path.exists(args.load_log):
        try:
            with open(args.load_log, 'r') as f:
                existing_data = json.load(f)
                reporter.deployment_log = existing_data.get("deployment_log", [])
                logger.info(f"Loaded {len(reporter.deployment_log)} existing events")
        except Exception as e:
            logger.warning(f"Failed to load existing log: {e}")
    
    # Execute action
    if args.action == "log-event":
        if not args.event_type or not args.message:
            logger.error("--event-type and --message are required for log-event action")
            sys.exit(1)
        
        reporter.log_event(args.event_type, args.message, args.status)
        
    elif args.action == "log-service":
        if not args.service_name:
            logger.error("--service-name is required for log-service action")
            sys.exit(1)
        
        reporter.log_service_deployment(args.service_name, args.status, args.service_url, args.error)
        
    elif args.action == "log-health":
        if not args.service_name:
            logger.error("--service-name is required for log-health action")
            sys.exit(1)
        
        reporter.log_health_check(args.service_name, args.status, args.response_time, args.error)
        
    elif args.action == "generate-report":
        if args.format == "json":
            summary = reporter.generate_deployment_summary()
            if args.output_file:
                reporter.save_report(args.output_file, "json")
            else:
                print(json.dumps(summary, indent=2))
        else:
            report = reporter.generate_markdown_report()
            if args.output_file:
                reporter.save_report(args.output_file, "markdown")
            else:
                print(report)
    
    # Always save current state if output file specified
    if args.output_file and args.action != "generate-report":
        reporter.save_report(args.output_file, "json")

if __name__ == "__main__":
    main()