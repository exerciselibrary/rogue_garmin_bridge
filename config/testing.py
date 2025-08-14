"""Testing configuration for Rogue Garmin Bridge."""

import os
from config.base import Config


class TestingConfig(Config):
    """Testing configuration class."""
    
    # Flask settings
    DEBUG = False
    TESTING = True
    SECRET_KEY = 'testing-secret-key'
    
    # Database - Use in-memory database for testing
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///:memory:')
    
    # Logging - Minimal logging during tests
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING')
    LOG_TO_FILE = False
    
    # FTMS Settings - Always use simulator for testing
    USE_SIMULATOR = True
    SIMULATOR_DEVICE_TYPE = 'bike'
    CONNECTION_TIMEOUT = 5  # Short timeout for tests
    RECONNECTION_ATTEMPTS = 1  # Minimal retries for tests
    
    # Performance settings - Fast settings for testing
    CHART_UPDATE_INTERVAL = 100  # Very fast updates
    DATA_RETENTION_DAYS = 1  # Minimal retention
    CACHE_TIMEOUT = 1  # Very short cache
    
    # Testing-specific settings
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    
    # Security settings (disabled for testing)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = False
    
    # File storage - Use temporary directories
    DATA_PATH = '/tmp/rogue_garmin_bridge_test/data'
    LOGS_PATH = '/tmp/rogue_garmin_bridge_test/logs'
    FIT_FILES_PATH = '/tmp/rogue_garmin_bridge_test/fit_files'
    BACKUP_PATH = '/tmp/rogue_garmin_bridge_test/backups'
    
    # Health check settings (minimal for testing)
    HEALTH_CHECK_ENABLED = False
    HEALTH_CHECK_DATABASE = False
    HEALTH_CHECK_BLUETOOTH = False
    
    # Disable metrics collection during testing
    METRICS_ENABLED = False
    
    @staticmethod
    def validate_config():
        """Validate testing configuration."""
        return True