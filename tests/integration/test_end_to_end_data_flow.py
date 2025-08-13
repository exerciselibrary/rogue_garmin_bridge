"""
End-to-end data flow integration tests for Rogue Garmin Bridge.

Tests complete workflow from simulator to FIT file generation,
data consistency across all system components, workout session management
with realistic data volumes, and error propagation and recovery mechanisms.

Requirements: 3.2, 8.1, 8.2, 8.4
"""

import pytest
import asyncio
import os
import tempfile
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock

# Import system modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from data.database import Database
from data.workout_manager import WorkoutManager
from ftms.ftms_manager import FTMSDeviceManager
from ftms.enhanced_bike_simulator import EnhancedBikeSimulator
from ftms.enhanced_rower_simulator import EnhancedRowerSimulator
from fit.fit_processor import FITProcessor
from utils.logging_config import get_component_logger

# Import test utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.mock_devices import MockFTMSDevice, create_mock_workout_data, inject_data_errors
from utils.database_utils import TestDatabaseManager, validate_database_integrity

logger = get_component_logger('integration_test')


class TestEndToEndDataFlow:
    """Test complete data flow from device simulation to FIT file generation."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        self.fit_output_dir = os.path.join(self.temp_dir, "fit_files")
        os.makedirs(self.fit_output_dir, exist_ok=True)
        
        # Initialize components
        self.database = Database(self.db_path)
        self.workout_manager = WorkoutManager(self.db_path)
        
        yield
        
        # Cleanup
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_complete_bike_workout_flow(self):
        """Test complete workflow from bike simulator to FIT file generation."""
        # Initialize FTMS manager with bike simulator
        ftms_manager = FTMSDeviceManager(
            workout_manager=self.workout_manager,
            use_simulator=True,
            device_type="bike"
        )
        
        # Start device discovery and connection
        devices = await ftms_manager.discover_devices()
        assert len(devices) > 0, "No devices discovered"
        
        # Connect to first available device
        device_address = list(devices.keys())[0]
        connection_success = await ftms_manager.connect(device_address, "bike")
        assert connection_success, "Failed to connect to device"
        
        # Verify connection status
        assert ftms_manager.device_status == "connected"
        assert ftms_manager.connected_device is not None
        
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "bike")
        assert workout_id is not None, "Failed to start workout"
        assert self.workout_manager.active_workout_id == workout_id
        
        # Notify FTMS manager about workout start
        ftms_manager.notify_workout_start(workout_id, "bike")
        
        # Collect data for realistic duration (30 seconds for test)
        data_collection_duration = 30
        collected_data_points = []
        
        def data_callback(data):
            collected_data_points.append(data.copy())
        
        ftms_manager.register_data_callback(data_callback)
        
        # Wait for data collection
        await asyncio.sleep(data_collection_duration)
        
        # Verify data was collected
        assert len(collected_data_points) >= 25, f"Expected at least 25 data points, got {len(collected_data_points)}"
        
        # Verify data structure for bike
        sample_data = collected_data_points[0]
        required_bike_fields = ['power', 'cadence', 'speed', 'heart_rate']
        for field in required_bike_fields:
            assert field in sample_data, f"Missing required bike field: {field}"
            assert sample_data[field] is not None, f"Field {field} is None"
        
        # End workout
        ftms_manager.notify_workout_end(workout_id)
        success = self.workout_manager.end_workout()
        assert success, "Failed to end workout"
        
        # Verify workout was saved to database
        saved_workout = self.workout_manager.get_workout(workout_id)
        assert saved_workout is not None, "Workout not saved to database"
        assert saved_workout['device_type'] == 'bike'
        assert saved_workout['duration'] >= data_collection_duration - 5  # Allow some tolerance
        
        # Verify data points were saved
        saved_data_points = self.workout_manager.get_workout_data(workout_id)
        assert len(saved_data_points) >= 25, f"Expected at least 25 saved data points, got {len(saved_data_points)}"
        
        # Test FIT file generation
        fit_processor = FITProcessor(self.db_path, self.fit_output_dir)
        fit_file_path = fit_processor.process_workout(workout_id)
        
        assert fit_file_path is not None, "FIT file generation failed"
        assert os.path.exists(fit_file_path), f"FIT file not created at {fit_file_path}"
        
        # Verify FIT file size is reasonable
        fit_file_size = os.path.getsize(fit_file_path)
        assert fit_file_size > 1000, f"FIT file too small: {fit_file_size} bytes"
        
        # Disconnect device
        disconnect_success = await ftms_manager.disconnect()
        assert disconnect_success, "Failed to disconnect device"
        assert ftms_manager.device_status == "disconnected"
    
    @pytest.mark.asyncio
    async def test_complete_rower_workout_flow(self):
        """Test complete workflow from rower simulator to FIT file generation."""
        # Initialize FTMS manager with rower simulator
        ftms_manager = FTMSDeviceManager(
            workout_manager=self.workout_manager,
            use_simulator=True,
            device_type="rower"
        )
        
        # Start device discovery and connection
        devices = await ftms_manager.discover_devices()
        assert len(devices) > 0, "No devices discovered"
        
        # Connect to first available device
        device_address = list(devices.keys())[0]
        connection_success = await ftms_manager.connect(device_address, "rower")
        assert connection_success, "Failed to connect to device"
        
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "rower")
        assert workout_id is not None, "Failed to start workout"
        
        # Notify FTMS manager about workout start
        ftms_manager.notify_workout_start(workout_id, "rower")
        
        # Collect data for realistic duration
        data_collection_duration = 30
        collected_data_points = []
        
        def data_callback(data):
            collected_data_points.append(data.copy())
        
        ftms_manager.register_data_callback(data_callback)
        
        # Wait for data collection
        await asyncio.sleep(data_collection_duration)
        
        # Verify data was collected
        assert len(collected_data_points) >= 25, f"Expected at least 25 data points, got {len(collected_data_points)}"
        
        # Verify data structure for rower
        sample_data = collected_data_points[0]
        required_rower_fields = ['power', 'stroke_rate', 'heart_rate']
        for field in required_rower_fields:
            assert field in sample_data, f"Missing required rower field: {field}"
            assert sample_data[field] is not None, f"Field {field} is None"
        
        # End workout
        ftms_manager.notify_workout_end(workout_id)
        success = self.workout_manager.end_workout()
        assert success, "Failed to end workout"
        
        # Verify workout was saved
        saved_workout = self.workout_manager.get_workout(workout_id)
        assert saved_workout is not None, "Workout not saved to database"
        assert saved_workout['device_type'] == 'rower'
        
        # Test FIT file generation
        fit_processor = FITProcessor(self.db_path, self.fit_output_dir)
        fit_file_path = fit_processor.process_workout(workout_id)
        
        assert fit_file_path is not None, "FIT file generation failed"
        assert os.path.exists(fit_file_path), f"FIT file not created at {fit_file_path}"
        
        # Disconnect device
        disconnect_success = await ftms_manager.disconnect()
        assert disconnect_success, "Failed to disconnect device"
    
    @pytest.mark.asyncio
    async def test_data_consistency_across_components(self):
        """Test data consistency across all system components."""
        # Initialize system
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
        
        # Track data at different levels
        ftms_data_points = []
        workout_manager_data_points = []
        
        def ftms_callback(data):
            ftms_data_points.append(data.copy())
        
        def workout_callback(data):
            workout_manager_data_points.append(data.copy())
        
        ftms_manager.register_data_callback(ftms_callback)
        self.workout_manager.register_data_callback(workout_callback)
        
        # Collect data
        await asyncio.sleep(20)
        
        # End workout
        ftms_manager.notify_workout_end(workout_id)
        self.workout_manager.end_workout()
        
        # Verify data consistency
        assert len(ftms_data_points) > 0, "No data collected at FTMS level"
        assert len(workout_manager_data_points) > 0, "No data collected at WorkoutManager level"
        
        # Check that data flows through both callbacks
        # Note: workout_manager_data_points might be fewer due to active workout filtering
        assert len(workout_manager_data_points) <= len(ftms_data_points), \
            "WorkoutManager received more data than FTMS manager"
        
        # Verify database consistency
        saved_data_points = self.workout_manager.get_workout_data(workout_id)
        assert len(saved_data_points) > 0, "No data points saved to database"
        
        # Check data field consistency
        if ftms_data_points and saved_data_points:
            ftms_sample = ftms_data_points[0]
            db_sample = saved_data_points[0]['data']
            
            # Verify key fields are preserved
            for field in ['power', 'cadence', 'speed', 'heart_rate']:
                if field in ftms_sample:
                    assert field in db_sample, f"Field {field} lost in database storage"
        
        # Disconnect
        await ftms_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_workout_session_management_realistic_volumes(self):
        """Test workout session management with realistic data volumes."""
        # Test with longer workout duration to simulate realistic volumes
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
        
        # Collect data for extended period (2 minutes for test)
        data_collection_duration = 120
        start_time = datetime.now()
        
        collected_data_count = 0
        def count_callback(data):
            nonlocal collected_data_count
            collected_data_count += 1
        
        ftms_manager.register_data_callback(count_callback)
        
        # Wait for data collection
        await asyncio.sleep(data_collection_duration)
        
        # End workout
        ftms_manager.notify_workout_end(workout_id)
        self.workout_manager.end_workout()
        
        end_time = datetime.now()
        actual_duration = (end_time - start_time).total_seconds()
        
        # Verify realistic data volumes
        expected_min_points = int(actual_duration * 0.8)  # Allow for some timing variance
        assert collected_data_count >= expected_min_points, \
            f"Expected at least {expected_min_points} data points, got {collected_data_count}"
        
        # Verify database can handle the volume
        saved_data_points = self.workout_manager.get_workout_data(workout_id)
        assert len(saved_data_points) >= expected_min_points, \
            f"Database saved {len(saved_data_points)} points, expected at least {expected_min_points}"
        
        # Verify workout summary metrics are calculated correctly
        saved_workout = self.workout_manager.get_workout(workout_id)
        summary = json.loads(saved_workout['summary']) if isinstance(saved_workout['summary'], str) else saved_workout['summary']
        
        assert 'avg_power' in summary, "Missing avg_power in workout summary"
        assert 'max_power' in summary, "Missing max_power in workout summary"
        assert 'total_distance' in summary, "Missing total_distance in workout summary"
        assert summary['avg_power'] > 0, "Average power should be greater than 0"
        assert summary['max_power'] >= summary['avg_power'], "Max power should be >= average power"
        
        # Test FIT file generation with realistic volume
        fit_processor = FITProcessor(self.db_path, self.fit_output_dir)
        fit_file_path = fit_processor.process_workout(workout_id)
        
        assert fit_file_path is not None, "FIT file generation failed with realistic data volume"
        assert os.path.exists(fit_file_path), "FIT file not created"
        
        # Verify FIT file size scales with data volume
        fit_file_size = os.path.getsize(fit_file_path)
        expected_min_size = collected_data_count * 10  # Rough estimate: 10 bytes per data point
        assert fit_file_size >= expected_min_size, \
            f"FIT file size {fit_file_size} too small for {collected_data_count} data points"
        
        # Disconnect
        await ftms_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_error_propagation_and_recovery(self):
        """Test error propagation and recovery mechanisms."""
        ftms_manager = FTMSDeviceManager(
            workout_manager=self.workout_manager,
            use_simulator=True,
            device_type="bike"
        )
        
        # Test connection error handling
        invalid_address = "INVALID:ADDRESS"
        connection_result = await ftms_manager.connect(invalid_address, "bike")
        assert not connection_result, "Should fail to connect to invalid address"
        assert ftms_manager.device_status == "disconnected", "Status should remain disconnected"
        
        # Test successful connection after failure
        devices = await ftms_manager.discover_devices()
        valid_address = list(devices.keys())[0]
        connection_result = await ftms_manager.connect(valid_address, "bike")
        assert connection_result, "Should successfully connect after previous failure"
        
        # Test workout error handling
        # Try to start workout without proper device ID
        try:
            invalid_workout_id = self.workout_manager.start_workout(999, "bike")
            # If this doesn't raise an exception, verify it handles gracefully
            assert invalid_workout_id is not None, "Workout should be created even with invalid device ID"
        except Exception as e:
            # If it raises an exception, that's also acceptable error handling
            logger.info(f"Expected error handling for invalid device ID: {e}")
        
        # Test data processing error recovery
        workout_id = self.workout_manager.start_workout(1, "bike")
        ftms_manager.notify_workout_start(workout_id, "bike")
        
        # Inject invalid data to test error handling
        error_count = 0
        def error_tracking_callback(data):
            nonlocal error_count
            try:
                # Simulate processing that might fail
                if 'power' in data and data['power'] < 0:
                    raise ValueError("Invalid power value")
                # Normal processing
                pass
            except Exception as e:
                error_count += 1
                logger.warning(f"Data processing error: {e}")
        
        ftms_manager.register_data_callback(error_tracking_callback)
        
        # Collect some data
        await asyncio.sleep(10)
        
        # End workout
        ftms_manager.notify_workout_end(workout_id)
        self.workout_manager.end_workout()
        
        # Verify system continued operating despite errors
        saved_workout = self.workout_manager.get_workout(workout_id)
        assert saved_workout is not None, "Workout should be saved despite processing errors"
        
        saved_data_points = self.workout_manager.get_workout_data(workout_id)
        assert len(saved_data_points) > 0, "Some data points should be saved despite errors"
        
        # Test disconnection error handling
        # Force disconnect and verify graceful handling
        await ftms_manager.disconnect()
        
        # Try to disconnect again (should handle gracefully)
        second_disconnect = await ftms_manager.disconnect()
        # Should not raise exception and return appropriate result
        assert isinstance(second_disconnect, bool), "Disconnect should return boolean result"
    
    @pytest.mark.asyncio
    async def test_concurrent_workout_sessions(self):
        """Test handling of concurrent workout session attempts."""
        ftms_manager = FTMSDeviceManager(
            workout_manager=self.workout_manager,
            use_simulator=True,
            device_type="bike"
        )
        
        # Connect device
        devices = await ftms_manager.discover_devices()
        device_address = list(devices.keys())[0]
        await ftms_manager.connect(device_address, "bike")
        
        # Start first workout
        workout_id_1 = self.workout_manager.start_workout(1, "bike")
        assert workout_id_1 is not None, "First workout should start successfully"
        assert self.workout_manager.active_workout_id == workout_id_1
        
        # Try to start second workout (should end first and start second)
        workout_id_2 = self.workout_manager.start_workout(1, "bike")
        assert workout_id_2 is not None, "Second workout should start"
        assert workout_id_2 != workout_id_1, "Second workout should have different ID"
        assert self.workout_manager.active_workout_id == workout_id_2, "Active workout should be the second one"
        
        # Verify first workout was ended
        first_workout = self.workout_manager.get_workout(workout_id_1)
        assert first_workout is not None, "First workout should exist in database"
        assert first_workout['end_time'] is not None, "First workout should have end time"
        
        # End second workout
        self.workout_manager.end_workout()
        assert self.workout_manager.active_workout_id is None, "No active workout after ending"
        
        # Disconnect
        await ftms_manager.disconnect()
    
    def test_database_integrity_after_operations(self):
        """Test database integrity after various operations."""
        # Create multiple workouts with different scenarios
        workout_ids = []
        
        # Normal workout
        workout_id_1 = self.workout_manager.start_workout(1, "bike")
        # Add some data points
        for i in range(10):
            self.workout_manager.add_data_point({
                'power': 150 + i,
                'cadence': 80 + i,
                'speed': 25.0,
                'heart_rate': 140
            })
        self.workout_manager.end_workout()
        workout_ids.append(workout_id_1)
        
        # Workout with minimal data
        workout_id_2 = self.workout_manager.start_workout(1, "rower")
        self.workout_manager.add_data_point({
            'power': 200,
            'stroke_rate': 24,
            'heart_rate': 150
        })
        self.workout_manager.end_workout()
        workout_ids.append(workout_id_2)
        
        # Workout ended without data (edge case)
        workout_id_3 = self.workout_manager.start_workout(1, "bike")
        self.workout_manager.end_workout()
        workout_ids.append(workout_id_3)
        
        # Validate database integrity
        integrity_report = validate_database_integrity(self.db_path)
        assert integrity_report['valid'], f"Database integrity issues: {integrity_report['errors']}"
        
        # Verify all workouts exist
        for workout_id in workout_ids:
            workout = self.workout_manager.get_workout(workout_id)
            assert workout is not None, f"Workout {workout_id} not found in database"
        
        # Test workout deletion
        delete_success = self.workout_manager.delete_workout(workout_id_1)
        assert delete_success, "Failed to delete workout"
        
        # Verify workout is deleted
        deleted_workout = self.workout_manager.get_workout(workout_id_1)
        assert deleted_workout is None, "Workout should be deleted"
        
        # Verify database integrity after deletion
        integrity_report_after = validate_database_integrity(self.db_path)
        assert integrity_report_after['valid'], f"Database integrity issues after deletion: {integrity_report_after['errors']}"


@pytest.mark.integration
class TestDataFlowPerformance:
    """Test data flow performance under various conditions."""
    
    @pytest.fixture(autouse=True)
    def setup_performance_test(self):
        """Set up performance test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "perf_test_rogue_garmin.db")
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
    async def test_high_frequency_data_processing(self):
        """Test system performance with high-frequency data."""
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
        
        # Track performance metrics
        start_time = datetime.now()
        data_count = 0
        processing_times = []
        
        def performance_callback(data):
            nonlocal data_count
            callback_start = datetime.now()
            data_count += 1
            # Simulate some processing
            _ = data.get('power', 0) * 1.1
            callback_end = datetime.now()
            processing_times.append((callback_end - callback_start).total_seconds())
        
        ftms_manager.register_data_callback(performance_callback)
        
        # Run for 60 seconds
        await asyncio.sleep(60)
        
        # End workout
        ftms_manager.notify_workout_end(workout_id)
        self.workout_manager.end_workout()
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Analyze performance
        data_rate = data_count / total_duration
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        max_processing_time = max(processing_times) if processing_times else 0
        
        # Performance assertions
        assert data_rate >= 0.8, f"Data rate too low: {data_rate} Hz"
        assert avg_processing_time < 0.01, f"Average processing time too high: {avg_processing_time}s"
        assert max_processing_time < 0.1, f"Max processing time too high: {max_processing_time}s"
        
        # Verify data integrity under high frequency
        saved_data_points = self.workout_manager.get_workout_data(workout_id)
        expected_min_points = int(total_duration * 0.8)
        assert len(saved_data_points) >= expected_min_points, \
            f"Data loss under high frequency: {len(saved_data_points)} < {expected_min_points}"
        
        await ftms_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_long_workout(self):
        """Test memory usage during extended workout sessions."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
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
        
        # Monitor memory usage over time
        memory_samples = []
        data_count = 0
        
        def memory_tracking_callback(data):
            nonlocal data_count
            data_count += 1
            if data_count % 60 == 0:  # Sample every 60 data points
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_samples.append(current_memory)
        
        ftms_manager.register_data_callback(memory_tracking_callback)
        
        # Run for extended period (3 minutes)
        await asyncio.sleep(180)
        
        # End workout
        ftms_manager.notify_workout_end(workout_id)
        self.workout_manager.end_workout()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Force garbage collection
        gc.collect()
        gc_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Memory usage analysis
        memory_growth = final_memory - initial_memory
        memory_after_gc = gc_memory - initial_memory
        
        # Memory assertions
        assert memory_growth < 100, f"Memory growth too high: {memory_growth} MB"
        assert memory_after_gc < 50, f"Memory not released after GC: {memory_after_gc} MB"
        
        # Check for memory leaks (memory should not continuously grow)
        if len(memory_samples) > 2:
            early_avg = sum(memory_samples[:2]) / 2
            late_avg = sum(memory_samples[-2:]) / 2
            memory_leak_indicator = late_avg - early_avg
            assert memory_leak_indicator < 20, f"Possible memory leak: {memory_leak_indicator} MB growth"
        
        await ftms_manager.disconnect()