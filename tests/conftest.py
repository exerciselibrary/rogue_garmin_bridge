"""
Pytest configuration and shared fixtures for the Rogue Garmin Bridge test suite.
"""

import pytest
import tempfile
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Generator
from unittest.mock import Mock, MagicMock
import json

# Add src to Python path for imports
import sys
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import modules with error handling for missing components
try:
    from data.database import Database
except ImportError:
    Database = None

try:
    from data.workout_manager import WorkoutManager
except ImportError:
    WorkoutManager = None

try:
    from ftms.ftms_manager import FTMSManager
except ImportError:
    FTMSManager = None

try:
    from ftms.ftms_simulator import FTMSSimulator
except ImportError:
    FTMSSimulator = None

try:
    from fit.fit_converter import FITConverter
except ImportError:
    FITConverter = None


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def test_database(test_data_dir):
    """Create a test database with clean state for each test."""
    if Database is None:
        pytest.skip("Database module not available")
    
    db_path = os.path.join(test_data_dir, "test_rogue_garmin.db")
    
    # Create test database
    db = Database(db_path)
    db.initialize_database()
    
    yield db
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def sample_workout_data():
    """Provide sample workout data for testing."""
    return {
        "bike_workout": {
            "device_type": "bike",
            "duration": 1200,  # 20 minutes
            "data_points": [
                {
                    "timestamp": datetime.now() - timedelta(seconds=1200-i),
                    "power": 150 + (i % 50),
                    "cadence": 80 + (i % 20),
                    "speed": 25.0 + (i % 5),
                    "heart_rate": 140 + (i % 30),
                    "distance": i * 0.1,
                    "calories": i * 0.5
                }
                for i in range(0, 1200, 10)  # Every 10 seconds
            ]
        },
        "rower_workout": {
            "device_type": "rower",
            "duration": 900,  # 15 minutes
            "data_points": [
                {
                    "timestamp": datetime.now() - timedelta(seconds=900-i),
                    "power": 200 + (i % 100),
                    "stroke_rate": 24 + (i % 8),
                    "heart_rate": 150 + (i % 25),
                    "distance": i * 0.15,
                    "calories": i * 0.7,
                    "stroke_count": i // 2
                }
                for i in range(0, 900, 10)  # Every 10 seconds
            ]
        }
    }


@pytest.fixture
def mock_ftms_device():
    """Create a mock FTMS device for testing."""
    device = Mock()
    device.name = "Test Rogue Echo Bike"
    device.address = "AA:BB:CC:DD:EE:FF"
    device.is_connected = True
    device.device_type = "bike"
    
    # Mock device characteristics
    device.power = 150
    device.cadence = 80
    device.speed = 25.0
    device.heart_rate = 140
    device.distance = 1000
    device.calories = 50
    
    return device


@pytest.fixture
def mock_ftms_manager(mock_ftms_device):
    """Create a mock FTMS Manager for testing."""
    if FTMSManager is None:
        # Create a basic mock if the real class isn't available
        manager = Mock()
    else:
        manager = Mock(spec=FTMSManager)
    
    manager.connected_devices = [mock_ftms_device]
    manager.is_scanning = False
    manager.callbacks = []
    
    # Mock methods
    manager.start_scanning = Mock()
    manager.stop_scanning = Mock()
    manager.connect_device = Mock(return_value=True)
    manager.disconnect_device = Mock(return_value=True)
    manager.register_callback = Mock()
    manager.unregister_callback = Mock()
    
    return manager


@pytest.fixture
def ftms_simulator():
    """Create an FTMS simulator for testing."""
    if FTMSSimulator is None:
        pytest.skip("FTMSSimulator module not available")
    
    simulator = FTMSSimulator(device_type="bike")
    yield simulator
    simulator.stop()


@pytest.fixture
def workout_manager(test_database):
    """Create a WorkoutManager instance with test database."""
    if WorkoutManager is None:
        pytest.skip("WorkoutManager module not available")
    return WorkoutManager(database=test_database)


@pytest.fixture
def fit_converter():
    """Create a FIT converter instance for testing."""
    if FITConverter is None:
        pytest.skip("FITConverter module not available")
    return FITConverter()


@pytest.fixture
def realistic_workout_scenarios():
    """Provide realistic workout scenarios based on workout.log analysis."""
    return {
        "short_bike_workout": {
            "name": "Short Bike Workout",
            "device_type": "bike",
            "duration": 300,  # 5 minutes
            "phases": [
                {"name": "warmup", "duration": 120, "avg_power": 100, "avg_cadence": 70},
                {"name": "main", "duration": 120, "avg_power": 180, "avg_cadence": 85},
                {"name": "cooldown", "duration": 60, "avg_power": 80, "avg_cadence": 60}
            ]
        },
        "medium_bike_workout": {
            "name": "Medium Bike Workout",
            "device_type": "bike", 
            "duration": 1200,  # 20 minutes
            "phases": [
                {"name": "warmup", "duration": 300, "avg_power": 120, "avg_cadence": 75},
                {"name": "main", "duration": 600, "avg_power": 200, "avg_cadence": 90},
                {"name": "cooldown", "duration": 300, "avg_power": 100, "avg_cadence": 65}
            ]
        },
        "interval_bike_workout": {
            "name": "Interval Bike Workout",
            "device_type": "bike",
            "duration": 1800,  # 30 minutes
            "phases": [
                {"name": "warmup", "duration": 300, "avg_power": 130, "avg_cadence": 75},
                {"name": "interval_high", "duration": 120, "avg_power": 280, "avg_cadence": 100},
                {"name": "interval_low", "duration": 180, "avg_power": 150, "avg_cadence": 80},
                {"name": "interval_high", "duration": 120, "avg_power": 280, "avg_cadence": 100},
                {"name": "interval_low", "duration": 180, "avg_power": 150, "avg_cadence": 80},
                {"name": "interval_high", "duration": 120, "avg_power": 280, "avg_cadence": 100},
                {"name": "interval_low", "duration": 180, "avg_power": 150, "avg_cadence": 80},
                {"name": "cooldown", "duration": 495, "avg_power": 110, "avg_cadence": 70}
            ]
        },
        "rower_workout": {
            "name": "Standard Rower Workout",
            "device_type": "rower",
            "duration": 1200,  # 20 minutes
            "phases": [
                {"name": "warmup", "duration": 300, "avg_power": 150, "avg_stroke_rate": 20},
                {"name": "main", "duration": 600, "avg_power": 220, "avg_stroke_rate": 26},
                {"name": "cooldown", "duration": 300, "avg_power": 120, "avg_stroke_rate": 18}
            ]
        }
    }


@pytest.fixture
def expected_fit_file_structure():
    """Define expected FIT file structure for validation."""
    return {
        "required_messages": [
            "file_id",
            "activity", 
            "session",
            "lap",
            "record"
        ],
        "file_id_fields": [
            "type",
            "manufacturer",
            "product",
            "time_created"
        ],
        "activity_fields": [
            "timestamp",
            "total_timer_time",
            "type",
            "event",
            "event_type"
        ],
        "session_fields": [
            "timestamp",
            "start_time",
            "total_elapsed_time",
            "total_timer_time",
            "total_distance",
            "total_calories",
            "avg_power",
            "max_power",
            "sport",
            "sub_sport"
        ],
        "record_fields": [
            "timestamp",
            "power",
            "heart_rate",
            "distance",
            "calories"
        ]
    }


class MockBluetoothDevice:
    """Mock Bluetooth device for testing FTMS connections."""
    
    def __init__(self, name: str = "Test Device", address: str = "AA:BB:CC:DD:EE:FF"):
        self.name = name
        self.address = address
        self.is_connected = False
        self.services = {}
        self.characteristics = {}
        
    async def connect(self):
        self.is_connected = True
        return True
        
    async def disconnect(self):
        self.is_connected = False
        return True
        
    async def read_gatt_char(self, char_uuid):
        # Return mock data based on characteristic
        if "2ad2" in char_uuid.lower():  # Indoor Bike Data
            return b'\x44\x02\x96\x00\x50\x00\x19\x00\x8c\x00'  # Mock bike data
        elif "2ad1" in char_uuid.lower():  # Rower Data  
            return b'\x3c\x00\xdc\x00\x1a\x00\x96\x00'  # Mock rower data
        return b'\x00\x00'


@pytest.fixture
def mock_bluetooth_device():
    """Provide a mock Bluetooth device for testing."""
    return MockBluetoothDevice()


class TestDataFactory:
    """Factory class for generating test data."""
    
    @staticmethod
    def create_workout_session(device_type: str = "bike", duration: int = 600) -> Dict[str, Any]:
        """Create a complete workout session with realistic data."""
        start_time = datetime.now() - timedelta(seconds=duration)
        
        session = {
            "id": 1,
            "device_type": device_type,
            "start_time": start_time,
            "end_time": start_time + timedelta(seconds=duration),
            "duration": duration,
            "data_points": []
        }
        
        # Generate data points every second
        for i in range(duration):
            timestamp = start_time + timedelta(seconds=i)
            
            if device_type == "bike":
                data_point = {
                    "timestamp": timestamp,
                    "power": 150 + (i % 100),
                    "cadence": 80 + (i % 20),
                    "speed": 25.0 + (i % 10),
                    "heart_rate": 140 + (i % 30),
                    "distance": i * 0.1,
                    "calories": i * 0.5
                }
            else:  # rower
                data_point = {
                    "timestamp": timestamp,
                    "power": 200 + (i % 80),
                    "stroke_rate": 24 + (i % 8),
                    "heart_rate": 150 + (i % 25),
                    "distance": i * 0.15,
                    "calories": i * 0.7,
                    "stroke_count": i // 2
                }
            
            session["data_points"].append(data_point)
        
        return session
    
    @staticmethod
    def create_fit_file_data(workout_session: Dict[str, Any]) -> bytes:
        """Create mock FIT file data for testing."""
        # This would normally generate actual FIT file bytes
        # For testing, we'll return a mock byte sequence
        return b'\x0e\x10\x43\x08\x78\x00\x00\x00.FIT'


@pytest.fixture
def test_data_factory():
    """Provide the test data factory."""
    return TestDataFactory


# Pytest hooks for custom test behavior
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "simulator: Simulator tests")
    config.addinivalue_line("markers", "fit_validation: FIT file validation tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "simulator" in str(item.fspath):
            item.add_marker(pytest.mark.simulator)
        elif "fit_validation" in str(item.fspath):
            item.add_marker(pytest.mark.fit_validation)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically set up test environment for each test."""
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # Cleanup after test
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
    if "LOG_LEVEL" in os.environ:
        del os.environ["LOG_LEVEL"]