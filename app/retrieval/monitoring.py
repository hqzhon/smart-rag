"""Monitoring and Exception Handling for Multi-Path RAG Retrieval

This module provides comprehensive monitoring, exception handling, and performance
tracking capabilities for the multi-path RAG retrieval system.
"""

from typing import Dict, Any, List, Optional, Callable, Union
import time
import asyncio
import traceback
import functools
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import json
import threading
from datetime import datetime, timedelta

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComponentStatus(Enum):
    """Component health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class PerformanceMetric:
    """Performance metric data"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = "ms"


@dataclass
class ErrorEvent:
    """Error event data"""
    component: str
    error_type: str
    message: str
    timestamp: float
    traceback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    severity: AlertLevel = AlertLevel.ERROR


@dataclass
class HealthCheck:
    """Health check result"""
    component: str
    status: ComponentStatus
    message: str
    timestamp: float
    metrics: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for fault tolerance"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: type = Exception):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying to recover
            expected_exception: Exception type to handle
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self._lock = threading.Lock()
    
    def __call__(self, func):
        """Decorator to wrap function with circuit breaker"""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    async def call(self, func, *args, **kwargs):
        """Call function with circuit breaker protection"""
        with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                else:
                    raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        return (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.recovery_timeout)
    
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            self.failure_count = 0
            self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time
        }


class PerformanceTracker:
    """Performance metrics tracker"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics = defaultdict(lambda: deque(maxlen=max_history))
        self._lock = threading.Lock()
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {}
        )
        
        with self._lock:
            self.metrics[name].append(metric)
    
    def get_metrics(self, name: str, 
                   time_window: Optional[float] = None) -> List[PerformanceMetric]:
        """Get metrics for a given name"""
        with self._lock:
            metrics = list(self.metrics[name])
        
        if time_window:
            cutoff_time = time.time() - time_window
            metrics = [m for m in metrics if m.timestamp >= cutoff_time]
        
        return metrics
    
    def get_statistics(self, name: str, 
                      time_window: Optional[float] = None) -> Dict[str, float]:
        """Get statistical summary of metrics"""
        metrics = self.get_metrics(name, time_window)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'p50': self._percentile(values, 0.5),
            'p95': self._percentile(values, 0.95),
            'p99': self._percentile(values, 0.99)
        }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile"""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def clear_metrics(self, name: Optional[str] = None):
        """Clear metrics"""
        with self._lock:
            if name:
                self.metrics[name].clear()
            else:
                self.metrics.clear()


class ErrorTracker:
    """Error tracking and alerting"""
    
    def __init__(self, max_errors: int = 1000):
        self.max_errors = max_errors
        self.errors = deque(maxlen=max_errors)
        self.error_counts = defaultdict(int)
        self._lock = threading.Lock()
        self.alert_handlers = []
    
    def record_error(self, component: str, error: Exception, 
                    context: Optional[Dict[str, Any]] = None,
                    severity: AlertLevel = AlertLevel.ERROR):
        """Record an error event"""
        error_event = ErrorEvent(
            component=component,
            error_type=type(error).__name__,
            message=str(error),
            timestamp=time.time(),
            traceback=traceback.format_exc(),
            context=context or {},
            severity=severity
        )
        
        with self._lock:
            self.errors.append(error_event)
            self.error_counts[f"{component}:{error_event.error_type}"] += 1
        
        # Trigger alerts
        self._trigger_alerts(error_event)
        
        logger.error(
            f"Error in {component}: {error_event.message}",
            extra={'error_event': error_event.__dict__}
        )
    
    def get_errors(self, component: Optional[str] = None, 
                  time_window: Optional[float] = None) -> List[ErrorEvent]:
        """Get error events"""
        with self._lock:
            errors = list(self.errors)
        
        if component:
            errors = [e for e in errors if e.component == component]
        
        if time_window:
            cutoff_time = time.time() - time_window
            errors = [e for e in errors if e.timestamp >= cutoff_time]
        
        return errors
    
    def get_error_summary(self, time_window: Optional[float] = None) -> Dict[str, Any]:
        """Get error summary statistics"""
        errors = self.get_errors(time_window=time_window)
        
        component_counts = defaultdict(int)
        error_type_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for error in errors:
            component_counts[error.component] += 1
            error_type_counts[error.error_type] += 1
            severity_counts[error.severity.value] += 1
        
        return {
            'total_errors': len(errors),
            'by_component': dict(component_counts),
            'by_error_type': dict(error_type_counts),
            'by_severity': dict(severity_counts),
            'time_window': time_window
        }
    
    def add_alert_handler(self, handler: Callable[[ErrorEvent], None]):
        """Add error alert handler"""
        self.alert_handlers.append(handler)
    
    def _trigger_alerts(self, error_event: ErrorEvent):
        """Trigger alert handlers"""
        for handler in self.alert_handlers:
            try:
                handler(error_event)
            except Exception as e:
                logger.error(f"Alert handler failed: {str(e)}")


class HealthMonitor:
    """System health monitoring"""
    
    def __init__(self):
        self.health_checks = {}
        self.component_status = {}
        self._lock = threading.Lock()
    
    def register_health_check(self, component: str, 
                             check_func: Callable[[], Dict[str, Any]]):
        """Register a health check function"""
        self.health_checks[component] = check_func
    
    async def check_health(self, component: Optional[str] = None) -> Dict[str, HealthCheck]:
        """Perform health checks"""
        results = {}
        
        components = [component] if component else self.health_checks.keys()
        
        for comp in components:
            if comp not in self.health_checks:
                continue
            
            try:
                check_result = await self._run_health_check(comp)
                results[comp] = check_result
                
                with self._lock:
                    self.component_status[comp] = check_result.status
                    
            except Exception as e:
                error_check = HealthCheck(
                    component=comp,
                    status=ComponentStatus.UNHEALTHY,
                    message=f"Health check failed: {str(e)}",
                    timestamp=time.time()
                )
                results[comp] = error_check
                
                with self._lock:
                    self.component_status[comp] = ComponentStatus.UNHEALTHY
        
        return results
    
    async def _run_health_check(self, component: str) -> HealthCheck:
        """Run individual health check"""
        check_func = self.health_checks[component]
        
        start_time = time.time()
        
        if asyncio.iscoroutinefunction(check_func):
            result = await check_func()
        else:
            result = check_func()
        
        check_time = (time.time() - start_time) * 1000  # ms
        
        # Determine status based on result
        if isinstance(result, dict):
            status = ComponentStatus(result.get('status', 'unknown'))
            message = result.get('message', 'OK')
            metrics = result.get('metrics', {})
            details = result.get('details', {})
        else:
            status = ComponentStatus.HEALTHY if result else ComponentStatus.UNHEALTHY
            message = 'OK' if result else 'Check failed'
            metrics = {}
            details = {}
        
        metrics['check_time_ms'] = check_time
        
        return HealthCheck(
            component=component,
            status=status,
            message=message,
            timestamp=time.time(),
            metrics=metrics,
            details=details
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        with self._lock:
            status_counts = defaultdict(int)
            for status in self.component_status.values():
                status_counts[status.value] += 1
        
        # Determine overall status
        if status_counts.get('unhealthy', 0) > 0:
            overall_status = ComponentStatus.UNHEALTHY
        elif status_counts.get('degraded', 0) > 0:
            overall_status = ComponentStatus.DEGRADED
        elif status_counts.get('healthy', 0) > 0:
            overall_status = ComponentStatus.HEALTHY
        else:
            overall_status = ComponentStatus.UNKNOWN
        
        return {
            'overall_status': overall_status.value,
            'component_status': dict(self.component_status),
            'status_summary': dict(status_counts),
            'timestamp': time.time()
        }


class RetrievalMonitor:
    """Comprehensive monitoring for retrieval system"""
    
    def __init__(self):
        self.performance_tracker = PerformanceTracker()
        self.error_tracker = ErrorTracker()
        self.health_monitor = HealthMonitor()
        self.circuit_breakers = {}
        
        # Setup default alert handlers
        self.error_tracker.add_alert_handler(self._log_alert)
    
    def create_circuit_breaker(self, name: str, **kwargs) -> CircuitBreaker:
        """Create and register a circuit breaker"""
        circuit_breaker = CircuitBreaker(**kwargs)
        self.circuit_breakers[name] = circuit_breaker
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self.circuit_breakers.get(name)
    
    @asynccontextmanager
    async def track_operation(self, operation_name: str, component: str = "unknown"):
        """Context manager to track operation performance and errors"""
        start_time = time.time()
        
        try:
            yield
            
            # Record success metrics
            duration = (time.time() - start_time) * 1000  # ms
            self.performance_tracker.record_metric(
                f"{operation_name}_duration",
                duration,
                tags={'component': component, 'status': 'success'}
            )
            
        except Exception as e:
            # Record error
            self.error_tracker.record_error(
                component=component,
                error=e,
                context={'operation': operation_name}
            )
            
            # Record failure metrics
            duration = (time.time() - start_time) * 1000  # ms
            self.performance_tracker.record_metric(
                f"{operation_name}_duration",
                duration,
                tags={'component': component, 'status': 'error'}
            )
            
            raise
    
    def _log_alert(self, error_event: ErrorEvent):
        """Default alert handler that logs alerts"""
        if error_event.severity in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
            logger.error(
                f"ALERT [{error_event.severity.value.upper()}] "
                f"{error_event.component}: {error_event.message}"
            )
    
    def get_dashboard_data(self, time_window: float = 3600) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data"""
        return {
            'system_health': self.health_monitor.get_system_status(),
            'error_summary': self.error_tracker.get_error_summary(time_window),
            'performance_metrics': self._get_performance_summary(time_window),
            'circuit_breakers': {
                name: cb.get_state() 
                for name, cb in self.circuit_breakers.items()
            },
            'timestamp': time.time(),
            'time_window': time_window
        }
    
    def _get_performance_summary(self, time_window: float) -> Dict[str, Any]:
        """Get performance metrics summary"""
        summary = {}
        
        # Get all metric names
        metric_names = list(self.performance_tracker.metrics.keys())
        
        for name in metric_names:
            stats = self.performance_tracker.get_statistics(name, time_window)
            if stats:
                summary[name] = stats
        
        return summary
    
    async def run_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks"""
        return await self.health_monitor.check_health()


# Global monitor instance
_monitor = None


def get_monitor() -> RetrievalMonitor:
    """Get global monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = RetrievalMonitor()
    return _monitor


# Decorator for automatic monitoring
def monitor_operation(operation_name: str, component: str = "unknown"):
    """Decorator to automatically monitor function performance and errors"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            monitor = get_monitor()
            async with monitor.track_operation(operation_name, component):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


# Exception classes for retrieval system
class RetrievalError(Exception):
    """Base exception for retrieval errors"""
    pass


class VectorRetrievalError(RetrievalError):
    """Vector retrieval specific error"""
    pass


class BM25RetrievalError(RetrievalError):
    """BM25 retrieval specific error"""
    pass


class FusionError(RetrievalError):
    """Fusion algorithm error"""
    pass


class RerankError(RetrievalError):
    """Reranking error"""
    pass


class ConfigurationError(RetrievalError):
    """Configuration error"""
    pass