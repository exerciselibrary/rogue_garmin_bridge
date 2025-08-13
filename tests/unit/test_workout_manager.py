#!/usr/bin/env python3
"""
Unit tests for Workout Manager Module

Tests workout session lifecycle, data validation, metric calculations, and database integration.
"""

import pytest
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data.workout_manager import WorkoutManager
from src.data.database import Database


class TestWorkoutManager:
    """Test cases for WorkoutManager class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Create mock FTMS manager
        self.mock_ftms_manager = Mock()
        
        # Initialize workout manager
        self.workout_manager = WorkoutManager(
            db_path=self.db_path,
            ftms_manager=self.mock_ftms_manager
        )
    
    def teardown_method(self):
        """Clean up after each test method."""
        # Close database connections
        if hasattr(self.workout_manager, 'database'):
            self.workout_manager.database.connections.close_connection()
        
        # Remove temporary database file
        try:
            os.unlink(self.db_path)
        except OSError:
            pass
    
    def test_init_with_ftms_manager(self):
        """Test initialization with FTMS manager."""
        assert self.workout_manager.database is not None
        assert self.workout_manager.ftms_manager == self.mock_ftms_manager
        assert self.workout_manager.active_workout_id is None
        assert self.workout_manager.active_device_id is None
        assert self.workout_manager.workout_start_time is None
        assert self.workout_manager.workout_type is None
        assert len(self.workout_manager.data_points) == 0
        assert len(self.workout_manager.summary_metrics) == 0
        
        # Check that callbacks were registered with FTMS manager
        self.mock_ftms_manager.register_data_callback.assert_called_once()
        self.mock_ftms_manager.register_status_callback.assert_called_once()
    
    def test_init_without_ftms_manager(self):
        """Test initialization without FTMS manager."""
        manager = WorkoutManager(db_path=self.db_path)
        
        assert manager.database is not None
        assert manager.ftms_manager is None
        assert manager.active_workout_id is None
    
    def test_register_data_callback(self):
        """Test registering data callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        self.workout_manager.register_data_callback(callback1)
        self.workout_manager.register_data_callback(callback2)
        
        assert len(self.workout_manager.data_callbacks) == 2
        assert callback1 in self.workout_manager.data_callbacks
        assert callback2 in self.workout_manager.data_callbacks
    
    def test_register_status_callback(self):
        """Test registering status callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        self.workout_manager.register_status_callback(callback1)
        self.workout_manager.register_status_callback(callback2)
        
        assert len(self.workout_manager.status_callbacks) == 2
        assert callback1 in self.workout_manager.status_callbacks
        assert callback2 in self.workout_manager.status_callbacks
    
    def test_start_workout_success(self):
        """Test successful workout start."""
        device_id = 1
        workout_type = "bike"
        
        # Mock database start_workout to return workout ID
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            workout_id = self.workout_manager.start_workout(device_id, workout_type)
        
        assert workout_id == 123
        assert self.workout_manager.active_workout_id == 123
        assert self.workout_manager.active_device_id == device_id
        assert self.workout_manager.workout_type == workout_type
        assert self.workout_manager.workout_start_time is not None
        assert len(self.workout_manager.data_points) == 0
        
        # Check summary metrics initialization
        expected_metrics = {
            'total_distance': 0,
            'total_calories': 0,
            'avg_power': 0,
            'max_power': 0,
            'avg_heart_rate': 0,
            'max_heart_rate': 0,
            'avg_cadence': 0,
            'max_cadence': 0,
            'avg_speed': 0,
            'max_speed': 0,
            'total_strokes': 0,
            'avg_stroke_rate': 0,
            'max_stroke_rate': 0,
        }
        assert self.workout_manager.summary_metrics == expected_metrics
    
    def test_start_workout_with_active_workout(self):
        """Test starting workout when one is already active."""
        # Start first workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        # Mock end_workout for the active workout
        with patch.object(self.workout_manager, 'end_workout', return_value=True) as mock_end:
            with patch.object(self.workout_manager.database, 'start_workout', return_value=456):
                workout_id = self.workout_manager.start_workout(2, "rower")
        
        # Should end previous workout and start new one
        mock_end.assert_called_once()
        assert workout_id == 456
        assert self.workout_manager.active_workout_id == 456
        assert self.workout_manager.active_device_id == 2
        assert self.workout_manager.workout_type == "rower"
    
    def test_end_workout_success(self):
        """Test successful workout end."""
        # Start a workout first
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        # Add some test data
        self.workout_manager.data_points = [
            {'power': 150, 'heart_rate': 140},
            {'power': 160, 'heart_rate': 145}
        ]
        
        # Mock database end_workout and FIT processor
        with patch.object(self.workout_manager.database, 'end_workout', return_value=True):
            with patch('src.fit.fit_processor.FITProcessor') as mock_fit_processor:
                mock_processor_instance = Mock()
                mock_processor_instance.process_workout.return_value = '/path/to/fit/file.fit'
                mock_fit_processor.return_value = mock_processor_instance
                
                result = self.workout_manager.end_workout()
        
        assert result is True
        assert self.workout_manager.active_workout_id is None
        assert self.workout_manager.active_device_id is None
        assert self.workout_manager.workout_start_time is None
        assert self.workout_manager.workout_type is None
        assert len(self.workout_manager.data_points) == 0
        assert len(self.workout_manager.summary_metrics) == 0
    
    def test_end_workout_no_active(self):
        """Test ending workout when none is active."""
        result = self.workout_manager.end_workout()
        
        assert result is False
    
    def test_end_workout_database_error(self):
        """Test ending workout with database error."""
        # Start a workout first
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        # Mock database end_workout to return False
        with patch.object(self.workout_manager.database, 'end_workout', return_value=False):
            result = self.workout_manager.end_workout()
        
        assert result is False
    
    def test_add_data_point_success(self):
        """Test successful data point addition."""
        # Start a workout first
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        test_data = {
            'instantaneous_power': 150,
            'heart_rate': 140,
            'instantaneous_cadence': 85,
            'instantaneous_speed': 25.0
        }
        
        # Mock database add_workout_data
        with patch.object(self.workout_manager.database, 'add_workout_data', return_value=True):
            result = self.workout_manager.add_data_point(test_data)
        
        assert result is True
        assert len(self.workout_manager.data_points) == 1
        
        # Check that data point was added with timestamp
        data_point = self.workout_manager.data_points[0]
        assert 'timestamp' in data_point
        assert data_point['instantaneous_power'] == 150
        assert data_point['heart_rate'] == 140
    
    def test_add_data_point_no_active_workout(self):
        """Test adding data point when no workout is active."""
        test_data = {'power': 150}
        
        result = self.workout_manager.add_data_point(test_data)
        
        assert result is False
    
    def test_add_data_point_database_error(self):
        """Test adding data point with database error."""
        # Start a workout first
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        test_data = {'power': 150}
        
        # Mock database add_workout_data to return False
        with patch.object(self.workout_manager.database, 'add_workout_data', return_value=False):
            result = self.workout_manager.add_data_point(test_data)
        
        assert result is False
    
    def test_update_bike_metrics_power(self):
        """Test updating bike metrics with power data."""
        # Start a bike workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        # Add data points with power
        test_data1 = {'instant_power': 150, 'timestamp': datetime.now().isoformat()}
        test_data2 = {'instant_power': 200, 'timestamp': datetime.now().isoformat()}
        
        self.workout_manager.data_points = [test_data1]
        self.workout_manager._update_bike_metrics(test_data1)
        
        assert self.workout_manager.summary_metrics['max_power'] == 150
        
        self.workout_manager.data_points.append(test_data2)
        self.workout_manager._update_bike_metrics(test_data2)
        
        assert self.workout_manager.summary_metrics['max_power'] == 200
        assert self.workout_manager.summary_metrics['avg_power'] == 175  # (150 + 200) / 2
    
    def test_update_bike_metrics_heart_rate(self):
        """Test updating bike metrics with heart rate data."""
        # Start a bike workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        # Add data points with heart rate
        test_data1 = {'heart_rate': 140, 'timestamp': datetime.now().isoformat()}
        test_data2 = {'heart_rate': 160, 'timestamp': datetime.now().isoformat()}
        
        self.workout_manager.data_points = [test_data1]
        self.workout_manager._update_bike_metrics(test_data1)
        
        assert self.workout_manager.summary_metrics['max_heart_rate'] == 140
        
        self.workout_manager.data_points.append(test_data2)
        self.workout_manager._update_bike_metrics(test_data2)
        
        assert self.workout_manager.summary_metrics['max_heart_rate'] == 160
        assert self.workout_manager.summary_metrics['avg_heart_rate'] == 150  # (140 + 160) / 2
    
    def test_update_bike_metrics_cadence(self):
        """Test updating bike metrics with cadence data."""
        # Start a bike workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        # Add data points with cadence
        test_data1 = {'instant_cadence': 80, 'timestamp': datetime.now().isoformat()}
        test_data2 = {'instant_cadence': 90, 'timestamp': datetime.now().isoformat()}
        
        self.workout_manager.data_points = [test_data1]
        self.workout_manager._update_bike_metrics(test_data1)
        
        assert self.workout_manager.summary_metrics['max_cadence'] == 80
        
        self.workout_manager.data_points.append(test_data2)
        self.workout_manager._update_bike_metrics(test_data2)
        
        assert self.workout_manager.summary_metrics['max_cadence'] == 90
        assert self.workout_manager.summary_metrics['avg_cadence'] == 85  # (80 + 90) / 2
    
    def test_update_bike_metrics_speed_with_outlier_filtering(self):
        """Test updating bike metrics with speed data and outlier filtering."""
        # Start a bike workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        # Add multiple data points with speeds including outliers
        speeds = [25.0, 26.0, 24.0, 25.5, 100.0, 26.5, 24.5]  # 100.0 is an outlier
        data_points = []
        
        for i, speed in enumerate(speeds):
            data_point = {
                'instant_speed': speed,
                'timestamp': (datetime.now() + timedelta(seconds=i)).isoformat()
            }
            data_points.append(data_point)
            self.workout_manager.data_points.append(data_point)
            self.workout_manager._update_bike_metrics(data_point)
        
        # Max speed should include the outlier
        assert self.workout_manager.summary_metrics['max_speed'] == 100.0
        
        # Average speed should filter out the outlier
        # Expected average without outlier: (25.0 + 26.0 + 24.0 + 25.5 + 26.5 + 24.5) / 6 = 25.25
        avg_speed = self.workout_manager.summary_metrics['avg_speed']
        assert abs(avg_speed - 25.25) < 0.1  # Allow small floating point differences
    
    def test_update_bike_metrics_distance(self):
        """Test updating bike metrics with distance data."""
        # Start a bike workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        test_data = {'total_distance': 5000.0}
        self.workout_manager._update_bike_metrics(test_data)
        
        assert self.workout_manager.summary_metrics['total_distance'] == 5000.0
    
    def test_update_bike_metrics_calories(self):
        """Test updating bike metrics with calories data."""
        # Start a bike workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        test_data = {'total_energy': 250}
        self.workout_manager._update_bike_metrics(test_data)
        
        assert self.workout_manager.summary_metrics['total_calories'] == 250
    
    def test_update_rower_metrics_power(self):
        """Test updating rower metrics with power data."""
        # Start a rower workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "rower")
        
        # Add data points with power
        test_data1 = {'instantaneous_power': 180, 'timestamp': datetime.now().isoformat()}
        test_data2 = {'instantaneous_power': 220, 'timestamp': datetime.now().isoformat()}
        
        self.workout_manager.data_points = [test_data1]
        self.workout_manager._update_rower_metrics(test_data1)
        
        assert self.workout_manager.summary_metrics['max_power'] == 180
        
        self.workout_manager.data_points.append(test_data2)
        self.workout_manager._update_rower_metrics(test_data2)
        
        assert self.workout_manager.summary_metrics['max_power'] == 220
        assert self.workout_manager.summary_metrics['avg_power'] == 200  # (180 + 220) / 2
    
    def test_update_rower_metrics_stroke_rate(self):
        """Test updating rower metrics with stroke rate data."""
        # Start a rower workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "rower")
        
        # Add data points with stroke rate
        test_data1 = {'stroke_rate': 24, 'timestamp': datetime.now().isoformat()}
        test_data2 = {'stroke_rate': 28, 'timestamp': datetime.now().isoformat()}
        
        self.workout_manager.data_points = [test_data1]
        self.workout_manager._update_rower_metrics(test_data1)
        
        assert self.workout_manager.summary_metrics['max_stroke_rate'] == 24
        
        self.workout_manager.data_points.append(test_data2)
        self.workout_manager._update_rower_metrics(test_data2)
        
        assert self.workout_manager.summary_metrics['max_stroke_rate'] == 28
        assert self.workout_manager.summary_metrics['avg_stroke_rate'] == 26  # (24 + 28) / 2
    
    def test_update_rower_metrics_stroke_count(self):
        """Test updating rower metrics with stroke count data."""
        # Start a rower workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "rower")
        
        test_data = {'stroke_count': 150}
        self.workout_manager._update_rower_metrics(test_data)
        
        assert self.workout_manager.summary_metrics['total_strokes'] == 150
    
    def test_get_workout_summary_metrics_active_workout(self):
        """Test getting summary metrics for active workout."""
        # Start a workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        # Set some metrics
        self.workout_manager.summary_metrics = {
            'avg_power': 150.5,
            'max_power': 200,
            'avg_heart_rate': 140.7,
            'total_distance': 5000.0
        }
        
        summary = self.workout_manager.get_workout_summary_metrics()
        
        assert summary['avg_power'] == 150.5  # Rounded to 2 decimal places
        assert summary['max_power'] == 200
        assert summary['avg_heart_rate'] == 140.7  # Rounded to 2 decimal places
        assert summary['total_distance'] == 5000.0
        assert summary['workout_type'] == 'bike'
        assert 'elapsed_time' in summary
        assert summary['elapsed_time'] >= 0
    
    def test_get_workout_summary_metrics_no_active_workout(self):
        """Test getting summary metrics when no workout is active."""
        summary = self.workout_manager.get_workout_summary_metrics()
        
        assert summary == {}
    
    def test_get_workout_summary_metrics_with_vo2_estimation(self):
        """Test getting summary metrics with VO2 max estimation."""
        # Start a workout
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        # Set metrics for VO2 calculation
        self.workout_manager.summary_metrics = {
            'avg_power': 200,
            'avg_heart_rate': 150  # Above 120 threshold
        }
        
        # Mock user profile with weight
        mock_profile = {'weight_kg': 75.0}
        with patch.object(self.workout_manager, 'get_user_profile', return_value=mock_profile):
            summary = self.workout_manager.get_workout_summary_metrics()
        
        # VO2 = (200 / 75) * 10.8 + 7 = 2.67 * 10.8 + 7 = 35.8
        assert 'estimated_vo2max' in summary
        assert abs(summary['estimated_vo2max'] - 35.8) < 0.1
    
    def test_handle_ftms_data(self):
        """Test handling FTMS data."""
        test_data = {'power': 150, 'heart_rate': 140}
        
        # Mock add_data_point
        with patch.object(self.workout_manager, 'add_data_point') as mock_add:
            self.workout_manager._handle_ftms_data(test_data)
        
        mock_add.assert_called_once_with(test_data)
    
    def test_handle_ftms_status_device_found(self):
        """Test handling FTMS status for device found."""
        mock_device = Mock()
        mock_device.address = 'AA:BB:CC:DD:EE:FF'
        mock_device.name = 'Test Bike'
        mock_device.rssi = -50
        
        # Mock database add_device
        with patch.object(self.workout_manager.database, 'add_device') as mock_add:
            self.workout_manager._handle_ftms_status('device_found', mock_device)
        
        mock_add.assert_called_once_with(
            address='AA:BB:CC:DD:EE:FF',
            name='Test Bike',
            device_type='unknown',
            metadata={'rssi': -50}
        )
    
    def test_handle_ftms_status_connected_bike(self):
        """Test handling FTMS status for connected bike device."""
        mock_device = Mock()
        mock_device.address = 'AA:BB:CC:DD:EE:FF'
        mock_device.name = 'Test Bike'
        mock_device.rssi = -50
        
        # Mock database add_device to return device ID
        with patch.object(self.workout_manager.database, 'add_device', return_value=1):
            with patch.object(self.workout_manager, 'start_workout') as mock_start:
                self.workout_manager._handle_ftms_status('connected', mock_device)
        
        # Should start bike workout
        mock_start.assert_called_once_with(1, 'bike')
    
    def test_handle_ftms_status_connected_rower(self):
        """Test handling FTMS status for connected rower device."""
        mock_device = Mock()
        mock_device.address = 'AA:BB:CC:DD:EE:FF'
        mock_device.name = 'Test Rower'
        mock_device.rssi = -50
        
        # Mock database add_device to return device ID
        with patch.object(self.workout_manager.database, 'add_device', return_value=2):
            with patch.object(self.workout_manager, 'start_workout') as mock_start:
                self.workout_manager._handle_ftms_status('connected', mock_device)
        
        # Should start rower workout
        mock_start.assert_called_once_with(2, 'rower')
    
    def test_handle_ftms_status_disconnected(self):
        """Test handling FTMS status for disconnected device."""
        # Start a workout first
        with patch.object(self.workout_manager.database, 'start_workout', return_value=123):
            self.workout_manager.start_workout(1, "bike")
        
        # Mock end_workout
        with patch.object(self.workout_manager, 'end_workout') as mock_end:
            self.workout_manager._handle_ftms_status('disconnected', None)
        
        mock_end.assert_called_once()
    
    def test_notify_data_callbacks(self):
        """Test notifying data callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        self.workout_manager.register_data_callback(callback1)
        self.workout_manager.register_data_callback(callback2)
        
        test_data = {'power': 150}
        self.workout_manager._notify_data(test_data)
        
        callback1.assert_called_once_with(test_data)
        callback2.assert_called_once_with(test_data)
    
    def test_notify_data_callbacks_with_error(self):
        """Test notifying data callbacks when one raises exception."""
        error_callback = Mock(side_effect=Exception("Callback error"))
        good_callback = Mock()
        
        self.workout_manager.register_data_callback(error_callback)
        self.workout_manager.register_data_callback(good_callback)
        
        test_data = {'power': 150}
        
        # Should not raise exception
        self.workout_manager._notify_data(test_data)
        
        # Both callbacks should be called
        error_callback.assert_called_once_with(test_data)
        good_callback.assert_called_once_with(test_data)
    
    def test_notify_status_callbacks(self):
        """Test notifying status callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        self.workout_manager.register_status_callback(callback1)
        self.workout_manager.register_status_callback(callback2)
        
        self.workout_manager._notify_status('workout_started', {'id': 123})
        
        callback1.assert_called_once_with('workout_started', {'id': 123})
        callback2.assert_called_once_with('workout_started', {'id': 123})
    
    def test_notify_status_callbacks_with_error(self):
        """Test notifying status callbacks when one raises exception."""
        error_callback = Mock(side_effect=Exception("Callback error"))
        good_callback = Mock()
        
        self.workout_manager.register_status_callback(error_callback)
        self.workout_manager.register_status_callback(good_callback)
        
        # Should not raise exception
        self.workout_manager._notify_status('test_status', None)
        
        # Both callbacks should be called
        error_callback.assert_called_once_with('test_status', None)
        good_callback.assert_called_once_with('test_status', None)
    
    def test_database_integration_methods(self):
        """Test database integration methods."""
        # Test get_workout
        with patch.object(self.workout_manager.database, 'get_workout', return_value={'id': 123}):
            result = self.workout_manager.get_workout(123)
            assert result == {'id': 123}
        
        # Test get_workout_data
        with patch.object(self.workout_manager.database, 'get_workout_data', return_value=[{'data': 'test'}]):
            result = self.workout_manager.get_workout_data(123)
            assert result == [{'data': 'test'}]
        
        # Test get_workouts
        with patch.object(self.workout_manager.database, 'get_workouts', return_value=[{'id': 123}]):
            result = self.workout_manager.get_workouts(10, 0)
            assert result == [{'id': 123}]
        
        # Test get_devices
        with patch.object(self.workout_manager.database, 'get_devices', return_value=[{'id': 1}]):
            result = self.workout_manager.get_devices()
            assert result == [{'id': 1}]
        
        # Test get_user_profile
        with patch.object(self.workout_manager.database, 'get_user_profile', return_value={'name': 'Test'}):
            result = self.workout_manager.get_user_profile()
            assert result == {'name': 'Test'}
        
        # Test set_user_profile
        with patch.object(self.workout_manager.database, 'set_user_profile', return_value=True):
            result = self.workout_manager.set_user_profile({'name': 'Test'})
            assert result is True
    
    def test_update_workout_fit_file(self):
        """Test updating workout FIT file path."""
        with patch.object(self.workout_manager.database, 'update_workout_fit_path', return_value=True):
            result = self.workout_manager.update_workout_fit_file(123, '/path/to/file.fit')
            assert result is True
    
    def test_calculate_summary_metrics(self):
        """Test calculating final summary metrics."""
        # Set some metrics with decimal values
        self.workout_manager.summary_metrics = {
            'avg_power': 150.789,
            'avg_heart_rate': 140.567,
            'max_power': 200
        }
        
        self.workout_manager._calculate_summary_metrics()
        
        # Average values should be rounded
        assert self.workout_manager.summary_metrics['avg_power'] == 150.79
        assert self.workout_manager.summary_metrics['avg_heart_rate'] == 140.57
        assert self.workout_manager.summary_metrics['max_power'] == 200  # Not an average, not rounded


if __name__ == '__main__':
    pytest.main([__file__])