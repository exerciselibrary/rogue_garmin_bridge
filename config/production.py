"""Production configuration for Rogue Garmin Bridge."""

import os
from .base import Config


class ProductionConfig(Config):
    """Production configuration class."""
    
    # Flask settings
    DEBUG = False
    TESTING = False
    
    # Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Database settings
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data/workouts.db')
    DATABASE_POOL_SIZE = 10
    DATABASE_POOL_TIMEOUT = 30
    DATABASE_POOL_RECYCLE = 3600
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_TO_FILE = True
    LOG_FILE_PATH = 'logs/rogue_garmin_bridge.log'
    
    # Performance settings
    CACHE_TIMEOUT = 600  # 10 minutes
    DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS', '365'))
    
    # Security and rate limiting
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT', '100 per minute')
    API_TIMEOUT = 30
    
    # Monitoring
    METRICS_ENABLED = True
    HEALTH_CHECK_ENABLED = True
    
    # FTMS settings for production
    USE_SIMULATOR = False  # Always use real devices in production
    CONNECTION_TIMEOUT = int(os.environ.get('CONNECTION_TIMEOUT', '30'))
    RECONNECTION_ATTEMPTS = int(os.environ.get('RECONNECTION_ATTEMPTS', '5'))
    RECONNECTION_DELAY = int(os.environ.get('RECONNECTION_DELAY', '10'))
    
    @staticmethod
    def validate_config():
        """Validate production configuration."""
        required_env_vars = [
            'SECRET_KEY',
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True