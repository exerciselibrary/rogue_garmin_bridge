#!/usr/bin/env python3
"""
Enhanced Centralized logging configuration for the Rogue Garmin Bridge application.

This module provides a comprehensive logging configuration across all components
of the application, including:
- Console logging for development
- File-based logging with rotation for production use
- Structured logging format for easier analysis
- Component-specific loggers for better categorization
- Performance metrics collection and reporting
- Alerting mechanisms for critical issues
- Log rotation and size management
"""

import os
import sys
import logging
import json
import threading
import time
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    component: str
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class LogAlert:
    """Log alert data structure"""
    timestamp: datetime
    severity: AlertSeverity
    component: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False

# Base directory for logs
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs'))

# Ensure log directory exists
Path(LOG_DIR).mkdir(exist_ok=True, parents=True)

# Log file paths
MAIN_LOG_FILE = os.path.join(LOG_DIR, 'rogue_garmin_bridge.log')
ERROR_LOG_FILE = os.path.join(LOG_DIR, 'error.log')
DATA_FLOW_LOG_FILE = os.path.join(LOG_DIR, 'data_flow.log')
WEB_LOG_FILE = os.path.join(LOG_DIR, 'web.log')
BLE_LOG_FILE = os.path.join(LOG_DIR, 'bluetooth.log')
WORKOUT_LOG_FILE = os.path.join(LOG_DIR, 'workout.log')
PERFORMANCE_LOG_FILE = os.path.join(LOG_DIR, 'performance.log')
ALERTS_LOG_FILE = os.path.join(LOG_DIR, 'alerts.log')

# Max log file size (10 MB)
MAX_LOG_SIZE = 10 * 1024 * 1024
# Number of backup logs to keep
BACKUP_COUNT = 5

# Flag to indicate if logging has been configured
_logging_configured = False

# Format string for logs
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# More detailed format for debugging
DEBUG_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(funcName)s - %(message)s'
# Structured JSON format for performance logs
JSON_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Global instances
_performance_monitor: Optional['PerformanceMonitor'] = None
_alert_manager: Optional['AlertManager'] = None

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record):
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'component': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)

class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.metric_callbacks: List[Callable[[PerformanceMetric], None]] = []
        self._lock = threading.RLock()
        
        # Set up performance logger
        self.logger = logging.getLogger('performance')
        
        # Start metrics collection thread
        self._start_metrics_thread()
    
    def record_metric(self, component: str, metric_name: str, value: float, 
                     unit: str, tags: Dict[str, str] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            component=component,
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        
        with self._lock:
            self.metrics.append(metric)
            
            # Keep only recent metrics to prevent memory issues
            if len(self.metrics) > 10000:
                self.metrics = self.metrics[-5000:]
        
        # Log the metric
        self.logger.info(f"METRIC: {component}.{metric_name} = {value} {unit}", 
                        extra={
                            'metric_component': component,
                            'metric_name': metric_name,
                            'metric_value': value,
                            'metric_unit': unit,
                            'metric_tags': tags or {}
                        })
        
        # Notify callbacks
        for callback in self.metric_callbacks:
            try:
                callback(metric)
            except Exception as e:
                logging.error(f"Error in metric callback: {e}")
    
    def register_callback(self, callback: Callable[[PerformanceMetric], None]):
        """Register a callback for metric events"""
        if callback not in self.metric_callbacks:
            self.metric_callbacks.append(callback)
    
    def get_metrics(self, component: str = None, metric_name: str = None, 
                   since: datetime = None) -> List[PerformanceMetric]:
        """Get metrics with optional filtering"""
        with self._lock:
            filtered_metrics = self.metrics.copy()
        
        if component:
            filtered_metrics = [m for m in filtered_metrics if m.component == component]
        
        if metric_name:
            filtered_metrics = [m for m in filtered_metrics if m.metric_name == metric_name]
        
        if since:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= since]
        
        return filtered_metrics
    
    def get_metric_summary(self, component: str = None, 
                          time_window: timedelta = None) -> Dict[str, Any]:
        """Get summary statistics for metrics"""
        if time_window:
            since = datetime.now() - time_window
            metrics = self.get_metrics(component=component, since=since)
        else:
            metrics = self.get_metrics(component=component)
        
        if not metrics:
            return {}
        
        # Group by metric name
        metric_groups = {}
        for metric in metrics:
            key = f"{metric.component}.{metric.metric_name}"
            if key not in metric_groups:
                metric_groups[key] = []
            metric_groups[key].append(metric.value)
        
        # Calculate statistics
        summary = {}
        for key, values in metric_groups.items():
            summary[key] = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': values[-1] if values else None
            }
        
        return summary
    
    def _start_metrics_thread(self):
        """Start background thread for metrics collection"""
        def metrics_worker():
            while True:
                try:
                    time.sleep(60)  # Collect system metrics every minute
                    self._collect_system_metrics()
                except Exception as e:
                    logging.error(f"Error in metrics collection: {e}")
        
        metrics_thread = threading.Thread(target=metrics_worker, daemon=True)
        metrics_thread.start()
    
    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric('system', 'cpu_usage', cpu_percent, 'percent')
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.record_metric('system', 'memory_usage', memory.percent, 'percent')
            self.record_metric('system', 'memory_available', memory.available / (1024**3), 'GB')
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.record_metric('system', 'disk_usage', (disk.used / disk.total) * 100, 'percent')
            
        except ImportError:
            # psutil not available, skip system metrics
            pass
        except Exception as e:
            logging.error(f"Error collecting system metrics: {e}")

class AlertManager:
    """Manage logging alerts and notifications"""
    
    def __init__(self):
        self.alerts: List[LogAlert] = []
        self.alert_callbacks: List[Callable[[LogAlert], None]] = []
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        
        # Set up alerts logger
        self.logger = logging.getLogger('alerts')
        
        # Default alert rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Set up default alerting rules"""
        self.alert_rules = {
            'high_error_rate': {
                'condition': lambda metrics: self._check_error_rate(metrics),
                'severity': AlertSeverity.HIGH,
                'message': 'High error rate detected'
            },
            'database_corruption': {
                'condition': lambda log_record: 'corruption' in log_record.getMessage().lower(),
                'severity': AlertSeverity.CRITICAL,
                'message': 'Database corruption detected'
            },
            'connection_failures': {
                'condition': lambda log_record: ('connection' in log_record.getMessage().lower() and 
                                               log_record.levelno >= logging.ERROR),
                'severity': AlertSeverity.MEDIUM,
                'message': 'Connection failure detected'
            },
            'memory_usage_high': {
                'condition': lambda metrics: self._check_memory_usage(metrics),
                'severity': AlertSeverity.MEDIUM,
                'message': 'High memory usage detected'
            }
        }
    
    def create_alert(self, severity: AlertSeverity, component: str, message: str, 
                    details: Dict[str, Any] = None):
        """Create a new alert"""
        alert = LogAlert(
            timestamp=datetime.now(),
            severity=severity,
            component=component,
            message=message,
            details=details or {}
        )
        
        with self._lock:
            self.alerts.append(alert)
            
            # Keep only recent alerts
            if len(self.alerts) > 1000:
                self.alerts = self.alerts[-500:]
        
        # Log the alert
        self.logger.warning(f"ALERT [{severity.value.upper()}] {component}: {message}",
                           extra={
                               'alert_severity': severity.value,
                               'alert_component': component,
                               'alert_details': details or {}
                           })
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logging.error(f"Error in alert callback: {e}")
    
    def register_callback(self, callback: Callable[[LogAlert], None]):
        """Register a callback for alert events"""
        if callback not in self.alert_callbacks:
            self.alert_callbacks.append(callback)
    
    def check_log_record(self, record: logging.LogRecord):
        """Check a log record against alert rules that expect LogRecord."""
        # Only check rules that expect a LogRecord, not metrics
        log_record_rules = ['database_corruption', 'connection_failures']
        for rule_name in log_record_rules:
            rule = self.alert_rules.get(rule_name)
            if rule and 'condition' in rule and callable(rule['condition']):
                try:
                    if rule['condition'](record):
                        self.create_alert(
                            severity=rule['severity'],
                            component=record.name,
                            message=rule['message'],
                            details={
                                'rule': rule_name,
                                'log_message': record.getMessage(),
                                'log_level': record.levelname
                            }
                        )
                except Exception as e:
                    logging.error(f"Error checking alert rule {rule_name}: {e}")
    
    def _check_error_rate(self, metrics: List[PerformanceMetric]) -> bool:
        """Check if error rate is too high"""
        # This would be implemented based on actual error rate metrics
        return False
    
    def _check_memory_usage(self, metrics: List[PerformanceMetric]) -> bool:
        """Check if memory usage is too high"""
        memory_metrics = [m for m in metrics if m.metric_name == 'memory_usage']
        if memory_metrics:
            latest_memory = memory_metrics[-1].value
            return latest_memory > 90.0  # Alert if memory usage > 90%
        return False
    
    def get_alerts(self, severity: AlertSeverity = None, component: str = None, 
                  since: datetime = None, acknowledged: bool = None) -> List[LogAlert]:
        """Get alerts with optional filtering"""
        with self._lock:
            filtered_alerts = self.alerts.copy()
        
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
        
        if component:
            filtered_alerts = [a for a in filtered_alerts if a.component == component]
        
        if since:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp >= since]
        
        if acknowledged is not None:
            filtered_alerts = [a for a in filtered_alerts if a.acknowledged == acknowledged]
        
        return filtered_alerts
    
    def acknowledge_alert(self, alert: LogAlert):
        """Acknowledge an alert"""
        alert.acknowledged = True
        self.logger.info(f"Alert acknowledged: {alert.message}")

class AlertingHandler(logging.Handler):
    """Custom logging handler that triggers alerts"""
    
    def __init__(self, alert_manager: AlertManager):
        super().__init__()
        self.alert_manager = alert_manager
    
    def emit(self, record):
        """Check record against alert rules"""
        try:
            self.alert_manager.check_log_record(record)
        except Exception:
            # Don't let alert checking break logging
            pass

def configure_logging(debug=False, enable_structured_logging=False, 
                     enable_performance_monitoring=True, enable_alerting=True):
    """
    Configure the global logging settings for the application.
    
    Args:
        debug: Whether to enable debug logging
        enable_structured_logging: Whether to use structured JSON logging
        enable_performance_monitoring: Whether to enable performance monitoring
        enable_alerting: Whether to enable alerting
    """
    global _logging_configured, _performance_monitor, _alert_manager
    
    if _logging_configured:
        return
    
    # Initialize performance monitor and alert manager
    if enable_performance_monitoring:
        _performance_monitor = PerformanceMonitor()
    
    if enable_alerting:
        _alert_manager = AlertManager()
    
    # Set the format based on debug mode and structured logging
    if enable_structured_logging:
        formatter = StructuredFormatter()
    else:
        log_format = DEBUG_LOG_FORMAT if debug else LOG_FORMAT
        formatter = logging.Formatter(log_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Clear any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Main log file handler with rotation
    file_handler = RotatingFileHandler(
        MAIN_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(file_handler)
    
    # Error log file handler
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    # Performance log handler
    if enable_performance_monitoring:
        perf_handler = RotatingFileHandler(
            PERFORMANCE_LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT
        )
        perf_handler.setFormatter(StructuredFormatter() if enable_structured_logging else formatter)
        perf_logger = logging.getLogger('performance')
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)
    
    # Alerts log handler
    if enable_alerting:
        alerts_handler = RotatingFileHandler(
            ALERTS_LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT
        )
        alerts_handler.setFormatter(formatter)
        alerts_logger = logging.getLogger('alerts')
        alerts_logger.addHandler(alerts_handler)
        alerts_logger.setLevel(logging.WARNING)
        
        # Add alerting handler to root logger
        alerting_handler = AlertingHandler(_alert_manager)
        alerting_handler.setLevel(logging.WARNING)
        root_logger.addHandler(alerting_handler)
    
    # Create component-specific log handlers
    _configure_component_handlers(formatter, debug, enable_structured_logging)
    
    # Mark logging as configured
    _logging_configured = True
    
    # Log startup message
    logging.info(f"Enhanced logging initialized at {datetime.now().isoformat()}")
    if debug:
        logging.info("Debug logging enabled")
    if enable_structured_logging:
        logging.info("Structured JSON logging enabled")
    if enable_performance_monitoring:
        logging.info("Performance monitoring enabled")
    if enable_alerting:
        logging.info("Alerting enabled")
    
    logging.info(f"Log files located at: {LOG_DIR}")

def _configure_component_handlers(formatter, debug, structured_logging=False):
    """
    Configure handlers for specific components.
    
    Args:
        formatter: Log formatter to use
        debug: Whether debug mode is enabled
        structured_logging: Whether to use structured logging
    """
    # Use structured formatter for specific components if enabled
    struct_formatter = StructuredFormatter() if structured_logging else formatter
    
    # Data flow logging
    data_flow_handler = RotatingFileHandler(
        DATA_FLOW_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    data_flow_handler.setFormatter(struct_formatter)
    data_flow_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Web logging
    web_handler = RotatingFileHandler(
        WEB_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    web_handler.setFormatter(formatter)
    web_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # BLE logging with time-based rotation (daily)
    ble_handler = TimedRotatingFileHandler(
        BLE_LOG_FILE,
        when='midnight',
        interval=1,
        backupCount=7  # Keep 7 days
    )
    ble_handler.setFormatter(struct_formatter)
    ble_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Workout logging
    workout_handler = RotatingFileHandler(
        WORKOUT_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    workout_handler.setFormatter(struct_formatter)
    workout_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Add handlers to component loggers
    component_handlers = {
        'data_flow': data_flow_handler,
        'web': web_handler,
        'ftms': ble_handler,
        'bluetooth': ble_handler,
        'bluetooth_connection': ble_handler,
        'ftms_connector': ble_handler,
        'workout_manager': workout_handler,
        'database': data_flow_handler,
        'data_validator': data_flow_handler,
        'fit_converter': data_flow_handler,
        'garmin_uploader': data_flow_handler,
    }
    
    for component, handler in component_handlers.items():
        logger = logging.getLogger(component)
        logger.addHandler(handler)
        # Make sure component loggers propagate to root logger as well
        logger.propagate = True

def get_component_logger(component_name):
    """
    Get a logger for a specific component.
    
    Args:
        component_name: Name of the component
        
    Returns:
        Logger instance for the component
    """
    # Make sure logging is configured
    if not _logging_configured:
        configure_logging()
    
    return logging.getLogger(component_name)

def get_performance_monitor() -> Optional[PerformanceMonitor]:
    """Get the global performance monitor instance"""
    return _performance_monitor

def get_alert_manager() -> Optional[AlertManager]:
    """Get the global alert manager instance"""
    return _alert_manager

def log_performance_metric(component: str, metric_name: str, value: float, 
                          unit: str, tags: Dict[str, str] = None):
    """
    Convenience function to log a performance metric.
    
    Args:
        component: Component name
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        tags: Optional tags for the metric
    """
    if _performance_monitor:
        _performance_monitor.record_metric(component, metric_name, value, unit, tags)

def create_alert(severity: AlertSeverity, component: str, message: str, 
                details: Dict[str, Any] = None):
    """
    Convenience function to create an alert.
    
    Args:
        severity: Alert severity
        component: Component name
        message: Alert message
        details: Optional additional details
    """
    if _alert_manager:
        _alert_manager.create_alert(severity, component, message, details)

def get_logging_status() -> Dict[str, Any]:
    """
    Get current logging system status.
    
    Returns:
        Dictionary with logging system information
    """
    status = {
        'configured': _logging_configured,
        'log_directory': LOG_DIR,
        'performance_monitoring': _performance_monitor is not None,
        'alerting': _alert_manager is not None,
        'log_files': {
            'main': MAIN_LOG_FILE,
            'error': ERROR_LOG_FILE,
            'data_flow': DATA_FLOW_LOG_FILE,
            'web': WEB_LOG_FILE,
            'bluetooth': BLE_LOG_FILE,
            'workout': WORKOUT_LOG_FILE,
            'performance': PERFORMANCE_LOG_FILE,
            'alerts': ALERTS_LOG_FILE
        }
    }
    
    # Add file sizes if files exist
    for log_type, log_file in status['log_files'].items():
        if os.path.exists(log_file):
            status['log_files'][log_type + '_size'] = os.path.getsize(log_file)
    
    # Add performance metrics summary if available
    if _performance_monitor:
        status['performance_summary'] = _performance_monitor.get_metric_summary(
            time_window=timedelta(hours=1)
        )
    
    # Add recent alerts if available
    if _alert_manager:
        recent_alerts = _alert_manager.get_alerts(
            since=datetime.now() - timedelta(hours=24),
            acknowledged=False
        )
        status['unacknowledged_alerts'] = len(recent_alerts)
        status['recent_alerts'] = [
            {
                'timestamp': alert.timestamp.isoformat(),
                'severity': alert.severity.value,
                'component': alert.component,
                'message': alert.message
            }
            for alert in recent_alerts[-5:]  # Last 5 alerts
        ]
    
    return status

# Configure logging when the module is imported
configure_logging()