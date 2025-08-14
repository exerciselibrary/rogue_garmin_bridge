"""Base configuration for Rogue Garmin Bridge."""

import os
from pathlib import Path


class Config:
    """Base configuration class."""
    
    # Application settings
    APP_NAME = 'Rogue Garmin Bridge'
    APP_VERSION = '1.0.0'
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # Database settings
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data/workouts.db')
    DATABASE_POOL_SIZE = 5
    DATABASE_POOL_TIMEOUT = 30
    DATABASE_POOL_RECYCLE = 3600
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_TO_FILE = True
    LOG_FILE_PATH = 'logs/rogue_garmin_bridge.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # FTMS settings
    USE_SIMULATOR = os.environ.get('USE_SIMULATOR', 'False').lower() == 'true'
    SIMULATOR_DEVICE_TYPE = os.environ.get('SIMULATOR_DEVICE_TYPE', 'bike')
    CONNECTION_TIMEOUT = int(os.environ.get('CONNECTION_TIMEOUT', '30'))
    RECONNECTION_ATTEMPTS = int(os.environ.get('RECONNECTION_ATTEMPTS', '3'))
    RECONNECTION_DELAY = int(os.environ.get('RECONNECTION_DELAY', '5'))
    SIGNAL_THRESHOLD = int(os.environ.get('SIGNAL_THRESHOLD', '-70'))
    DATA_QUALITY_THRESHOLD = float(os.environ.get('DATA_QUALITY_THRESHOLD', '0.8'))
    
    # Workout settings
    DEFAULT_RECORDING_INTERVAL = int(os.environ.get('DEFAULT_RECORDING_INTERVAL', '1'))
    MAX_WORKOUT_DURATION = int(os.environ.get('MAX_WORKOUT_DURATION', '14400'))  # 4 hours
    AUTO_PAUSE_THRESHOLD = int(os.environ.get('AUTO_PAUSE_THRESHOLD', '30'))  # seconds
    POWER_SMOOTHING_WINDOW = int(os.environ.get('POWER_SMOOTHING_WINDOW', '3'))
    
    # Performance settings
    CHART_UPDATE_INTERVAL = int(os.environ.get('CHART_UPDATE_INTERVAL', '1000'))  # milliseconds
    DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS', '365'))
    MAX_CONCURRENT_WORKOUTS = int(os.environ.get('MAX_CONCURRENT_WORKOUTS', '1'))
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', '300'))  # 5 minutes
    
    # File storage settings
    DATA_PATH = Path(os.environ.get('DATA_PATH', 'data'))
    LOGS_PATH = Path(os.environ.get('LOGS_PATH', 'logs'))
    FIT_FILES_PATH = Path(os.environ.get('FIT_FILES_PATH', 'fit_files'))
    BACKUP_PATH = Path(os.environ.get('BACKUP_PATH', 'backups'))
    
    # FIT file settings
    FIT_MANUFACTURER_ID = int(os.environ.get('FIT_MANUFACTURER_ID', '255'))  # Development
    FIT_PRODUCT_ID = int(os.environ.get('FIT_PRODUCT_ID', '1'))
    MAX_FIT_FILE_AGE_DAYS = int(os.environ.get('MAX_FIT_FILE_AGE_DAYS', '30'))
    
    # Security settings
    SESSION_COOKIE_SECURE = False  # Override in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # API settings
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT', '100 per minute')
    API_TIMEOUT = int(os.environ.get('API_TIMEOUT', '30'))
    
    # Health check settings
    HEALTH_CHECK_ENABLED = True
    HEALTH_CHECK_DATABASE = True
    HEALTH_CHECK_BLUETOOTH = True
    HEALTH_CHECK_DISK_SPACE = True
    HEALTH_CHECK_MEMORY = True
    
    # Monitoring settings
    METRICS_ENABLED = os.environ.get('METRICS_ENABLED', 'True').lower() == 'true'
    METRICS_RETENTION_DAYS = int(os.environ.get('METRICS_RETENTION_DAYS', '7'))
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories if they don't exist."""
        directories = [
            cls.DATA_PATH,
            cls.LOGS_PATH,
            cls.FIT_FILES_PATH,
            cls.BACKUP_PATH
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def validate_config():
        """Validate configuration settings."""
        return True