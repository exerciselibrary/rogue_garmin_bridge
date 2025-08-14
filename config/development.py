"""Development configuration for Rogue Garmin Bridge."""

import os
from config.base import Config


class DevelopmentConfig(Config):
    """Development configuration class."""
    
    # Flask settings
    DEBUG = True
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data/workouts_dev.db')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    LOG_TO_FILE = True
    LOG_FILE_PATH = 'logs/development.log'
    
    # FTMS Settings - Use simulator by default in development
    USE_SIMULATOR = os.environ.get('USE_SIMULATOR', 'True').lower() == 'true'
    SIMULATOR_DEVICE_TYPE = os.environ.get('SIMULATOR_DEVICE_TYPE', 'bike')
    CONNECTION_TIMEOUT = int(os.environ.get('CONNECTION_TIMEOUT', '10'))  # Shorter for dev
    RECONNECTION_ATTEMPTS = int(os.environ.get('RECONNECTION_ATTEMPTS', '2'))
    
    # Performance settings - More responsive for development
    CHART_UPDATE_INTERVAL = int(os.environ.get('CHART_UPDATE_INTERVAL', '500'))  # Faster updates
    DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS', '30'))  # Less retention
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', '60'))  # Shorter cache
    
    # Development-specific settings
    FLASK_ENV = 'development'
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Disable caching for development
    
    # Security settings (relaxed for development)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    
    # File storage
    FIT_FILES_PATH = os.environ.get('FIT_FILES_PATH', 'fit_files_dev')
    MAX_FIT_FILE_AGE_DAYS = int(os.environ.get('MAX_FIT_FILE_AGE_DAYS', '7'))  # Shorter retention
    
    # Development tools
    PROFILING = os.environ.get('PROFILING', 'False').lower() == 'true'
    SQL_ECHO = os.environ.get('SQL_ECHO', 'False').lower() == 'true'
    
    # Health check settings (less strict for development)
    HEALTH_CHECK_ENABLED = True
    HEALTH_CHECK_DATABASE = True
    HEALTH_CHECK_BLUETOOTH = False  # May not have real Bluetooth in dev
    
    @staticmethod
    def validate_config():
        """Validate development configuration."""
        # Less strict validation for development
        return True