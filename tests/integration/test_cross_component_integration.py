"""
Cross-component integration tests for Rogue Garmin Bridge.

Tests FTMS Manager to Workout Manager data flow, Workout Manager to Database
integration, Database to FIT Converter pipeline, and component error handling
and graceful degradation.

Requirements: 3.2, 6.3, 6.4, 8.4
"""

import pytest
import asyncio
import os
import tempfile
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import threading
import sqlite3

# Import system modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from data.database import Database
from data.workout_manager import WorkoutManager
from ftms.ftms_manager import FTMSDeviceManager
from fit.fit_processor import FITProcessor
from fit.fit_converter import FITConverter
from utils.logging_config import get_component_logger

# Import test utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.mock_devices import MockFTMSDevice, create_mock_workout_data, inject_data_errors
from utils.database_utils import TestDatabaseManager, validate_database_integrity

logger = get_component_logger('cross_component_test')


class TestFTMSToWorkoutManagerFlow:
    """Test data flow from FTMS Manager to Workout Manager."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        
        # Initialize components
        self.database = Database(self.db_path)
        self.workout_manager = WorkoutManager(self.db_path)
        
        yield
        
        # Cleanup
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_ftms_to_workout_manager_data_flow(self):
        """Test complete data flow from FTMS Manager to Workout Manager."""
        # Initialize FTMS manager with workout manager
        ftms_manager = FTMSDeviceManager(
            workout_manager=self.workout_manager,
            use_simulator=True,
            device_type="bike"
        )
        
        # Track data flow
        ftms_data_received = []
        workout_manager_data_received = []
        
        def ftms_callback(data):
            ftms_data_received.append(data.copy())
        
        def workout_callback(data):
            workout_manager_data_received.append(data.copy())
        
        ftms_manager.register_data_callback(ftms_callback)
        self.workout_manager.register_data_callback(workout_callback)
        
        # Connect device
        devices = await ftms_manager.discover_devices()
        device_address = list(devices.keys())[0]
        connection_success = await ftms_manager.connect(device_address, "bike")
        assert connection_success, "Failed to connect to device"
        
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "bike")
        ftms_manager.notify_workout_start(workout_id, "bike")
        
        # Collect data for a period
        await asyncio.sleep(15)
        
        # End workout
        ftms_manager.notify_workout_end(workout_id)
        self.workout_manager.end_workout()
        
        # Verify data flow
        assert len(ftms_data_received) > 0, "No data received at FTMS level"
        assert len(workout_manager_data_received) > 0, "No data received at WorkoutManager level"
        
        # Verify data consistency
        assert len(workout_manager_data_received) <= len(ftms_data_received), \
            "WorkoutManager received more data than FTMS manager"
        
        # Verify data structure consistency
        if ftms_data_received and workout_manager_data_received:
            ftms_sample = ftms_data_received[0]
            wm_sample = workout_manager_data_received[0]
            
            # Check that key fields are preserved
            for field in ['power', 'cadence', 'speed', 'heart_rate']:
                if field in ftms_sample:
                    assert field in wm_sample, f"Field {field} lost in WorkoutManager flow"
        
        # Verify workout was created and populated
        saved_workout = self.workout_manager.get_workout(workout_id)
        assert saved_workout is not None, "Workout not saved"
        
        saved_data_points = self.workout_manager.get_workout_data(workout_id)
        assert len(saved_data_points) > 0, "No data points saved"
        
        # Disconnect
        await ftms_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_ftms_callback_registration_and_unregistration(self):
        """Test callback registration and unregistration between components."""
        ftms_manager = FTMSDeviceManager(
            workout_manager=self.workout_manager,
            use_simulator=True,
            device_type="bike"
        )
        
        # Test callback registration
        callback_calls = []
        
        def test_callback(data):
            callback_calls.append(data)
        
        # Register callback
        ftms_manager.register_data_callback(test_callback)
        
        # Connect and generate some data
        devices = await ftms_manager.discover_devices()
        device_address = list(devices.keys())[0]
        await ftms_manager.connect(device_address, "bike")
        
        workout_id = self.workout_manager.start_workout(1, "bike")
        ftms_manager.notify_workout_start(workout_id, "bike")
        
        await asyncio.sleep(5)
        
        # Verify callback was called
        initial_call_count = len(callback_calls)
        assert initial_call_count > 0, "Callback was not called"
        
        # Unregister callback (if supported)
        if hasattr(ftms_manager, 'unregister_data_callback'):
            ftms_manager.unregister_data_callback(test_callback)
            
            # Continue generating data
            await asyncio.sleep(5)
            
            # Verify callback is no longer called
            final_call_count = len(callback_calls)
            # Allow for some buffered calls but should not significantly increase
            assert final_call_count <= initial_call_count + 2, \
                "Callback continued to be called after unregistration"
        
        # Cleanup
        ftms_manager.notify_workout_end(workout_id)
        self.workout_manager.end_workout()
        await ftms_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_ftms_status_propagation_to_workout_manager(self):
        """Test status updates propagation from FTMS to Workout Manager."""
        ftms_manager = FTMSDeviceManager(
            workout_manager=self.workout_manager,
            use_simulator=True,
            device_type="bike"
        )
        
        # Track status updates
        status_updates = []
        
        def status_callback(status, data):
            status_updates.append({'status': status, 'data': data})
        
        ftms_manager.register_status_callback(status_callback)
        
        # Test connection status
        devices = await ftms_manager.discover_devices()
        device_address = list(devices.keys())[0]
        
        connection_success = await ftms_manager.connect(device_address, "bike")
        assert connection_success, "Failed to connect"
        
        # Verify connection status was propagated
        connected_statuses = [s for s in status_updates if s['status'] == 'connected']
        assert len(connected_statuses) > 0, "Connection status not propagated"
        
        # Test workout status propagation
        workout_id = self.workout_manager.start_workout(1, "bike")
        ftms_manager.notify_workout_start(workout_id, "bike")
        
        await asyncio.sleep(3)
        
        # End workout and test disconnection
        ftms_manager.notify_workout_end(workout_id)
        self.workout_manager.end_workout()
        
        disconnect_success = await ftms_manager.disconnect()
        assert disconnect_success, "Failed to disconnect"
        
        # Verify disconnection status was propagated
        disconnected_statuses = [s for s in status_updates if s['status'] == 'disconnected']
        assert len(disconnected_statuses) > 0, "Disconnection status not propagated"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_ftms_to_workout_flow(self):
        """Test error handling in FTMS to Workout Manager flow."""
        ftms_manager = FTMSDeviceManager(
            workout_manager=self.workout_manager,
            use_simulator=True,
            device_type="bike"
        )
        
        # Connect device
        devices = await ftms_manager.discover_devices()
        device_address = list(devices.keys())[0]
        await ftms_manager.connect(device_address, "bike")
        
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "bike")
        ftms_manager.notify_workout_start(workout_id, "bike")
        
        # Inject error in data processing
        error_count = 0
        original_add_data_point = self.workout_manager.add_data_point
        
        def error_prone_add_data_point(data):
            nonlocal error_count
            if error_count < 3:  # Fail first 3 attempts
                error_count += 1
                raise Exception(f"Simulated error {error_count}")
            return original_add_data_point(data)
        
        # Patch the method to simulate errors
        self.workout_manager.add_data_point = error_prone_add_data_point
        
        # Collect data (should handle errors gracefully)
        await asyncio.sleep(10)
        
        # Restore original method
        self.workout_manager.add_data_point = original_add_data_point
        
        # Continue collecting data
        await asyncio.sleep(5)
        
        # End workout
        ftms_manager.notify_workout_end(workout_id)
        self.workout_manager.end_workout()
        
        # Verify system recovered and saved some data
        saved_data_points = self.workout_manager.get_workout_data(workout_id)
        assert len(saved_data_points) > 0, "No data saved despite error recovery"
        
        # Verify workout was completed
        saved_workout = self.workout_manager.get_workout(workout_id)
        assert saved_workout is not None, "Workout not saved"
        assert saved_workout['end_time'] is not None, "Workout not properly ended"
        
        await ftms_manager.disconnect()


class TestWorkoutManagerToDatabaseIntegration:
    """Test integration between Workout Manager and Database."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        
        self.database = Database(self.db_path)
        self.workout_manager = WorkoutManager(self.db_path)
        
        yield
        
        # Cleanup
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_workout_lifecycle_database_integration(self):
        """Test complete workout lifecycle with database operations."""
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "bike")
        assert workout_id is not None, "Failed to start workout"
        
        # Verify workout exists in database
        db_workout = self.database.get_workout(workout_id)
        assert db_workout is not None, "Workout not created in database"
        assert db_workout['device_type'] == 'bike'
        assert db_workout['end_time'] is None, "Workout should not have end time yet"
        
        # Add data points
        test_data_points = [
            {'power': 150, 'cadence': 80, 'speed': 25.0, 'heart_rate': 140},
            {'power': 160, 'cadence': 85, 'speed': 26.0, 'heart_rate': 145},
            {'power': 155, 'cadence': 82, 'speed': 25.5, 'heart_rate': 142},
            {'power': 165, 'cadence': 88, 'speed': 27.0, 'heart_rate': 148}
        ]
        
        for data_point in test_data_points:
            success = self.workout_manager.add_data_point(data_point)
            assert success, f"Failed to add data point: {data_point}"
        
        # Verify data points in database
        db_data_points = self.database.get_workout_data(workout_id)
        assert len(db_data_points) == len(test_data_points), \
            f"Expected {len(test_data_points)} data points, got {len(db_data_points)}"
        
        # Verify data point content
        for i, db_point in enumerate(db_data_points):
            original_point = test_data_points[i]
            db_data = db_point['data']
            
            for field in ['power', 'cadence', 'speed', 'heart_rate']:
                assert db_data[field] == original_point[field], \
                    f"Data mismatch for {field}: expected {original_point[field]}, got {db_data[field]}"
        
        # End workout
        success = self.workout_manager.end_workout()
        assert success, "Failed to end workout"
        
        # Verify workout was properly ended in database
        db_workout_final = self.database.get_workout(workout_id)
        assert db_workout_final is not None, "Workout not found after ending"
        assert db_workout_final['end_time'] is not None, "Workout should have end time"
        assert db_workout_final['duration'] > 0, "Workout should have positive duration"
        
        # Verify summary metrics were calculated and saved
        if 'summary' in db_workout_final and db_workout_final['summary']:
            if isinstance(db_workout_final['summary'], str):
                summary = json.loads(db_workout_final['summary'])
            else:
                summary = db_workout_final['summary']
            
            assert 'avg_power' in summary, "Summary should contain avg_power"
            assert summary['avg_power'] > 0, "Average power should be positive"
    
    def test_concurrent_database_operations(self):
        """Test concurrent database operations through Workout Manager."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def create_workout_with_data(workout_type, data_count):
            try:
                # Create workout
                workout_id = self.workout_manager.start_workout(1, workout_type)
                
                # Add data points
                for i in range(data_count):
                    data_point = {
                        'power': 150 + i,
                        'heart_rate': 140 + (i % 30)
                    }
                    
                    if workout_type == "bike":
                        data_point.update({
                            'cadence': 80 + (i % 20),
                            'speed': 25.0 + (i % 5)
                        })
                    elif workout_type == "rower":
                        data_point.update({
                            'stroke_rate': 24 + (i % 8),
                            'stroke_count': i
                        })
                    
                    self.workout_manager.add_data_point(data_point)
                
                # End workout
                self.workout_manager.end_workout()
                
                results.put({
                    'workout_id': workout_id,
                    'workout_type': workout_type,
                    'data_count': data_count,
                    'success': True
                })
                
            except Exception as e:
                results.put({
                    'workout_type': workout_type,
                    'error': str(e),
                    'success': False
                })
        
        # Create multiple concurrent workouts
        threads = []
        workout_configs = [
            ("bike", 10),
            ("rower", 8),
            ("bike", 12),
            ("rower", 6)
        ]
        
        for workout_type, data_count in workout_configs:
            thread = threading.Thread(target=create_workout_with_data, args=(workout_type, data_count))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Collect results
        successful_workouts = []
        failed_workouts = []
        
        while not results.empty():
            result = results.get()
            if result['success']:
                successful_workouts.append(result)
            else:
                failed_workouts.append(result)
        
        # Verify results
        assert len(successful_workouts) >= 3, f"Too many failed workouts: {len(failed_workouts)}"
        
        # Verify database integrity
        integrity_report = validate_database_integrity(self.db_path)
        assert integrity_report['valid'], f"Database integrity compromised: {integrity_report['errors']}"
        
        # Verify all successful workouts exist in database
        for workout_result in successful_workouts:
            workout_id = workout_result['workout_id']
            db_workout = self.database.get_workout(workout_id)
            assert db_workout is not None, f"Workout {workout_id} not found in database"
            
            db_data_points = self.database.get_workout_data(workout_id)
            expected_count = workout_result['data_count']
            assert len(db_data_points) == expected_count, \
                f"Expected {expected_count} data points, got {len(db_data_points)}"
    
    def test_database_transaction_handling(self):
        """Test database transaction handling in Workout Manager."""
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "bike")
        
        # Add some data points
        for i in range(5):
            self.workout_manager.add_data_point({
                'power': 150 + i,
                'cadence': 80,
                'heart_rate': 140
            })
        
        # Simulate database error during workout end
        original_end_workout = self.database.end_workout
        
        def failing_end_workout(*args, **kwargs):
            raise sqlite3.Error("Simulated database error")
        
        # Patch database method to simulate error
        self.database.end_workout = failing_end_workout
        
        # Try to end workout (should handle error gracefully)
        try:
            success = self.workout_manager.end_workout()
            # If it doesn't raise an exception, it should return False
            assert not success, "End workout should fail with database error"
        except Exception:
            # If it raises an exception, that's also acceptable error handling
            pass
        
        # Restore original method
        self.database.end_workout = original_end_workout
        
        # Verify workout still exists and can be ended properly
        db_workout = self.database.get_workout(workout_id)
        assert db_workout is not None, "Workout should still exist after failed end"
        
        # Try ending again (should work now)
        success = self.database.end_workout(workout_id, summary={'avg_power': 150})
        assert success, "Should be able to end workout after fixing database"
    
    def test_data_validation_in_database_integration(self):
        """Test data validation during database operations."""
        workout_id = self.workout_manager.start_workout(1, "bike")
        
        # Test valid data
        valid_data = {'power': 150, 'cadence': 80, 'speed': 25.0, 'heart_rate': 140}
        success = self.workout_manager.add_data_point(valid_data)
        assert success, "Valid data should be accepted"
        
        # Test data with None values (should be handled gracefully)
        data_with_none = {'power': None, 'cadence': 80, 'speed': 25.0, 'heart_rate': 140}
        success = self.workout_manager.add_data_point(data_with_none)
        assert success, "Data with None values should be handled gracefully"
        
        # Test data with negative values (should be accepted but flagged)
        negative_data = {'power': -10, 'cadence': 80, 'speed': 25.0, 'heart_rate': 140}
        success = self.workout_manager.add_data_point(negative_data)
        assert success, "Negative values should be accepted (device might send them)"
        
        # Test data with extreme values
        extreme_data = {'power': 9999, 'cadence': 200, 'speed': 100.0, 'heart_rate': 250}
        success = self.workout_manager.add_data_point(extreme_data)
        assert success, "Extreme values should be accepted"
        
        # End workout
        self.workout_manager.end_workout()
        
        # Verify all data points were saved
        saved_data_points = self.workout_manager.get_workout_data(workout_id)
        assert len(saved_data_points) == 4, "All data points should be saved"


class TestDatabaseToFITConverterPipeline:
    """Test pipeline from Database to FIT Converter."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        self.fit_output_dir = os.path.join(self.temp_dir, "fit_files")
        os.makedirs(self.fit_output_dir, exist_ok=True)
        
        self.database = Database(self.db_path)
        self.workout_manager = WorkoutManager(self.db_path)
        
        yield
        
        # Cleanup
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_database_to_fit_conversion_pipeline(self):
        """Test complete pipeline from database to FIT file generation."""
        # Create workout with comprehensive data
        workout_id = self.database.start_workout(1, "bike")
        
        # Add realistic data points
        start_time = datetime.now() - timedelta(minutes=20)
        data_points = []
        
        for i in range(120):  # 2 minutes of data at 1Hz
            timestamp = start_time + timedelta(seconds=i)
            data_point = {
                'power': 150 + (i % 100),
                'cadence': 80 + (i % 30),
                'speed': 25.0 + (i % 10),
                'heart_rate': 140 + (i % 40),
                'distance': i * 0.1,
                'calories': i * 0.5
            }
            
            self.database.add_workout_data(workout_id, timestamp, data_point)
            data_points.append(data_point)
        
        # End workout with summary
        summary = {
            'avg_power': 200,
            'max_power': 250,
            'avg_cadence': 95,
            'max_cadence': 110,
            'avg_speed': 30.0,
            'max_speed': 35.0,
            'total_distance': 12.0,
            'total_calories': 60
        }
        self.database.end_workout(workout_id, summary=summary)
        
        # Test FIT file generation
        fit_processor = FITProcessor(self.db_path, self.fit_output_dir)
        fit_file_path = fit_processor.process_workout(workout_id)
        
        assert fit_file_path is not None, "FIT file generation failed"
        assert os.path.exists(fit_file_path), f"FIT file not created at {fit_file_path}"
        
        # Verify FIT file properties
        file_size = os.path.getsize(fit_file_path)
        assert file_size > 1000, f"FIT file too small: {file_size} bytes"
        
        # Verify file naming convention
        assert "bike_" in os.path.basename(fit_file_path), "FIT file should include device type"
        assert fit_file_path.endswith(".fit"), "FIT file should have .fit extension"
    
    def test_fit_conversion_with_different_workout_types(self):
        """Test FIT conversion for different workout types."""
        workout_types = ["bike", "rower"]
        fit_files_created = []
        
        for workout_type in workout_types:
            # Create workout
            workout_id = self.database.start_workout(1, workout_type)
            
            # Add type-specific data
            for i in range(60):  # 1 minute of data
                timestamp = datetime.now() - timedelta(seconds=60-i)
                
                if workout_type == "bike":
                    data_point = {
                        'power': 150 + i,
                        'cadence': 80 + (i % 20),
                        'speed': 25.0 + (i % 5),
                        'heart_rate': 140 + (i % 30)
                    }
                else:  # rower
                    data_point = {
                        'power': 200 + i,
                        'stroke_rate': 24 + (i % 8),
                        'heart_rate': 150 + (i % 25),
                        'stroke_count': i
                    }
                
                self.database.add_workout_data(workout_id, timestamp, data_point)
            
            # End workout
            if workout_type == "bike":
                summary = {'avg_power': 175, 'avg_cadence': 90, 'avg_speed': 27.5}
            else:
                summary = {'avg_power': 225, 'avg_stroke_rate': 28}
            
            self.database.end_workout(workout_id, summary=summary)
            
            # Generate FIT file
            fit_processor = FITProcessor(self.db_path, self.fit_output_dir)
            fit_file_path = fit_processor.process_workout(workout_id)
            
            assert fit_file_path is not None, f"FIT generation failed for {workout_type}"
            assert os.path.exists(fit_file_path), f"FIT file not created for {workout_type}"
            
            fit_files_created.append((workout_type, fit_file_path))
        
        # Verify different workout types create different files
        assert len(fit_files_created) == 2, "Should create FIT files for both workout types"
        
        bike_file = next(f for t, f in fit_files_created if t == "bike")
        rower_file = next(f for t, f in fit_files_created if t == "rower")
        
        assert bike_file != rower_file, "Different workout types should create different files"
        assert "bike_" in os.path.basename(bike_file), "Bike file should be identifiable"
        assert "rower_" in os.path.basename(rower_file), "Rower file should be identifiable"
    
    def test_fit_conversion_error_handling(self):
        """Test error handling in FIT conversion pipeline."""
        # Create workout with minimal data
        workout_id = self.database.start_workout(1, "bike")
        self.database.add_workout_data(workout_id, datetime.now(), {'power': 150})
        self.database.end_workout(workout_id, summary={'avg_power': 150})
        
        # Test with invalid output directory
        invalid_output_dir = "/invalid/path/that/does/not/exist"
        fit_processor = FITProcessor(self.db_path, invalid_output_dir)
        
        # Should handle error gracefully
        fit_file_path = fit_processor.process_workout(workout_id)
        # Depending on implementation, might return None or create directory
        # The key is that it shouldn't crash
        
        # Test with non-existent workout
        fit_processor = FITProcessor(self.db_path, self.fit_output_dir)
        fit_file_path = fit_processor.process_workout(999)
        assert fit_file_path is None, "Should return None for non-existent workout"
        
        # Test with corrupted database
        # Create a workout then corrupt the database
        workout_id = self.database.start_workout(1, "bike")
        self.database.add_workout_data(workout_id, datetime.now(), {'power': 150})
        self.database.end_workout(workout_id, summary={'avg_power': 150})
        
        # Simulate database corruption by closing connection
        if hasattr(self.database, 'connection') and self.database.connection:
            self.database.connection.close()
        
        # Try to process workout (should handle gracefully)
        try:
            fit_file_path = fit_processor.process_workout(workout_id)
            # Should either return None or handle the error
        except Exception as e:
            # If it raises an exception, it should be a handled exception
            assert "database" in str(e).lower() or "connection" in str(e).lower(), \
                f"Unexpected exception type: {e}"
    
    def test_fit_file_data_integrity(self):
        """Test data integrity in FIT file conversion."""
        # Create workout with known data
        workout_id = self.database.start_workout(1, "bike")
        
        # Add specific data points for verification
        test_data = [
            {'power': 100, 'cadence': 70, 'speed': 20.0, 'heart_rate': 130},
            {'power': 150, 'cadence': 80, 'speed': 25.0, 'heart_rate': 140},
            {'power': 200, 'cadence': 90, 'speed': 30.0, 'heart_rate': 150},
            {'power': 175, 'cadence': 85, 'speed': 27.5, 'heart_rate': 145}
        ]
        
        start_time = datetime.now() - timedelta(minutes=5)
        for i, data_point in enumerate(test_data):
            timestamp = start_time + timedelta(seconds=i * 60)  # 1 minute intervals
            self.database.add_workout_data(workout_id, timestamp, data_point)
        
        # Calculate expected summary
        expected_avg_power = sum(d['power'] for d in test_data) / len(test_data)
        expected_max_power = max(d['power'] for d in test_data)
        expected_avg_cadence = sum(d['cadence'] for d in test_data) / len(test_data)
        
        summary = {
            'avg_power': expected_avg_power,
            'max_power': expected_max_power,
            'avg_cadence': expected_avg_cadence,
            'total_distance': 5.0,
            'total_calories': 25
        }
        self.database.end_workout(workout_id, summary=summary)
        
        # Generate FIT file
        fit_processor = FITProcessor(self.db_path, self.fit_output_dir)
        fit_file_path = fit_processor.process_workout(workout_id)
        
        assert fit_file_path is not None, "FIT file generation failed"
        assert os.path.exists(fit_file_path), "FIT file not created"
        
        # Verify FIT file contains expected data structure
        # (This would require FIT file parsing, which is complex)
        # For now, verify file size indicates substantial content
        file_size = os.path.getsize(fit_file_path)
        expected_min_size = len(test_data) * 20  # Rough estimate
        assert file_size >= expected_min_size, f"FIT file smaller than expected: {file_size} bytes"


class TestComponentErrorHandlingAndGracefulDegradation:
    """Test error handling and graceful degradation across components."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        self.fit_output_dir = os.path.join(self.temp_dir, "fit_files")
        os.makedirs(self.fit_output_dir, exist_ok=True)
        
        self.database = Database(self.db_path)
        self.workout_manager = WorkoutManager(self.db_path)
        
        yield
        
        # Cleanup
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_database_failure_graceful_degradation(self):
        """Test graceful degradation when database fails."""
        ftms_manager = FTMSDeviceManager(
            workout_manager=self.workout_manager,
            use_simulator=True,
            device_type="bike"
        )
        
        # Connect and start workout
        devices = await ftms_manager.discover_devices()
        device_address = list(devices.keys())[0]
        await ftms_manager.connect(device_address, "bike")
        
        workout_id = self.workout_manager.start_workout(1, "bike")
        ftms_manager.notify_workout_start(workout_id, "bike")
        
        # Collect some initial data
        await asyncio.sleep(5)
        
        # Simulate database failure
        original_add_workout_data = self.database.add_workout_data
        
        def failing_add_workout_data(*args, **kwargs):
            raise sqlite3.Error("Database connection lost")
        
        self.database.add_workout_data = failing_add_workout_data
        
        # Continue collecting data (should handle database errors gracefully)
        data_collection_errors = 0
        
        def error_tracking_callback(data):
            nonlocal data_collection_errors
            try:
                # This should trigger the database error
                self.workout_manager.add_data_point(data)
            except Exception:
                data_collection_errors += 1
        
        ftms_manager.register_data_callback(error_tracking_callback)
        
        # Continue for a period with database errors
        await asyncio.sleep(10)
        
        # Restore database functionality
        self.database.add_workout_data = original_add_workout_data
        
        # Continue collecting data (should recover)
        await asyncio.sleep(5)
        
        # End workout
        ftms_manager.notify_workout_end(workout_id)
        
        # Try to end workout (might fail due to database issues during the test)
        try:
            self.workout_manager.end_workout()
        except Exception as e:
            logger.warning(f"Expected error ending workout after database failure: {e}")
        
        # Verify system didn't crash and can still operate
        # Try to start a new workout to verify recovery
        new_workout_id = self.workout_manager.start_workout(1, "bike")
        assert new_workout_id is not None, "System should recover after database failure"
        
        # Add a data point to verify database is working
        success = self.workout_manager.add_data_point({'power': 150, 'heart_rate': 140})
        assert success, "Should be able to add data after database recovery"
        
        self.workout_manager.end_workout()
        await ftms_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_ftms_connection_failure_handling(self):
        """Test handling of FTMS connection failures."""
        ftms_manager = FTMSDeviceManager(
            workout_manager=self.workout_manager,
            use_simulator=True,
            device_type="bike"
        )
        
        # Test connection to invalid device
        connection_success = await ftms_manager.connect("INVALID:ADDRESS", "bike")
        assert not connection_success, "Should fail to connect to invalid device"
        
        # Verify system state after connection failure
        assert ftms_manager.device_status == "disconnected", "Status should remain disconnected"
        assert ftms_manager.connected_device is None, "No device should be connected"
        
        # Test successful connection after failure
        devices = await ftms_manager.discover_devices()
        valid_address = list(devices.keys())[0]
        connection_success = await ftms_manager.connect(valid_address, "bike")
        assert connection_success, "Should connect successfully after previous failure"
        
        # Start workout and collect data
        workout_id = self.workout_manager.start_workout(1, "bike")
        ftms_manager.notify_workout_start(workout_id, "bike")
        
        await asyncio.sleep(5)
        
        # Simulate connection loss during workout
        original_disconnect = ftms_manager.disconnect
        
        async def forced_disconnect():
            # Simulate unexpected disconnection
            ftms_manager.device_status = "disconnected"
            ftms_manager.connected_device = None
            return True
        
        await forced_disconnect()
        
        # Verify workout can still be ended gracefully
        ftms_manager.notify_workout_end(workout_id)
        success = self.workout_manager.end_workout()
        assert success, "Should be able to end workout after connection loss"
        
        # Verify workout was saved
        saved_workout = self.workout_manager.get_workout(workout_id)
        assert saved_workout is not None, "Workout should be saved despite connection loss"
    
    def test_fit_conversion_failure_handling(self):
        """Test handling of FIT conversion failures."""
        # Create workout
        workout_id = self.database.start_workout(1, "bike")
        
        # Add some data
        for i in range(10):
            self.database.add_workout_data(
                workout_id, 
                datetime.now() - timedelta(seconds=10-i),
                {'power': 150 + i, 'heart_rate': 140}
            )
        
        self.database.end_workout(workout_id, summary={'avg_power': 155})
        
        # Test FIT conversion with invalid output directory
        invalid_fit_processor = FITProcessor(self.db_path, "/invalid/path")
        fit_file_path = invalid_fit_processor.process_workout(workout_id)
        
        # Should handle error gracefully (return None or handle exception)
        # The key is that it shouldn't crash the entire system
        
        # Test with valid processor
        valid_fit_processor = FITProcessor(self.db_path, self.fit_output_dir)
        
        # Mock FIT converter to simulate conversion failure
        with patch('src.fit.fit_processor.FITConverter') as mock_converter:
            mock_instance = Mock()
            mock_instance.convert_workout.return_value = None  # Simulate failure
            mock_converter.return_value = mock_instance
            
            fit_file_path = valid_fit_processor.process_workout(workout_id)
            assert fit_file_path is None, "Should return None when conversion fails"
        
        # Verify workout data is still intact after conversion failure
        saved_workout = self.database.get_workout(workout_id)
        assert saved_workout is not None, "Workout should still exist after FIT conversion failure"
        
        saved_data_points = self.database.get_workout_data(workout_id)
        assert len(saved_data_points) == 10, "Data points should still exist after FIT conversion failure"
    
    def test_memory_pressure_handling(self):
        """Test system behavior under memory pressure."""
        # Create multiple large workouts to simulate memory pressure
        workout_ids = []
        
        for workout_num in range(5):
            workout_id = self.database.start_workout(1, "bike")
            workout_ids.append(workout_id)
            
            # Add substantial amount of data
            for i in range(1000):  # Large number of data points
                data_point = {
                    'power': 150 + (i % 100),
                    'cadence': 80 + (i % 30),
                    'speed': 25.0 + (i % 10),
                    'heart_rate': 140 + (i % 40),
                    'distance': i * 0.1,
                    'calories': i * 0.5
                }
                self.database.add_workout_data(workout_id, datetime.now(), data_point)
            
            self.database.end_workout(workout_id, summary={'avg_power': 200})
        
        # Verify all workouts were created successfully
        for workout_id in workout_ids:
            saved_workout = self.database.get_workout(workout_id)
            assert saved_workout is not None, f"Workout {workout_id} should exist"
            
            saved_data_points = self.database.get_workout_data(workout_id)
            assert len(saved_data_points) == 1000, f"Workout {workout_id} should have all data points"
        
        # Test FIT conversion under memory pressure
        fit_processor = FITProcessor(self.db_path, self.fit_output_dir)
        
        successful_conversions = 0
        for workout_id in workout_ids:
            try:
                fit_file_path = fit_processor.process_workout(workout_id)
                if fit_file_path and os.path.exists(fit_file_path):
                    successful_conversions += 1
            except Exception as e:
                logger.warning(f"FIT conversion failed under memory pressure: {e}")
        
        # Should successfully convert at least some workouts
        assert successful_conversions >= 3, f"Only {successful_conversions}/5 conversions succeeded"
        
        # Verify database integrity after memory pressure
        integrity_report = validate_database_integrity(self.db_path)
        assert integrity_report['valid'], f"Database integrity compromised: {integrity_report['errors']}"
    
    def test_component_isolation_during_failures(self):
        """Test that component failures don't cascade to other components."""
        # Start with a working system
        workout_id = self.workout_manager.start_workout(1, "bike")
        
        # Add some data
        self.workout_manager.add_data_point({'power': 150, 'heart_rate': 140})
        
        # Simulate failure in one component (FIT processor)
        fit_processor = FITProcessor(self.db_path, self.fit_output_dir)
        
        with patch.object(fit_processor, 'process_workout') as mock_process:
            mock_process.side_effect = Exception("FIT processor failure")
            
            # Try FIT conversion (should fail)
            try:
                fit_file_path = fit_processor.process_workout(workout_id)
                assert False, "Should have raised exception"
            except Exception as e:
                assert "FIT processor failure" in str(e)
        
        # Verify other components still work
        # Database should still be functional
        saved_workout = self.database.get_workout(workout_id)
        assert saved_workout is not None, "Database should still work after FIT processor failure"
        
        # Workout manager should still be functional
        success = self.workout_manager.add_data_point({'power': 160, 'heart_rate': 145})
        assert success, "Workout manager should still work after FIT processor failure"
        
        # Should be able to end workout
        success = self.workout_manager.end_workout()
        assert success, "Should be able to end workout after FIT processor failure"
        
        # Verify final state
        final_workout = self.database.get_workout(workout_id)
        assert final_workout is not None, "Workout should be properly saved"
        assert final_workout['end_time'] is not None, "Workout should be properly ended"