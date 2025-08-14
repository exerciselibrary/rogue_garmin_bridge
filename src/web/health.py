"""Health check endpoints for monitoring and Docker health checks."""

import os
import psutil
import sqlite3
from datetime import datetime
from flask import Blueprint, jsonify, current_app
from pathlib import Path

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health_check():
    """Basic health check endpoint for Docker and load balancers."""
    try:
        # Basic application health
        status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': current_app.config.get('APP_VERSION', '1.0.0')
        }
        
        return jsonify(status), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@health_bp.route('/health/detailed')
def detailed_health_check():
    """Detailed health check with component status."""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': current_app.config.get('APP_VERSION', '1.0.0'),
        'components': {}
    }
    
    overall_healthy = True
    
    # Check database health
    if current_app.config.get('HEALTH_CHECK_DATABASE', True):
        db_status = _check_database_health()
        health_status['components']['database'] = db_status
        if db_status['status'] != 'healthy':
            overall_healthy = False
    
    # Check Bluetooth health
    if current_app.config.get('HEALTH_CHECK_BLUETOOTH', True):
        bt_status = _check_bluetooth_health()
        health_status['components']['bluetooth'] = bt_status
        if bt_status['status'] != 'healthy':
            overall_healthy = False
    
    # Check disk space
    if current_app.config.get('HEALTH_CHECK_DISK_SPACE', True):
        disk_status = _check_disk_space()
        health_status['components']['disk_space'] = disk_status
        if disk_status['status'] != 'healthy':
            overall_healthy = False
    
    # Check memory usage
    if current_app.config.get('HEALTH_CHECK_MEMORY', True):
        memory_status = _check_memory_usage()
        health_status['components']['memory'] = memory_status
        if memory_status['status'] != 'healthy':
            overall_healthy = False
    
    # Set overall status
    health_status['status'] = 'healthy' if overall_healthy else 'unhealthy'
    
    return jsonify(health_status), 200 if overall_healthy else 503


@health_bp.route('/health/ready')
def readiness_check():
    """Readiness check for Kubernetes deployments."""
    try:
        # Check if application is ready to serve requests
        ready_status = {
            'ready': True,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        # Check database connectivity
        db_ready = _check_database_connectivity()
        ready_status['checks']['database'] = db_ready
        
        # Check required directories exist
        dirs_ready = _check_required_directories()
        ready_status['checks']['directories'] = dirs_ready
        
        # Overall readiness
        overall_ready = db_ready and dirs_ready
        ready_status['ready'] = overall_ready
        
        return jsonify(ready_status), 200 if overall_ready else 503
        
    except Exception as e:
        return jsonify({
            'ready': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@health_bp.route('/health/live')
def liveness_check():
    """Liveness check for Kubernetes deployments."""
    try:
        # Simple liveness check - application is running
        return jsonify({
            'alive': True,
            'timestamp': datetime.utcnow().isoformat(),
            'pid': os.getpid()
        }), 200
    except Exception as e:
        return jsonify({
            'alive': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


def _check_database_health():
    """Check database health and connectivity."""
    try:
        database_url = current_app.config.get('DATABASE_URL', '')
        
        if database_url.startswith('sqlite:///'):
            # SQLite database check
            db_path = database_url.replace('sqlite:///', '')
            
            if not os.path.exists(db_path):
                return {
                    'status': 'unhealthy',
                    'error': 'Database file does not exist',
                    'path': db_path
                }
            
            # Test connection
            conn = sqlite3.connect(db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            conn.close()
            
            # Check database size
            db_size = os.path.getsize(db_path)
            
            return {
                'status': 'healthy',
                'type': 'sqlite',
                'path': db_path,
                'size_bytes': db_size,
                'size_mb': round(db_size / (1024 * 1024), 2)
            }
        else:
            return {
                'status': 'unknown',
                'error': 'Unsupported database type',
                'database_url': database_url
            }
            
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def _check_bluetooth_health():
    """Check Bluetooth adapter health."""
    try:
        # This is a basic check - in production, you might want to
        # check if the Bluetooth adapter is present and functional
        
        # Check if running in simulator mode
        if current_app.config.get('USE_SIMULATOR', False):
            return {
                'status': 'healthy',
                'mode': 'simulator',
                'note': 'Running in simulator mode'
            }
        
        # Check for Bluetooth adapter (Linux)
        if os.path.exists('/sys/class/bluetooth'):
            adapters = os.listdir('/sys/class/bluetooth')
            if adapters:
                return {
                    'status': 'healthy',
                    'adapters': adapters,
                    'adapter_count': len(adapters)
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'No Bluetooth adapters found'
                }
        
        # For other platforms or if we can't detect
        return {
            'status': 'unknown',
            'note': 'Bluetooth status cannot be determined on this platform'
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def _check_disk_space():
    """Check available disk space."""
    try:
        # Check disk space for data directory
        data_path = current_app.config.get('DATA_PATH', 'data')
        
        if isinstance(data_path, str):
            data_path = Path(data_path)
        
        # Get disk usage
        disk_usage = psutil.disk_usage(str(data_path.parent))
        
        # Calculate percentages
        used_percent = (disk_usage.used / disk_usage.total) * 100
        free_percent = (disk_usage.free / disk_usage.total) * 100
        
        # Determine status based on free space
        if free_percent < 5:  # Less than 5% free
            status = 'unhealthy'
        elif free_percent < 10:  # Less than 10% free
            status = 'warning'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'total_bytes': disk_usage.total,
            'used_bytes': disk_usage.used,
            'free_bytes': disk_usage.free,
            'used_percent': round(used_percent, 2),
            'free_percent': round(free_percent, 2),
            'total_gb': round(disk_usage.total / (1024**3), 2),
            'free_gb': round(disk_usage.free / (1024**3), 2)
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def _check_memory_usage():
    """Check memory usage."""
    try:
        # Get memory information
        memory = psutil.virtual_memory()
        
        # Get current process memory usage
        process = psutil.Process()
        process_memory = process.memory_info()
        
        # Determine status based on system memory usage
        if memory.percent > 90:
            status = 'unhealthy'
        elif memory.percent > 80:
            status = 'warning'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'system': {
                'total_bytes': memory.total,
                'available_bytes': memory.available,
                'used_bytes': memory.used,
                'used_percent': memory.percent,
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2)
            },
            'process': {
                'rss_bytes': process_memory.rss,
                'vms_bytes': process_memory.vms,
                'rss_mb': round(process_memory.rss / (1024**2), 2),
                'vms_mb': round(process_memory.vms / (1024**2), 2)
            }
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def _check_database_connectivity():
    """Check if database is accessible."""
    try:
        database_url = current_app.config.get('DATABASE_URL', '')
        
        if database_url.startswith('sqlite:///'):
            db_path = database_url.replace('sqlite:///', '')
            conn = sqlite3.connect(db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            conn.close()
            return True
        
        return False
        
    except Exception:
        return False


def _check_required_directories():
    """Check if required directories exist."""
    try:
        required_dirs = [
            current_app.config.get('DATA_PATH', 'data'),
            current_app.config.get('LOGS_PATH', 'logs'),
            current_app.config.get('FIT_FILES_PATH', 'fit_files')
        ]
        
        for dir_path in required_dirs:
            if isinstance(dir_path, str):
                dir_path = Path(dir_path)
            
            if not dir_path.exists():
                return False
        
        return True
        
    except Exception:
        return False