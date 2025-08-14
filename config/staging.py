"""Staging configuration for Rogue Garmin Bridge."""

import os
from .base import Config


class StagingConfig(Config):
    """Staging configuration class."""
    
    # Flask settings
    DEBUG = True
    TESTING = False
    
    # Security settings (less strict for staging)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'staging-secret-key')
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Database settings
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data/workouts_staging.db')
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    LOG_TO_FILE = True
    LOG_FILE_PATH = 'logs/rogue_garmin_bridge_staging.log'
    
    # Performance settings
    CACHE_TIMEOUT = 300  # 5 minutes
    DATA_RETENTION_DAYS = 30  # Shorter retention for staging
    
    # API settings
    API_RATE_LIMIT = '200 per minute'  # More lenient for testing
    
    # Monitoring
    METRICS_ENABLED = True
    HEALTH_CHECK_ENABLED = True
    
    # FTMS settings - allow simulator for staging
    USE_SIMULATOR = os.environ.get('USE_SIMULATOR', 'True').lower() == 'true'
    SIMULATOR_DEVICE_TYPE = os.environ.get('SIMULATOR_DEVICE_TYPE', 'bike')
    CONNECTION_TIMEOUT = 20
    RECONNECTION_ATTEMPTS = 3
    
    # File cleanup settings (more aggressive for staging)
    MAX_FIT_FILE_AGE_DAYS = 7
    
    @staticmethod
    def validate_config():
        """Validate staging configuration."""
        return True