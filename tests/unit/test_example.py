"""
Example unit test to verify test framework setup.
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestExampleFramework:
    """Example test class to verify framework setup."""
    
    def test_basic_assertion(self):
        """Test basic assertion functionality."""
        assert True
        assert 1 + 1 == 2
        assert "hello" in "hello world"
    
    def test_datetime_operations(self):
        """Test datetime operations."""
        now = datetime.now()
        future = now + timedelta(seconds=10)
        
        assert future > now
        assert (future - now).total_seconds() == 10
    
    def test_list_operations(self):
        """Test list operations."""
        test_list = [1, 2, 3, 4, 5]
        
        assert len(test_list) == 5
        assert 3 in test_list
        assert test_list[0] == 1
        assert test_list[-1] == 5
    
    def test_dictionary_operations(self):
        """Test dictionary operations."""
        test_dict = {
            "name": "Test Device",
            "type": "bike",
            "power": 150
        }
        
        assert test_dict["name"] == "Test Device"
        assert test_dict.get("type") == "bike"
        assert "power" in test_dict
        assert test_dict.get("missing_key", "default") == "default"
    
    @pytest.mark.parametrize("input_value,expected", [
        (0, 0),
        (1, 1),
        (2, 4),
        (3, 9),
        (4, 16),
        (5, 25)
    ])
    def test_parametrized_square(self, input_value, expected):
        """Test parametrized square function."""
        assert input_value ** 2 == expected
    
    def test_exception_handling(self):
        """Test exception handling."""
        with pytest.raises(ValueError):
            int("not_a_number")
        
        with pytest.raises(KeyError):
            test_dict = {"key": "value"}
            _ = test_dict["missing_key"]
        
        with pytest.raises(ZeroDivisionError):
            _ = 1 / 0


class TestFixtureUsage:
    """Test fixture usage from conftest.py."""
    
    def test_sample_workout_data_fixture(self, sample_workout_data):
        """Test sample workout data fixture."""
        assert "bike_workout" in sample_workout_data
        assert "rower_workout" in sample_workout_data
        
        bike_data = sample_workout_data["bike_workout"]
        assert bike_data["device_type"] == "bike"
        assert bike_data["duration"] == 1200
        assert len(bike_data["data_points"]) > 0
        
        # Check first data point structure
        first_point = bike_data["data_points"][0]
        assert "timestamp" in first_point
        assert "power" in first_point
        assert "cadence" in first_point
        assert "speed" in first_point
    
    def test_realistic_workout_scenarios_fixture(self, realistic_workout_scenarios):
        """Test realistic workout scenarios fixture."""
        assert "short_bike_workout" in realistic_workout_scenarios
        assert "medium_bike_workout" in realistic_workout_scenarios
        assert "interval_bike_workout" in realistic_workout_scenarios
        assert "rower_workout" in realistic_workout_scenarios
        
        short_workout = realistic_workout_scenarios["short_bike_workout"]
        assert short_workout["device_type"] == "bike"
        assert short_workout["duration"] == 300
        assert "phases" in short_workout
    
    def test_expected_fit_file_structure_fixture(self, expected_fit_file_structure):
        """Test expected FIT file structure fixture."""
        assert "required_messages" in expected_fit_file_structure
        assert "file_id" in expected_fit_file_structure["required_messages"]
        assert "activity" in expected_fit_file_structure["required_messages"]
        assert "session" in expected_fit_file_structure["required_messages"]
        assert "lap" in expected_fit_file_structure["required_messages"]
        assert "record" in expected_fit_file_structure["required_messages"]
    
    def test_test_data_factory_fixture(self, test_data_factory):
        """Test data factory fixture."""
        # Test workout session creation
        bike_session = test_data_factory.create_workout_session("bike", 300)
        assert bike_session["device_type"] == "bike"
        assert bike_session["duration"] == 300
        assert len(bike_session["data_points"]) == 300
        
        rower_session = test_data_factory.create_workout_session("rower", 600)
        assert rower_session["device_type"] == "rower"
        assert rower_session["duration"] == 600
        assert len(rower_session["data_points"]) == 600
        
        # Check data point structure
        bike_point = bike_session["data_points"][0]
        assert "power" in bike_point
        assert "cadence" in bike_point
        assert "speed" in bike_point
        
        rower_point = rower_session["data_points"][0]
        assert "power" in rower_point
        assert "stroke_rate" in rower_point
        assert "stroke_count" in rower_point


@pytest.mark.slow
class TestSlowOperations:
    """Test slow operations (marked for separate execution)."""
    
    def test_long_running_operation(self):
        """Test a long-running operation."""
        import time
        
        start_time = datetime.now()
        time.sleep(1)  # Simulate slow operation
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        assert duration >= 1.0
    
    def test_large_data_processing(self):
        """Test processing large amounts of data."""
        large_list = list(range(100000))
        
        # Process the data
        result = sum(x * x for x in large_list)
        
        # Verify result
        expected = sum(x * x for x in range(100000))
        assert result == expected


class TestEnvironmentSetup:
    """Test environment setup and configuration."""
    
    def test_testing_environment_variable(self):
        """Test that testing environment is properly set."""
        # This should be set by the autouse fixture in conftest.py
        assert os.environ.get("TESTING") == "true"
    
    def test_log_level_environment_variable(self):
        """Test that log level is set for testing."""
        assert os.environ.get("LOG_LEVEL") == "DEBUG"
    
    def test_python_path_setup(self):
        """Test that Python path includes src directory."""
        # Check that we can import from src
        try:
            # This should work if the path is set up correctly
            import sys
            src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
            assert any(src_path in path for path in sys.path)
        except ImportError:
            pytest.fail("Cannot import from src directory - path not set up correctly")