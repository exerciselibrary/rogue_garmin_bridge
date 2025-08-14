"""
Load testing for extended workout sessions.

Tests system performance with 2+ hour workout sessions, validates memory usage
and garbage collection efficiency, tests database performance with large datasets,
and monitors system resources during extended operations.
"""

import pytest
import asyncio
import time
import psutil
import gc
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch
import sqlite3
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tests.utils.mock_devices import MockFTMSDevice, MockFTMSManager, create_mock_workout_data
from tests.conftest import TestDataFactory

# Import system components
try:
    from data.database_manager import DatabaseManager
    from data.workout_manager import WorkoutManager
    from ftms.ftms_manager import FTMSDeviceManager
    from fit.fit_processor import FITProcessor
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


class SystemResourceMonitor:
    """Monitor system resources during testing."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.metrics = []
        self.monitor_thread = None
        self.monitor_interval = 1.0  # seconds
    
    def start_monitoring(self):
        """Start resource monitoring."""
        self.monitoring = True
        self.metrics = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
    
    def _monitor_loop(self):
        """Monitor system resources in a loop."""
        while self.monitoring:
            try:
                memory_info = self.process.memory_info()
                cpu_percent = self.process.cpu_percent()
                
                metric = {
                    'timestamp': datetime.now(),
                    'memory_rss': memory_info.rss,  # Resident Set Size
                    'memory_vms': memory_info.vms,  # Virtual Memory Size
                    'cpu_percent': cpu_percent,
                    'num_threads': self.process.num_threads(),
                    'num_fds': self.process.num_fds() if hasattr(self.process, 'num_fds') else 0
                }
                
                self.metrics.append(metric)
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                print(f"Error monitoring resources: {e}")
                break
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        if not self.metrics:
            return {}
        
        memory_rss_values = [m['memory_rss'] for m in self.metrics]
        memory_vms_values = [m['memory_vms'] for m in self.metrics]
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        thread_values = [m['num_threads'] for m in self.metrics]
        
        return {
            'duration_seconds': len(self.metrics) * self.monitor_interval,
            'memory_rss': {
                'min': min(memory_rss_values),
                'max': max(memory_rss_values),
                'avg': sum(memory_rss_values) / len(memory_rss_values),
                'final': memory_rss_values[-1],
                'growth': memory_rss_values[-1] - memory_rss_values[0]
            },
            'memory_vms': {
                'min': min(memory_vms_values),
                'max': max(memory_vms_values),
                'avg': sum(memory_vms_values) / len(memory_vms_values),
                'final': memory_vms_values[-1],
                'growth': memory_vms_values[-1] - memory_vms_values[0]
            },
            'cpu_percent': {
                'min': min(cpu_values),
                'max': max(cpu_values),
                'avg': sum(cpu_values) / len(cpu_values)
            },
            'num_threads': {
                'min': min(thread_values),
                'max': max(thread_values),
                'final': thread_values[-1]
            },
            'total_samples': len(self.metrics)
        }


class ExtendedWorkoutSimulator:
    """Simulate extended workout sessions for load testing."""
    
    def __init__(self, device_type: str = "bike", duration_hours: float = 2.0):
        self.device_type = device_type
        self.duration_seconds = int(duration_hours * 3600)
        self.data_frequency = 1.0  # 1 Hz
        self.device = MockFTMSDevice(device_type)
        self.data_points = []
        self.callbacks = []
    
    def register_callback(self, callback):
        """Register callback for data updates."""
        self.callbacks.append(callback)
    
    async def run_simulation(self):
        """Run extended workout simulation."""
        await self.device.connect()
        self.device.start_workout()
        
        start_time = datetime.now()
        
        for i in range(self.duration_seconds):
            # Generate realistic data point
            elapsed = i
            data_point = self._generate_data_point(start_time, elapsed)
            self.data_points.append(data_point)
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data_point)
                    else:
                        callback(data_point)
                except Exception as e:
                    print(f"Error in callback: {e}")
            
            # Control simulation speed (for testing, we don't wait full second)
            if i % 100 == 0:  # Every 100 data points, yield control
                await asyncio.sleep(0.001)
        
        self.device.stop_workout()
        await self.device.disconnect()
    
    def _generate_data_point(self, start_time: datetime, elapsed_seconds: int) -> Dict[str, Any]:
        """Generate a realistic data point."""
        timestamp = start_time + timedelta(seconds=elapsed_seconds)
        
        # Create workout phases for long session
        phase_duration = self.duration_seconds // 4
        if elapsed_seconds < phase_duration:
            phase = "warmup"
            intensity = 0.4
        elif elapsed_seconds < phase_duration * 3:
            phase = "main"
            intensity = 0.7 + 0.2 * (elapsed_seconds % 600) / 600  # Vary intensity
        else:
            phase = "cooldown"
            intensity = 0.3
        
        base_data = {
            "timestamp": timestamp,
            "phase": phase,
            "elapsed_seconds": elapsed_seconds
        }
        
        if self.device_type == "bike":
            base_data.update({
                "power": int(200 * intensity + (elapsed_seconds % 50) - 25),
                "cadence": int(85 * intensity + (elapsed_seconds % 20) - 10),
                "speed": 25.0 * intensity + (elapsed_seconds % 10) / 10 - 0.5,
                "heart_rate": int(150 + intensity * 40 + (elapsed_seconds % 30) - 15),
                "distance": elapsed_seconds * 0.007,  # Accumulating distance
                "calories": elapsed_seconds * 0.5
            })
        else:  # rower
            base_data.update({
                "power": int(220 * intensity + (elapsed_seconds % 60) - 30),
                "stroke_rate": int(24 * intensity + (elapsed_seconds % 8) - 4),
                "heart_rate": int(155 + intensity * 35 + (elapsed_seconds % 25) - 12),
                "distance": elapsed_seconds * 0.008,
                "calories": elapsed_seconds * 0.6,
                "stroke_count": elapsed_seconds // 2
            })
        
        return base_data


@pytest.fixture
def resource_monitor():
    """Provide system resource monitor."""
    monitor = SystemResourceMonitor()
    yield monitor
    monitor.stop_monitoring()


@pytest.fixture
def extended_workout_simulator():
    """Provide extended workout simulator."""
    return ExtendedWorkoutSimulator


@pytest.mark.slow
@pytest.mark.performance
class TestExtendedWorkoutSessions:
    """Test system performance with extended workout sessions."""
    
    async def test_2_hour_bike_workout_memory_usage(self, resource_monitor, extended_workout_simulator, test_database):
        """Test 2-hour bike workout for memory leaks and performance."""
        # Create simulator for 2-hour workout
        simulator = extended_workout_simulator("bike", duration_hours=2.0)
        
        # Create workout manager with database
        workout_manager = WorkoutManager(database=test_database)
        
        # Track data points received
        received_data_points = []
        
        def data_callback(data_point):
            received_data_points.append(data_point)
            # Simulate processing by workout manager
            workout_manager.process_data_point(data_point)
        
        simulator.register_callback(data_callback)
        
        # Start resource monitoring
        resource_monitor.start_monitoring()
        
        # Force garbage collection before test
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Run simulation
        start_time = time.time()
        await simulator.run_simulation()
        end_time = time.time()
        
        # Stop monitoring
        resource_monitor.stop_monitoring()
        
        # Force garbage collection after test
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Get resource metrics
        metrics = resource_monitor.get_metrics_summary()
        
        # Assertions for performance requirements
        assert len(received_data_points) == 7200, "Should receive 7200 data points (2 hours at 1Hz)"
        assert end_time - start_time < 60, "Simulation should complete within 60 seconds"
        
        # Memory leak detection
        memory_growth_mb = metrics['memory_rss']['growth'] / (1024 * 1024)
        assert memory_growth_mb < 100, f"Memory growth should be < 100MB, got {memory_growth_mb:.2f}MB"
        
        # Object leak detection
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Object count growth should be < 1000, got {object_growth}"
        
        # CPU usage should be reasonable
        assert metrics['cpu_percent']['avg'] < 50, f"Average CPU usage should be < 50%, got {metrics['cpu_percent']['avg']:.2f}%"
        
        print(f"Performance metrics for 2-hour bike workout:")
        print(f"  Memory growth: {memory_growth_mb:.2f} MB")
        print(f"  Object growth: {object_growth}")
        print(f"  Average CPU: {metrics['cpu_percent']['avg']:.2f}%")
        print(f"  Simulation time: {end_time - start_time:.2f} seconds")
    
    async def test_2_hour_rower_workout_memory_usage(self, resource_monitor, extended_workout_simulator, test_database):
        """Test 2-hour rower workout for memory leaks and performance."""
        simulator = extended_workout_simulator("rower", duration_hours=2.0)
        workout_manager = WorkoutManager(database=test_database)
        
        received_data_points = []
        
        def data_callback(data_point):
            received_data_points.append(data_point)
            workout_manager.process_data_point(data_point)
        
        simulator.register_callback(data_callback)
        
        resource_monitor.start_monitoring()
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        start_time = time.time()
        await simulator.run_simulation()
        end_time = time.time()
        
        resource_monitor.stop_monitoring()
        gc.collect()
        final_objects = len(gc.get_objects())
        
        metrics = resource_monitor.get_metrics_summary()
        
        # Assertions
        assert len(received_data_points) == 7200, "Should receive 7200 data points"
        
        memory_growth_mb = metrics['memory_rss']['growth'] / (1024 * 1024)
        assert memory_growth_mb < 100, f"Memory growth should be < 100MB, got {memory_growth_mb:.2f}MB"
        
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Object count growth should be < 1000, got {object_growth}"
        
        print(f"Performance metrics for 2-hour rower workout:")
        print(f"  Memory growth: {memory_growth_mb:.2f} MB")
        print(f"  Object growth: {object_growth}")
        print(f"  Average CPU: {metrics['cpu_percent']['avg']:.2f}%")
    
    async def test_database_performance_large_dataset(self, test_database, resource_monitor):
        """Test database performance with large datasets."""
        # Create a large workout with many data points
        workout_data = {
            "device_type": "bike",
            "start_time": datetime.now() - timedelta(hours=2),
            "duration": 7200  # 2 hours
        }
        
        resource_monitor.start_monitoring()
        
        # Create workout
        start_time = time.time()
        workout_id = test_database.create_workout(workout_data)
        
        # Insert 7200 data points (2 hours at 1Hz)
        data_points = create_mock_workout_data("bike", duration=7200)
        
        insert_start = time.time()
        for i, data_point in enumerate(data_points):
            test_database.add_data_point(workout_id, data_point)
            
            # Check performance every 1000 inserts
            if i > 0 and i % 1000 == 0:
                elapsed = time.time() - insert_start
                rate = i / elapsed
                assert rate > 100, f"Insert rate should be > 100/sec, got {rate:.2f}/sec at {i} inserts"
        
        insert_end = time.time()
        
        # Test query performance
        query_start = time.time()
        retrieved_data = test_database.get_workout_data_points(workout_id)
        query_end = time.time()
        
        # Test workout summary calculation
        summary_start = time.time()
        workout_summary = test_database.get_workout_summary(workout_id)
        summary_end = time.time()
        
        resource_monitor.stop_monitoring()
        metrics = resource_monitor.get_metrics_summary()
        
        # Performance assertions
        total_time = insert_end - start_time
        insert_rate = len(data_points) / (insert_end - insert_start)
        query_time = query_end - query_start
        summary_time = summary_end - summary_start
        
        assert total_time < 120, f"Total operation should complete in < 120s, got {total_time:.2f}s"
        assert insert_rate > 50, f"Insert rate should be > 50/sec, got {insert_rate:.2f}/sec"
        assert query_time < 5, f"Query time should be < 5s, got {query_time:.2f}s"
        assert summary_time < 2, f"Summary calculation should be < 2s, got {summary_time:.2f}s"
        assert len(retrieved_data) == 7200, "Should retrieve all 7200 data points"
        
        print(f"Database performance metrics:")
        print(f"  Insert rate: {insert_rate:.2f} points/sec")
        print(f"  Query time: {query_time:.2f} seconds")
        print(f"  Summary time: {summary_time:.2f} seconds")
        print(f"  Memory usage: {metrics['memory_rss']['max'] / (1024*1024):.2f} MB")
    
    async def test_concurrent_data_processing(self, resource_monitor, extended_workout_simulator, test_database):
        """Test concurrent data processing from multiple devices."""
        # Create multiple simulators
        bike_simulator = extended_workout_simulator("bike", duration_hours=1.0)
        rower_simulator = extended_workout_simulator("rower", duration_hours=1.0)
        
        # Create workout managers
        bike_workout_manager = WorkoutManager(database=test_database)
        rower_workout_manager = WorkoutManager(database=test_database)
        
        # Track data from both devices
        bike_data = []
        rower_data = []
        
        def bike_callback(data_point):
            bike_data.append(data_point)
            bike_workout_manager.process_data_point(data_point)
        
        def rower_callback(data_point):
            rower_data.append(data_point)
            rower_workout_manager.process_data_point(data_point)
        
        bike_simulator.register_callback(bike_callback)
        rower_simulator.register_callback(rower_callback)
        
        resource_monitor.start_monitoring()
        
        # Run both simulations concurrently
        start_time = time.time()
        await asyncio.gather(
            bike_simulator.run_simulation(),
            rower_simulator.run_simulation()
        )
        end_time = time.time()
        
        resource_monitor.stop_monitoring()
        metrics = resource_monitor.get_metrics_summary()
        
        # Assertions
        assert len(bike_data) == 3600, "Should receive 3600 bike data points"
        assert len(rower_data) == 3600, "Should receive 3600 rower data points"
        assert end_time - start_time < 60, "Concurrent simulation should complete within 60 seconds"
        
        # Memory and CPU should handle concurrent load
        memory_growth_mb = metrics['memory_rss']['growth'] / (1024 * 1024)
        assert memory_growth_mb < 150, f"Memory growth should be < 150MB for concurrent load, got {memory_growth_mb:.2f}MB"
        assert metrics['cpu_percent']['avg'] < 70, f"Average CPU should be < 70% for concurrent load, got {metrics['cpu_percent']['avg']:.2f}%"
        
        print(f"Concurrent processing metrics:")
        print(f"  Total data points: {len(bike_data) + len(rower_data)}")
        print(f"  Processing time: {end_time - start_time:.2f} seconds")
        print(f"  Memory growth: {memory_growth_mb:.2f} MB")
        print(f"  Average CPU: {metrics['cpu_percent']['avg']:.2f}%")
    
    async def test_garbage_collection_efficiency(self, extended_workout_simulator):
        """Test garbage collection efficiency during extended operations."""
        simulator = extended_workout_simulator("bike", duration_hours=1.0)
        
        # Track garbage collection stats
        gc_stats_before = gc.get_stats()
        gc.collect()
        
        # Track object counts by type
        initial_objects = {}
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            initial_objects[obj_type] = initial_objects.get(obj_type, 0) + 1
        
        # Run simulation with periodic GC monitoring
        gc_collections = []
        
        def data_callback(data_point):
            # Trigger GC every 1000 data points
            if data_point.get('elapsed_seconds', 0) % 1000 == 0:
                before_gc = len(gc.get_objects())
                collected = gc.collect()
                after_gc = len(gc.get_objects())
                
                gc_collections.append({
                    'timestamp': data_point['timestamp'],
                    'before_gc': before_gc,
                    'after_gc': after_gc,
                    'collected': collected,
                    'freed': before_gc - after_gc
                })
        
        simulator.register_callback(data_callback)
        
        await simulator.run_simulation()
        
        # Final garbage collection
        gc.collect()
        gc_stats_after = gc.get_stats()
        
        # Count final objects
        final_objects = {}
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            final_objects[obj_type] = final_objects.get(obj_type, 0) + 1
        
        # Analyze garbage collection efficiency
        total_freed = sum(gc['freed'] for gc in gc_collections)
        avg_freed_per_gc = total_freed / len(gc_collections) if gc_collections else 0
        
        # Check for object leaks by type
        object_growth = {}
        for obj_type in set(initial_objects.keys()) | set(final_objects.keys()):
            initial_count = initial_objects.get(obj_type, 0)
            final_count = final_objects.get(obj_type, 0)
            growth = final_count - initial_count
            if growth > 0:
                object_growth[obj_type] = growth
        
        # Assertions
        assert len(gc_collections) > 0, "Should have performed garbage collection during simulation"
        assert avg_freed_per_gc > 0, "Garbage collection should free objects"
        
        # Check for significant object leaks
        problematic_types = {obj_type: count for obj_type, count in object_growth.items() 
                           if count > 100 and obj_type not in ['dict', 'list', 'tuple']}
        
        assert len(problematic_types) == 0, f"Found potential object leaks: {problematic_types}"
        
        print(f"Garbage collection efficiency:")
        print(f"  GC cycles: {len(gc_collections)}")
        print(f"  Average freed per GC: {avg_freed_per_gc:.2f}")
        print(f"  Total objects freed: {total_freed}")
        if object_growth:
            print(f"  Object growth by type: {dict(list(object_growth.items())[:5])}")


@pytest.mark.slow
@pytest.mark.performance
class TestSystemResourceMonitoring:
    """Test system resource monitoring during extended operations."""
    
    def test_resource_monitor_accuracy(self, resource_monitor):
        """Test resource monitor accuracy and reliability."""
        resource_monitor.start_monitoring()
        
        # Perform some memory-intensive operations
        large_data = []
        for i in range(1000):
            large_data.append([j for j in range(1000)])
            time.sleep(0.01)
        
        time.sleep(2)  # Let monitor collect data
        resource_monitor.stop_monitoring()
        
        metrics = resource_monitor.get_metrics_summary()
        
        # Verify metrics were collected
        assert metrics['total_samples'] > 0, "Should collect resource samples"
        assert metrics['memory_rss']['max'] > metrics['memory_rss']['min'], "Memory usage should vary"
        assert metrics['duration_seconds'] > 1, "Should monitor for at least 1 second"
        
        # Memory should have increased during the test
        assert metrics['memory_rss']['growth'] > 0, "Memory should have grown during intensive operations"
        
        print(f"Resource monitor metrics:")
        print(f"  Samples collected: {metrics['total_samples']}")
        print(f"  Memory growth: {metrics['memory_rss']['growth'] / (1024*1024):.2f} MB")
        print(f"  Max CPU: {metrics['cpu_percent']['max']:.2f}%")
    
    async def test_fit_file_generation_performance(self, extended_workout_simulator, resource_monitor):
        """Test FIT file generation performance with large datasets."""
        simulator = extended_workout_simulator("bike", duration_hours=2.0)
        
        # Collect all data points
        all_data_points = []
        
        def data_callback(data_point):
            all_data_points.append(data_point)
        
        simulator.register_callback(data_callback)
        
        # Run simulation to collect data
        await simulator.run_simulation()
        
        # Test FIT file generation performance
        resource_monitor.start_monitoring()
        
        fit_processor = FITProcessor()
        
        generation_start = time.time()
        fit_data = fit_processor.create_fit_file(all_data_points, device_type="bike")
        generation_end = time.time()
        
        resource_monitor.stop_monitoring()
        metrics = resource_monitor.get_metrics_summary()
        
        generation_time = generation_end - generation_start
        data_points_per_second = len(all_data_points) / generation_time
        
        # Performance assertions
        assert generation_time < 30, f"FIT generation should complete in < 30s, got {generation_time:.2f}s"
        assert data_points_per_second > 100, f"Should process > 100 points/sec, got {data_points_per_second:.2f}/sec"
        assert len(fit_data) > 0, "Should generate non-empty FIT file"
        
        # Memory usage should be reasonable
        memory_peak_mb = metrics['memory_rss']['max'] / (1024 * 1024)
        assert memory_peak_mb < 200, f"Peak memory should be < 200MB, got {memory_peak_mb:.2f}MB"
        
        print(f"FIT file generation performance:")
        print(f"  Data points: {len(all_data_points)}")
        print(f"  Generation time: {generation_time:.2f} seconds")
        print(f"  Processing rate: {data_points_per_second:.2f} points/sec")
        print(f"  FIT file size: {len(fit_data)} bytes")
        print(f"  Peak memory: {memory_peak_mb:.2f} MB")


if __name__ == "__main__":
    # Run specific performance tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])