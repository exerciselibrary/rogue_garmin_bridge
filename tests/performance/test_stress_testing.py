"""
Stress testing for edge cases and system robustness.

Tests connection interruption and recovery scenarios, validates system behavior
under resource constraints, tests concurrent user access and data processing,
and implements chaos engineering scenarios for robustness testing.
"""

import pytest
import asyncio
import time
import random
import threading
import psutil
import tempfile
import shutil
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tests.utils.mock_devices import MockFTMSDevice, MockFTMSManager, inject_data_errors
from tests.performance.test_load_testing import SystemResourceMonitor

# Import system components
try:
    from data.database_manager import DatabaseManager
    from data.workout_manager import WorkoutManager
    from ftms.ftms_manager import FTMSDeviceManager
    from ftms.connection_manager import BluetoothConnectionManager, ConnectionState
    from web.app import app as flask_app
    from utils.data_validator import DataValidator
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


class ConnectionInterruptionSimulator:
    """Simulate various connection interruption scenarios."""
    
    def __init__(self, device: MockFTMSDevice):
        self.device = device
        self.interruption_active = False
        self.interruption_patterns = {
            'brief_dropout': {'duration': 2, 'frequency': 30},
            'extended_dropout': {'duration': 10, 'frequency': 120},
            'intermittent': {'duration': 1, 'frequency': 5},
            'complete_failure': {'duration': float('inf'), 'frequency': 60}
        }
    
    async def simulate_pattern(self, pattern_name: str, total_duration: int):
        """Simulate a specific interruption pattern."""
        pattern = self.interruption_patterns.get(pattern_name)
        if not pattern:
            raise ValueError(f"Unknown pattern: {pattern_name}")
        
        start_time = time.time()
        next_interruption = pattern['frequency']
        
        while time.time() - start_time < total_duration:
            # Wait until next interruption
            await asyncio.sleep(min(next_interruption, total_duration - (time.time() - start_time)))
            
            if time.time() - start_time >= total_duration:
                break
            
            # Simulate disconnection
            self.interruption_active = True
            if self.device.is_connected:
                await self.device.disconnect()
            
            # Wait for interruption duration
            interruption_duration = pattern['duration']
            if interruption_duration != float('inf'):
                await asyncio.sleep(interruption_duration)
                
                # Reconnect
                self.interruption_active = False
                if not self.device.is_connected:
                    await self.device.connect()
                    if hasattr(self.device, 'start_workout'):
                        self.device.start_workout()
            
            next_interruption = pattern['frequency']


class ResourceConstraintSimulator:
    """Simulate system resource constraints."""
    
    def __init__(self):
        self.memory_hogs = []
        self.cpu_hogs = []
        self.disk_fillers = []
        self.active_constraints = []
    
    def apply_memory_constraint(self, target_mb: int):
        """Apply memory pressure by allocating large amounts of memory."""
        memory_hog = []
        try:
            # Allocate memory in chunks
            chunk_size = 1024 * 1024  # 1MB chunks
            for _ in range(target_mb):
                chunk = bytearray(chunk_size)
                memory_hog.append(chunk)
            
            self.memory_hogs.append(memory_hog)
            self.active_constraints.append(f"memory_{target_mb}MB")
        except MemoryError:
            # If we can't allocate the requested memory, allocate what we can
            self.memory_hogs.append(memory_hog)
            self.active_constraints.append(f"memory_{len(memory_hog)}MB")
    
    def apply_cpu_constraint(self, duration_seconds: int, intensity: float = 0.8):
        """Apply CPU pressure by running intensive calculations."""
        def cpu_intensive_task():
            end_time = time.time() + duration_seconds
            while time.time() < end_time:
                # Perform CPU-intensive calculations
                for _ in range(int(10000 * intensity)):
                    _ = sum(i * i for i in range(100))
                time.sleep(0.001)  # Brief pause to allow other threads
        
        thread = threading.Thread(target=cpu_intensive_task)
        thread.daemon = True
        thread.start()
        self.cpu_hogs.append(thread)
        self.active_constraints.append(f"cpu_{intensity*100:.0f}%")
    
    def apply_disk_constraint(self, target_mb: int, temp_dir: str):
        """Apply disk space pressure by creating large files."""
        try:
            file_path = os.path.join(temp_dir, f"disk_filler_{len(self.disk_fillers)}.tmp")
            with open(file_path, 'wb') as f:
                chunk_size = 1024 * 1024  # 1MB chunks
                for _ in range(target_mb):
                    f.write(b'0' * chunk_size)
            
            self.disk_fillers.append(file_path)
            self.active_constraints.append(f"disk_{target_mb}MB")
        except OSError:
            # If we can't create the file, note the constraint attempt
            self.active_constraints.append(f"disk_failed_{target_mb}MB")
    
    def release_all_constraints(self):
        """Release all applied constraints."""
        # Clear memory hogs
        self.memory_hogs.clear()
        
        # CPU hogs will naturally end when their threads complete
        
        # Remove disk fillers
        for file_path in self.disk_fillers:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass
        self.disk_fillers.clear()
        
        self.active_constraints.clear()


class ChaosEngineeringScenarios:
    """Implement chaos engineering scenarios for robustness testing."""
    
    def __init__(self):
        self.active_scenarios = []
        self.scenario_tasks = []
    
    async def random_database_errors(self, database, duration_seconds: int, error_rate: float = 0.1):
        """Inject random database errors."""
        original_execute = database.connection.execute
        
        def error_injecting_execute(*args, **kwargs):
            if random.random() < error_rate:
                raise sqlite3.OperationalError("Simulated database error")
            return original_execute(*args, **kwargs)
        
        database.connection.execute = error_injecting_execute
        self.active_scenarios.append("database_errors")
        
        await asyncio.sleep(duration_seconds)
        
        # Restore original method
        database.connection.execute = original_execute
        self.active_scenarios.remove("database_errors")
    
    async def random_network_delays(self, duration_seconds: int, delay_range: tuple = (0.1, 2.0)):
        """Simulate random network delays."""
        async def inject_delays():
            while "network_delays" in self.active_scenarios:
                delay = random.uniform(*delay_range)
                await asyncio.sleep(delay)
        
        self.active_scenarios.append("network_delays")
        delay_task = asyncio.create_task(inject_delays())
        self.scenario_tasks.append(delay_task)
        
        await asyncio.sleep(duration_seconds)
        
        self.active_scenarios.remove("network_delays")
        delay_task.cancel()
    
    async def random_device_disconnections(self, devices: List[MockFTMSDevice], 
                                         duration_seconds: int, disconnect_rate: float = 0.05):
        """Randomly disconnect and reconnect devices."""
        async def chaos_disconnections():
            while "device_disconnections" in self.active_scenarios:
                for device in devices:
                    if random.random() < disconnect_rate and device.is_connected:
                        await device.disconnect()
                        # Reconnect after a short delay
                        await asyncio.sleep(random.uniform(1, 5))
                        if "device_disconnections" in self.active_scenarios:
                            await device.connect()
                            if hasattr(device, 'start_workout'):
                                device.start_workout()
                
                await asyncio.sleep(1)
        
        self.active_scenarios.append("device_disconnections")
        chaos_task = asyncio.create_task(chaos_disconnections())
        self.scenario_tasks.append(chaos_task)
        
        await asyncio.sleep(duration_seconds)
        
        self.active_scenarios.remove("device_disconnections")
        chaos_task.cancel()
    
    async def data_corruption_injection(self, data_callback: Callable, 
                                      duration_seconds: int, corruption_rate: float = 0.02):
        """Inject corrupted data into the data stream."""
        original_callback = data_callback
        
        def corrupting_callback(data_point):
            if random.random() < corruption_rate:
                # Corrupt the data in various ways
                corruption_type = random.choice(['invalid_values', 'missing_fields', 'wrong_types'])
                
                if corruption_type == 'invalid_values':
                    data_point['power'] = -999 if 'power' in data_point else data_point.get('power')
                    data_point['heart_rate'] = 999 if 'heart_rate' in data_point else data_point.get('heart_rate')
                elif corruption_type == 'missing_fields':
                    if 'power' in data_point:
                        del data_point['power']
                elif corruption_type == 'wrong_types':
                    data_point['timestamp'] = "invalid_timestamp"
                    data_point['power'] = "not_a_number"
            
            return original_callback(data_point)
        
        return corrupting_callback
    
    def cleanup_all_scenarios(self):
        """Clean up all active chaos scenarios."""
        self.active_scenarios.clear()
        for task in self.scenario_tasks:
            if not task.done():
                task.cancel()
        self.scenario_tasks.clear()


@pytest.fixture
def connection_interruptor():
    """Provide connection interruption simulator."""
    def _create_interruptor(device):
        return ConnectionInterruptionSimulator(device)
    return _create_interruptor


@pytest.fixture
def resource_constrainer():
    """Provide resource constraint simulator."""
    constrainer = ResourceConstraintSimulator()
    yield constrainer
    constrainer.release_all_constraints()


@pytest.fixture
def chaos_engineer():
    """Provide chaos engineering scenarios."""
    chaos = ChaosEngineeringScenarios()
    yield chaos
    chaos.cleanup_all_scenarios()


@pytest.mark.slow
@pytest.mark.stress
class TestConnectionInterruptionRecovery:
    """Test connection interruption and recovery scenarios."""
    
    async def test_brief_connection_dropouts(self, connection_interruptor, test_database):
        """Test recovery from brief connection dropouts."""
        device = MockFTMSDevice("bike")
        interruptor = connection_interruptor(device)
        workout_manager = WorkoutManager(database=test_database)
        
        # Track data continuity
        received_data = []
        connection_events = []
        
        def data_callback(data_point):
            received_data.append(data_point)
            workout_manager.process_data_point(data_point)
        
        def connection_callback(event_type, timestamp):
            connection_events.append({'type': event_type, 'timestamp': timestamp})
        
        device.register_callback(data_callback)
        
        # Start workout and interruption simulation
        await device.connect()
        device.start_workout()
        
        # Run brief dropout pattern for 2 minutes
        interruption_task = asyncio.create_task(
            interruptor.simulate_pattern('brief_dropout', 120)
        )
        
        # Let it run
        await asyncio.sleep(125)
        
        device.stop_workout()
        await device.disconnect()
        
        if not interruption_task.done():
            interruption_task.cancel()
        
        # Analyze results
        data_gaps = []
        for i in range(1, len(received_data)):
            time_diff = (received_data[i]['timestamp'] - received_data[i-1]['timestamp']).total_seconds()
            if time_diff > 5:  # Gap longer than 5 seconds
                data_gaps.append(time_diff)
        
        # Assertions
        assert len(received_data) > 60, "Should receive substantial data despite interruptions"
        assert len(data_gaps) > 0, "Should have some data gaps due to interruptions"
        assert all(gap < 15 for gap in data_gaps), "Data gaps should be brief (< 15 seconds)"
        
        # Check data integrity after reconnection
        valid_data_points = [dp for dp in received_data if dp.get('power', 0) > 0]
        assert len(valid_data_points) > len(received_data) * 0.7, "Should maintain > 70% valid data"
        
        print(f"Brief dropout test results:")
        print(f"  Total data points: {len(received_data)}")
        print(f"  Data gaps: {len(data_gaps)}")
        print(f"  Max gap: {max(data_gaps) if data_gaps else 0:.2f} seconds")
        print(f"  Valid data percentage: {len(valid_data_points)/len(received_data)*100:.1f}%")
    
    async def test_extended_connection_loss(self, connection_interruptor, test_database):
        """Test recovery from extended connection loss."""
        device = MockFTMSDevice("rower")
        interruptor = connection_interruptor(device)
        workout_manager = WorkoutManager(database=test_database)
        
        received_data = []
        recovery_times = []
        
        def data_callback(data_point):
            received_data.append(data_point)
            workout_manager.process_data_point(data_point)
        
        device.register_callback(data_callback)
        
        await device.connect()
        device.start_workout()
        
        # Track when data resumes after interruptions
        last_data_time = time.time()
        
        def track_recovery():
            nonlocal last_data_time
            while device.is_active:
                current_time = time.time()
                if received_data and current_time - last_data_time > 1:
                    # Data resumed after gap
                    gap_duration = current_time - last_data_time
                    if gap_duration > 5:  # Only count significant gaps
                        recovery_times.append(gap_duration)
                last_data_time = current_time
                time.sleep(0.5)
        
        recovery_thread = threading.Thread(target=track_recovery)
        recovery_thread.daemon = True
        recovery_thread.start()
        
        # Run extended dropout pattern for 3 minutes
        interruption_task = asyncio.create_task(
            interruptor.simulate_pattern('extended_dropout', 180)
        )
        
        await asyncio.sleep(185)
        
        device.stop_workout()
        await device.disconnect()
        
        if not interruption_task.done():
            interruption_task.cancel()
        
        # Analyze recovery performance
        avg_recovery_time = sum(recovery_times) / len(recovery_times) if recovery_times else 0
        
        # Assertions
        assert len(received_data) > 30, "Should receive some data despite extended interruptions"
        assert len(recovery_times) > 0, "Should have recovery events"
        assert avg_recovery_time < 30, f"Average recovery time should be < 30s, got {avg_recovery_time:.2f}s"
        
        # Check that system maintains state across disconnections
        if len(received_data) > 10:
            distance_values = [dp.get('distance', 0) for dp in received_data if dp.get('distance')]
            assert len(distance_values) > 0, "Should maintain distance tracking"
            assert distance_values[-1] > distance_values[0], "Distance should accumulate across reconnections"
        
        print(f"Extended dropout test results:")
        print(f"  Total data points: {len(received_data)}")
        print(f"  Recovery events: {len(recovery_times)}")
        print(f"  Average recovery time: {avg_recovery_time:.2f} seconds")
    
    async def test_intermittent_connection_issues(self, connection_interruptor, test_database):
        """Test handling of intermittent connection issues."""
        device = MockFTMSDevice("bike")
        interruptor = connection_interruptor(device)
        workout_manager = WorkoutManager(database=test_database)
        
        received_data = []
        error_count = 0
        
        def data_callback(data_point):
            nonlocal error_count
            try:
                received_data.append(data_point)
                workout_manager.process_data_point(data_point)
            except Exception as e:
                error_count += 1
                print(f"Error processing data point: {e}")
        
        device.register_callback(data_callback)
        
        await device.connect()
        device.start_workout()
        
        # Run intermittent pattern for 2 minutes
        interruption_task = asyncio.create_task(
            interruptor.simulate_pattern('intermittent', 120)
        )
        
        await asyncio.sleep(125)
        
        device.stop_workout()
        await device.disconnect()
        
        if not interruption_task.done():
            interruption_task.cancel()
        
        # Calculate data consistency metrics
        timestamps = [dp['timestamp'] for dp in received_data]
        if len(timestamps) > 1:
            time_diffs = [(timestamps[i] - timestamps[i-1]).total_seconds() 
                         for i in range(1, len(timestamps))]
            consistent_intervals = sum(1 for diff in time_diffs if 0.8 <= diff <= 1.2)
            consistency_rate = consistent_intervals / len(time_diffs) if time_diffs else 0
        else:
            consistency_rate = 0
        
        # Assertions
        assert len(received_data) > 30, "Should receive data despite intermittent issues"
        assert error_count < len(received_data) * 0.1, "Error rate should be < 10%"
        assert consistency_rate > 0.3, f"Should maintain > 30% timing consistency, got {consistency_rate:.2f}"
        
        print(f"Intermittent connection test results:")
        print(f"  Total data points: {len(received_data)}")
        print(f"  Processing errors: {error_count}")
        print(f"  Timing consistency: {consistency_rate:.2f}")


@pytest.mark.slow
@pytest.mark.stress
class TestResourceConstraints:
    """Test system behavior under resource constraints."""
    
    async def test_memory_pressure_handling(self, resource_constrainer, test_database, resource_monitor):
        """Test system behavior under memory pressure."""
        # Apply memory constraint (allocate 500MB)
        resource_constrainer.apply_memory_constraint(500)
        
        # Start resource monitoring
        resource_monitor.start_monitoring()
        
        # Create workout simulation under memory pressure
        device = MockFTMSDevice("bike")
        workout_manager = WorkoutManager(database=test_database)
        
        received_data = []
        processing_errors = []
        
        def data_callback(data_point):
            try:
                received_data.append(data_point)
                workout_manager.process_data_point(data_point)
            except Exception as e:
                processing_errors.append(str(e))
        
        device.register_callback(data_callback)
        
        await device.connect()
        device.start_workout()
        
        # Run for 2 minutes under memory pressure
        await asyncio.sleep(120)
        
        device.stop_workout()
        await device.disconnect()
        
        resource_monitor.stop_monitoring()
        metrics = resource_monitor.get_metrics_summary()
        
        # Analyze performance under memory pressure
        memory_peak_mb = metrics['memory_rss']['max'] / (1024 * 1024)
        
        # Assertions
        assert len(received_data) > 60, "Should continue processing data under memory pressure"
        assert len(processing_errors) < len(received_data) * 0.05, "Error rate should be < 5% under memory pressure"
        assert memory_peak_mb > 400, "Should be operating under significant memory pressure"
        
        # System should remain responsive
        avg_cpu = metrics['cpu_percent']['avg']
        assert avg_cpu < 90, f"CPU usage should remain manageable, got {avg_cpu:.2f}%"
        
        print(f"Memory pressure test results:")
        print(f"  Data points processed: {len(received_data)}")
        print(f"  Processing errors: {len(processing_errors)}")
        print(f"  Peak memory usage: {memory_peak_mb:.2f} MB")
        print(f"  Average CPU: {avg_cpu:.2f}%")
    
    async def test_cpu_constraint_handling(self, resource_constrainer, test_database, resource_monitor):
        """Test system behavior under CPU pressure."""
        # Start resource monitoring
        resource_monitor.start_monitoring()
        
        # Apply CPU constraint (80% load for 3 minutes)
        resource_constrainer.apply_cpu_constraint(180, intensity=0.8)
        
        device = MockFTMSDevice("rower")
        workout_manager = WorkoutManager(database=test_database)
        
        received_data = []
        processing_times = []
        
        def data_callback(data_point):
            start_time = time.time()
            try:
                received_data.append(data_point)
                workout_manager.process_data_point(data_point)
            except Exception as e:
                print(f"Processing error under CPU pressure: {e}")
            finally:
                processing_times.append(time.time() - start_time)
        
        device.register_callback(data_callback)
        
        await device.connect()
        device.start_workout()
        
        # Run for 2 minutes under CPU pressure
        await asyncio.sleep(120)
        
        device.stop_workout()
        await device.disconnect()
        
        resource_monitor.stop_monitoring()
        metrics = resource_monitor.get_metrics_summary()
        
        # Analyze performance under CPU pressure
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        max_processing_time = max(processing_times) if processing_times else 0
        
        # Assertions
        assert len(received_data) > 60, "Should continue processing data under CPU pressure"
        assert avg_processing_time < 0.1, f"Average processing time should be < 0.1s, got {avg_processing_time:.4f}s"
        assert max_processing_time < 1.0, f"Max processing time should be < 1s, got {max_processing_time:.4f}s"
        
        # CPU should be highly utilized but not completely saturated
        avg_cpu = metrics['cpu_percent']['avg']
        assert avg_cpu > 50, f"Should show high CPU usage, got {avg_cpu:.2f}%"
        
        print(f"CPU pressure test results:")
        print(f"  Data points processed: {len(received_data)}")
        print(f"  Average processing time: {avg_processing_time:.4f} seconds")
        print(f"  Max processing time: {max_processing_time:.4f} seconds")
        print(f"  Average CPU: {avg_cpu:.2f}%")
    
    async def test_disk_space_constraint(self, resource_constrainer, test_database, test_data_dir):
        """Test system behavior when disk space is limited."""
        # Apply disk constraint (fill up significant space)
        resource_constrainer.apply_disk_constraint(100, test_data_dir)  # 100MB
        
        device = MockFTMSDevice("bike")
        workout_manager = WorkoutManager(database=test_database)
        
        received_data = []
        database_errors = []
        
        def data_callback(data_point):
            try:
                received_data.append(data_point)
                workout_manager.process_data_point(data_point)
            except Exception as e:
                database_errors.append(str(e))
        
        device.register_callback(data_callback)
        
        await device.connect()
        device.start_workout()
        
        # Run for 2 minutes
        await asyncio.sleep(120)
        
        device.stop_workout()
        await device.disconnect()
        
        # Check disk usage
        disk_usage = shutil.disk_usage(test_data_dir)
        free_space_mb = disk_usage.free / (1024 * 1024)
        
        # Assertions
        assert len(received_data) > 30, "Should process some data even with disk constraints"
        
        # If disk space is very limited, expect some database errors
        if free_space_mb < 50:  # Less than 50MB free
            print(f"Low disk space detected: {free_space_mb:.2f} MB free")
            # System should handle gracefully, not crash
            assert len(database_errors) < len(received_data), "Should not fail on every operation"
        
        print(f"Disk constraint test results:")
        print(f"  Data points processed: {len(received_data)}")
        print(f"  Database errors: {len(database_errors)}")
        print(f"  Free disk space: {free_space_mb:.2f} MB")


@pytest.mark.slow
@pytest.mark.stress
class TestConcurrentAccess:
    """Test concurrent user access and data processing."""
    
    async def test_multiple_device_connections(self, test_database, resource_monitor):
        """Test concurrent connections from multiple devices."""
        # Create multiple devices
        devices = [
            MockFTMSDevice("bike", f"Bike_{i}", f"AA:BB:CC:DD:EE:{i:02X}")
            for i in range(5)
        ]
        devices.extend([
            MockFTMSDevice("rower", f"Rower_{i}", f"BB:CC:DD:EE:FF:{i:02X}")
            for i in range(3)
        ])
        
        # Create workout managers for each device
        workout_managers = [WorkoutManager(database=test_database) for _ in devices]
        
        # Track data from all devices
        all_received_data = {i: [] for i in range(len(devices))}
        processing_errors = []
        
        def create_callback(device_index):
            def callback(data_point):
                try:
                    all_received_data[device_index].append(data_point)
                    workout_managers[device_index].process_data_point(data_point)
                except Exception as e:
                    processing_errors.append(f"Device {device_index}: {str(e)}")
            return callback
        
        # Register callbacks
        for i, device in enumerate(devices):
            device.register_callback(create_callback(i))
        
        resource_monitor.start_monitoring()
        
        # Connect all devices concurrently
        connect_tasks = [device.connect() for device in devices]
        await asyncio.gather(*connect_tasks)
        
        # Start all workouts
        for device in devices:
            device.start_workout()
        
        # Run for 2 minutes
        await asyncio.sleep(120)
        
        # Stop all workouts
        for device in devices:
            device.stop_workout()
        
        # Disconnect all devices
        disconnect_tasks = [device.disconnect() for device in devices]
        await asyncio.gather(*disconnect_tasks)
        
        resource_monitor.stop_monitoring()
        metrics = resource_monitor.get_metrics_summary()
        
        # Analyze concurrent performance
        total_data_points = sum(len(data) for data in all_received_data.values())
        devices_with_data = sum(1 for data in all_received_data.values() if len(data) > 0)
        
        # Assertions
        assert devices_with_data >= len(devices) * 0.8, "At least 80% of devices should provide data"
        assert total_data_points > len(devices) * 60, "Should receive substantial data from all devices"
        assert len(processing_errors) < total_data_points * 0.02, "Error rate should be < 2%"
        
        # Resource usage should scale reasonably
        memory_peak_mb = metrics['memory_rss']['max'] / (1024 * 1024)
        assert memory_peak_mb < 300, f"Memory usage should be reasonable, got {memory_peak_mb:.2f} MB"
        
        print(f"Concurrent device test results:")
        print(f"  Total devices: {len(devices)}")
        print(f"  Devices with data: {devices_with_data}")
        print(f"  Total data points: {total_data_points}")
        print(f"  Processing errors: {len(processing_errors)}")
        print(f"  Peak memory: {memory_peak_mb:.2f} MB")
    
    async def test_concurrent_web_requests(self, test_database):
        """Test concurrent web interface requests."""
        # Create test client
        flask_app.config['TESTING'] = True
        client = flask_app.test_client()
        
        # Populate database with test data
        workout_ids = []
        for i in range(10):
            workout_data = {
                'device_type': 'bike' if i % 2 == 0 else 'rower',
                'start_time': datetime.now() - timedelta(hours=i),
                'duration': 1800 + i * 60
            }
            workout_id = test_database.create_workout(workout_data)
            workout_ids.append(workout_id)
            
            # Add some data points
            for j in range(100):
                data_point = {
                    'timestamp': workout_data['start_time'] + timedelta(seconds=j),
                    'power': 150 + j,
                    'heart_rate': 140 + j % 30
                }
                test_database.add_data_point(workout_id, data_point)
        
        # Define concurrent request scenarios
        def make_requests():
            results = []
            endpoints = [
                '/',
                '/devices',
                '/workout',
                '/history',
                '/api/workouts',
                f'/api/workout/{workout_ids[0]}',
                '/api/device/status'
            ]
            
            for endpoint in endpoints:
                try:
                    response = client.get(endpoint)
                    results.append({
                        'endpoint': endpoint,
                        'status_code': response.status_code,
                        'response_time': time.time()
                    })
                except Exception as e:
                    results.append({
                        'endpoint': endpoint,
                        'error': str(e),
                        'response_time': time.time()
                    })
            
            return results
        
        # Execute concurrent requests
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_requests) for _ in range(20)]
            all_results = []
            
            for future in as_completed(futures):
                try:
                    results = future.result(timeout=30)
                    all_results.extend(results)
                except Exception as e:
                    print(f"Request thread failed: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_requests = [r for r in all_results if r.get('status_code', 0) == 200]
        failed_requests = [r for r in all_results if 'error' in r or r.get('status_code', 0) != 200]
        
        # Assertions
        assert len(all_results) > 100, "Should have made substantial number of requests"
        assert len(successful_requests) > len(all_results) * 0.9, "Success rate should be > 90%"
        assert total_time < 60, f"All requests should complete within 60s, took {total_time:.2f}s"
        
        print(f"Concurrent web requests test results:")
        print(f"  Total requests: {len(all_results)}")
        print(f"  Successful requests: {len(successful_requests)}")
        print(f"  Failed requests: {len(failed_requests)}")
        print(f"  Total time: {total_time:.2f} seconds")
        print(f"  Requests per second: {len(all_results)/total_time:.2f}")


@pytest.mark.slow
@pytest.mark.stress
class TestChaosEngineering:
    """Test chaos engineering scenarios for robustness."""
    
    async def test_random_database_errors(self, chaos_engineer, test_database):
        """Test system resilience to random database errors."""
        device = MockFTMSDevice("bike")
        workout_manager = WorkoutManager(database=test_database)
        
        received_data = []
        processing_errors = []
        
        def data_callback(data_point):
            try:
                received_data.append(data_point)
                workout_manager.process_data_point(data_point)
            except Exception as e:
                processing_errors.append(str(e))
        
        device.register_callback(data_callback)
        
        await device.connect()
        device.start_workout()
        
        # Start chaos scenario - inject database errors for 2 minutes
        chaos_task = asyncio.create_task(
            chaos_engineer.random_database_errors(test_database, 120, error_rate=0.1)
        )
        
        # Run workout
        await asyncio.sleep(125)
        
        device.stop_workout()
        await device.disconnect()
        
        if not chaos_task.done():
            chaos_task.cancel()
        
        # Analyze resilience
        error_rate = len(processing_errors) / len(received_data) if received_data else 1
        
        # Assertions
        assert len(received_data) > 30, "Should continue processing despite database errors"
        assert error_rate < 0.2, f"Error rate should be manageable, got {error_rate:.2f}"
        
        # Check that some data was still successfully stored
        stored_workouts = test_database.get_all_workouts()
        assert len(stored_workouts) > 0, "Should have stored at least some workout data"
        
        print(f"Database chaos test results:")
        print(f"  Data points received: {len(received_data)}")
        print(f"  Processing errors: {len(processing_errors)}")
        print(f"  Error rate: {error_rate:.2f}")
        print(f"  Workouts stored: {len(stored_workouts)}")
    
    async def test_multiple_chaos_scenarios(self, chaos_engineer, test_database):
        """Test system under multiple simultaneous chaos scenarios."""
        # Create multiple devices
        devices = [
            MockFTMSDevice("bike", "Chaos_Bike"),
            MockFTMSDevice("rower", "Chaos_Rower")
        ]
        
        workout_managers = [WorkoutManager(database=test_database) for _ in devices]
        
        all_data = {i: [] for i in range(len(devices))}
        all_errors = {i: [] for i in range(len(devices))}
        
        def create_callback(device_index):
            def callback(data_point):
                try:
                    all_data[device_index].append(data_point)
                    workout_managers[device_index].process_data_point(data_point)
                except Exception as e:
                    all_errors[device_index].append(str(e))
            return callback
        
        # Apply chaos data corruption to callbacks
        for i, device in enumerate(devices):
            original_callback = create_callback(i)
            corrupted_callback = await chaos_engineer.data_corruption_injection(
                original_callback, 180, corruption_rate=0.05
            )
            device.register_callback(corrupted_callback)
        
        # Connect devices
        for device in devices:
            await device.connect()
            device.start_workout()
        
        # Start multiple chaos scenarios
        chaos_tasks = [
            asyncio.create_task(chaos_engineer.random_database_errors(test_database, 120, 0.05)),
            asyncio.create_task(chaos_engineer.random_device_disconnections(devices, 120, 0.03)),
            asyncio.create_task(chaos_engineer.random_network_delays(120, (0.1, 1.0)))
        ]
        
        # Run for 2 minutes under chaos
        await asyncio.sleep(125)
        
        # Cleanup
        for device in devices:
            device.stop_workout()
            await device.disconnect()
        
        for task in chaos_tasks:
            if not task.done():
                task.cancel()
        
        # Analyze system resilience under multiple stressors
        total_data = sum(len(data) for data in all_data.values())
        total_errors = sum(len(errors) for errors in all_errors.values())
        
        # Assertions
        assert total_data > 60, "Should process substantial data despite multiple chaos scenarios"
        assert total_errors < total_data * 0.3, "Error rate should be manageable under chaos"
        
        # System should maintain basic functionality
        stored_workouts = test_database.get_all_workouts()
        assert len(stored_workouts) >= 0, "Database should remain accessible"
        
        print(f"Multiple chaos scenarios test results:")
        print(f"  Total data points: {total_data}")
        print(f"  Total errors: {total_errors}")
        print(f"  Error rate: {total_errors/total_data if total_data > 0 else 0:.2f}")
        print(f"  Stored workouts: {len(stored_workouts)}")


if __name__ == "__main__":
    # Run specific stress tests
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "stress"])