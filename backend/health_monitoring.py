"""
Health checks and monitoring for enterprise deployment.
Provides endpoints for load balancers and monitoring systems.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import psutil
import threading

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthChecker:
    """Monitor system and application health."""
    
    def __init__(self, db_engine=None):
        self.db_engine = db_engine
        self.last_check_time: Optional[datetime] = None
        self.check_lock = threading.RLock()
        self.issues: List[str] = []
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        with self.check_lock:
            status = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": HealthStatus.HEALTHY,
                "checks": {
                    "database": self._check_database(),
                    "memory": self._check_memory(),
                    "disk": self._check_disk(),
                    "cpu": self._check_cpu(),
                    "uptime": self._get_uptime()
                },
                "issues": self.issues.copy()
            }
            
            # Determine overall status
            check_statuses = [v.get("status") for v in status["checks"].values() 
                            if isinstance(v, dict) and "status" in v]
            
            if HealthStatus.UNHEALTHY in check_statuses:
                status["status"] = HealthStatus.UNHEALTHY
            elif HealthStatus.DEGRADED in check_statuses:
                status["status"] = HealthStatus.DEGRADED
            
            self.last_check_time = datetime.utcnow()
            return status
    
    def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and health."""
        try:
            if self.db_engine:
                with self.db_engine.connect() as conn:
                    result = conn.execute("SELECT 1")
                    if result.fetchone():
                        return {
                            "status": HealthStatus.HEALTHY,
                            "message": "Database connection successful"
                        }
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Database not configured"
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)[:100]}")
            self.issues.append(f"Database error: {str(e)[:100]}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Database connection failed: {str(e)[:50]}"
            }
    
    def _check_memory(self) -> Dict[str, Any]:
        """Check system memory usage."""
        try:
            memory = psutil.virtual_memory()
            percent_used = memory.percent
            
            if percent_used > 90:
                self.issues.append(f"Memory usage critical: {percent_used:.1f}%")
                status = HealthStatus.UNHEALTHY
            elif percent_used > 75:
                self.issues.append(f"Memory usage high: {percent_used:.1f}%")
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                "status": status,
                "percent_used": percent_used,
                "available_mb": memory.available / 1024 / 1024,
                "total_mb": memory.total / 1024 / 1024
            }
        except Exception as e:
            logger.warning(f"Memory check failed: {str(e)[:50]}")
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Could not check memory"
            }
    
    def _check_disk(self) -> Dict[str, Any]:
        """Check disk space usage."""
        try:
            disk = psutil.disk_usage('/')
            percent_used = disk.percent
            
            if percent_used > 90:
                self.issues.append(f"Disk usage critical: {percent_used:.1f}%")
                status = HealthStatus.UNHEALTHY
            elif percent_used > 75:
                self.issues.append(f"Disk usage high: {percent_used:.1f}%")
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                "status": status,
                "percent_used": percent_used,
                "free_gb": disk.free / 1024 / 1024 / 1024,
                "total_gb": disk.total / 1024 / 1024 / 1024
            }
        except Exception as e:
            logger.warning(f"Disk check failed: {str(e)[:50]}")
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Could not check disk"
            }
    
    def _check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            
            if cpu_percent > 90:
                self.issues.append(f"CPU usage critical: {cpu_percent:.1f}%")
                status = HealthStatus.UNHEALTHY
            elif cpu_percent > 75:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            result = {
                "status": status,
                "percent": cpu_percent,
                "cores": psutil.cpu_count()
            }
            
            if load_avg:
                result["load_average"] = load_avg
            
            return result
        except Exception as e:
            logger.warning(f"CPU check failed: {str(e)[:50]}")
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Could not check CPU"
            }
    
    def _get_uptime(self) -> Dict[str, Any]:
        """Get application uptime."""
        try:
            # Get process uptime
            import time
            import os
            if hasattr(os, 'times'):
                times = os.times()
                uptime_seconds = times[4] if len(times) > 4 else time.time()
            else:
                import psutil as ps
                uptime_seconds = time.time() - ps.Process(os.getpid()).create_time()
            
            hours, remainder = divmod(uptime_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return {
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            }
        except Exception as e:
            logger.warning(f"Uptime check failed: {str(e)[:50]}")
            return {"uptime_seconds": 0}


class MetricsCollector:
    """Collect and track performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.lock = threading.RLock()
        self.max_history = 100  # Keep last N samples
    
    def record_metric(self, metric_name: str, value: float):
        """Record a metric value."""
        with self.lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = []
            
            self.metrics[metric_name].append(value)
            
            # Keep only recent history
            if len(self.metrics[metric_name]) > self.max_history:
                self.metrics[metric_name] = self.metrics[metric_name][-self.max_history:]
    
    def get_metric_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        with self.lock:
            if metric_name not in self.metrics or not self.metrics[metric_name]:
                return {}
            
            values = self.metrics[metric_name]
            
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1]
            }
    
    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics."""
        with self.lock:
            return {
                name: self.get_metric_stats(name)
                for name in self.metrics.keys()
            }


class LoadMetrics:
    """Track application load metrics."""
    
    def __init__(self):
        self.request_times: List[float] = []
        self.active_requests = 0
        self.lock = threading.RLock()
        self.max_history = 1000
    
    def record_request_time(self, duration_ms: float):
        """Record request duration."""
        with self.lock:
            self.request_times.append(duration_ms)
            if len(self.request_times) > self.max_history:
                self.request_times = self.request_times[-self.max_history:]
    
    def get_load_average(self) -> Dict[str, float]:
        """Get load averages."""
        with self.lock:
            if not self.request_times:
                return {}
            
            sorted_times = sorted(self.request_times)
            n = len(sorted_times)
            
            return {
                "p50": sorted_times[n // 2],
                "p95": sorted_times[int(n * 0.95)],
                "p99": sorted_times[int(n * 0.99)],
                "avg": sum(self.request_times) / n,
                "min": min(self.request_times),
                "max": max(self.request_times)
            }


# Global instances for use throughout the application
health_checker = HealthChecker()
metrics_collector = MetricsCollector()
load_metrics = LoadMetrics()


__all__ = [
    'HealthStatus',
    'HealthChecker',
    'MetricsCollector',
    'LoadMetrics',
    'health_checker',
    'metrics_collector',
    'load_metrics'
]
