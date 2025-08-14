"""
Simple cross-component integration test to verify basic functionality.
"""

import pytest
import tempfile
import os
import sqlite3
from datetime import datetime
import sys

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

try:
    from data.database import Database
except ImportError as e:
    print(f"Import error: {e}")
    Database = None


class TestSimpleCrossComponent:
    """Simple cross-component integration tests."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        if Database is None:
            pytest.skip("Database module not available")
            
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        
        self.database = Database(self.db_path)
        
        yield
        
        # Cleanup - close database connections first
        if hasattr(self, 'database') and hasattr(self.database, 'connections'):
            self.database.connections.close_connection()
        
        import shutil
        import time
        if os.path.exists(self.temp_dir):
            # Retry cleanup a few times on Windows
            for i in range(3):
                try:
                    shutil.rmtree(self.temp_dir)
                    break
                except PermissionError:
                    time.sleep(0.1)
                    if i == 2:  # Last attempt
                        pass  # Ignore cleanup error
    
    def test_database_basic_operations(self):
        """Test basic database operations work."""
        # Test device creation
        device_id = self.database.add_device("AA:BB:CC:DD:EE:FF", "Test Device", "bike")
        assert device_id is not None, "Should create device"
        
        # Test workout creation
        workout_id = self.database.start_workout(device_id, "bike")
        assert workout_id is not None, "Should create workout"
        
        # Test data addition
        success = self.database.add_workout_data(
            workout_id, 
            datetime.now(), 
            {'power': 150, 'heart_rate': 140}
        )
        assert success, "Should add workout data"
        
        # Test workout ending
        success = self.database.end_workout(workout_id, summary={'avg_power': 150})
        assert success, "Should end workout"
        
        # Verify data retrieval
        workout = self.database.get_workout(workout_id)
        assert workout is not None, "Should retrieve workout"
        
        data_points = self.database.get_workout_data(workout_id)
        assert len(data_points) == 1, "Should have one data point"