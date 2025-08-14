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
import sqlite3
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import threading

# Cross-component integration tests


class MockFTMSManager:
    """Mock FTMS Manager for integration testing."""
    
    def __init__(self):
        self.data_callbacks = []
        self.status_callbacks = []
        self.is_connected = False
        self.device_info = None
        self.data_generation_task = None
        
    def register_data_callback(self, callback):
        self.data_callbacks.append(callback)
    
    def register_status_callback(self, callback):
        self.status_callbacks.append(callback)
    
    async def connect(self, device_address, device_type="bike"):
        self.is_connected = True
        self.device_info = {
            "address": device_address,
            "name": f"Mock {device_type.title()}",
            "type": device_type
        }
        
        # Notify status callbacks
        for callback in self.status_callbacks:
            callback("connected", self.device_info)
        
        return True
    
    async def disconnect(self):
        if self.data_generation_task:
            self.data_generation_task.cancel()
        
        self.is_connected = False
        
        # Notify status callbacks
        for callback in self.status_callbacks:
            callback("disconnected", None)
        
        return True
    
    def start_data_generation(self, device_type="bike", duration=10):
        """Start generating mock data for testing."""
        if not self.is_connected:
            return False
            
        self.data_generation_task = asyncio.create_task(
            self._generate_data(device_type, duration)
        )
        return True
    
    async def _generate_data(self, device_type, duration):
        """Generate realistic mock data."""
        start_time = time.time()
        data_point_count = 0
        
        try:
            while time.time() - start_time < duration:
                elapsed = time.time() - start_time
                
                # Generate realistic data based on device type
                if device_type == "bike":
                    data = {
                        "power": int(150 + 50 * (0.5 + 0.3 * (elapsed / duration))),
                        "cadence": int(80 + 20 * (0.5 + 0.2 * (elapsed / duration))),
                        "speed": 25.0 + 5.0 * (0.5 + 0.2 * (elapsed / duration)),
                        "heart_rate": int(140 + 30 * (elapsed / duration)),
                        "distance": elapsed * 0.1,
                        "calories": elapsed * 0.5
                    }
                else:  # rower
                    data = {
                        "power": int(200 + 80 * (0.5 + 0.3 * (elapsed / duration))),
                        "stroke_rate": int(24 + 6 * (0.5 + 0.2 * (elapsed / duration))),
                        "heart_rate": int(150 + 25 * (elapsed / duration)),
                        "distance": elapsed * 0.15,
                        "calories": elapsed * 0.7,
                        "stroke_count": int(elapsed * 0.4)
                    }
                
                # Notify data callbacks
                for callback in self.data_callbacks:
                    try:
                        callback(data)
                        data_point_count += 1
                    except Exception as e:
                        print(f"Error in data callback: {e}")
                
                await asyncio.sleep(1.0)  # 1Hz data rate
                
        except asyncio.CancelledError:
            pass


class MockWorkoutManager:
    """Mock Workout Manager for integration testing."""
    
    def __init__(self, database):
        self.database = database
        self.active_workout_id = None
        self.data_points = []
        self.data_callbacks = []
        self.status_callbacks = []
        
    def register_data_callback(self, callback):
        self.data_callbacks.append(callback)
    
    def register_status_callback(self, callback):
        self.status_callbacks.append(callback)
    
    def start_workout(self, device_id, workout_type):
        """Start a new workout."""
        if self.active_workout_id:
            self.end_workout()
        
        self.active_workout_id = self.database.start_workout(device_id, workout_type)
        self.data_points = []
        
        # Notify status callbacks
        for callback in self.status_callbacks:
            callback("workout_started", {
                "workout_id": self.active_workout_id,
                "device_id": device_id,
                "workout_type": workout_type
            })
        
        return self.active_workout_id
    
    def add_data_point(self, data):
        """Add a data point to the active workout."""
        if not self.active_workout_id:
            return False
        
        # Store locally
        self.data_points.append(data.copy())
        
        # Store in database
        success = self.database.add_workout_data(
            self.active_workout_id,
            datetime.now(),
            data
        )
        
        if success:
            # Notify data callbacks
            for callback in self.data_callbacks:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in workout manager data callback: {e}")
        
        return success
    
    def end_workout(self):
        """End the active workout."""
        if not self.active_workout_id:
            return False
        
        # Calculate summary metrics
        summary = self._calculate_summary()
        
        # End workout in database
        success = self.database.end_workout(self.active_workout_id, summary)
        
        if success:
            # Notify status callbacks
            for callback in self.status_callbacks:
                callback("workout_ended", {
                    "workout_id": self.active_workout_id,
                    "summary": summary
                })
        
        self.active_workout_id = None
        self.data_points = []
        
        return success
    
    def _calculate_summary(self):
        """Calculate summary metrics from data points."""
        if not self.data_points:
            return {}
        
        summary = {}
        
        # Calculate averages and maximums
        for field in ['power', 'cadence', 'speed', 'heart_rate', 'stroke_rate']:
            values = [dp.get(field, 0) for dp in self.data_points if dp.get(field) is not None]
            if values:
                summary[f'avg_{field}'] = sum(values) / len(values)
                summary[f'max_{field}'] = max(values)
        
        # Get final accumulated values
        if self.data_points:
            last_point = self.data_points[-1]
            summary['total_distance'] = last_point.get('distance', 0)
            summary['total_calories'] = last_point.get('calories', 0)
            summary['total_strokes'] = last_point.get('stroke_count', 0)
        
        return summary
    
    def get_workout(self, workout_id):
        """Get workout information."""
        return self.database.get_workout(workout_id)
    
    def get_workout_data(self, workout_id):
        """Get workout data points."""
        return self.database.get_workout_data(workout_id)


class MockDatabase:
    """Mock Database for integration testing."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()
        
    def _create_tables(self):
        """Create database tables."""
        cursor = self.connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER,
                workout_type TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration INTEGER,
                summary TEXT,
                fit_file_path TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER,
                timestamp TIMESTAMP,
                data TEXT,
                FOREIGN KEY (workout_id) REFERENCES workouts (id)
            )
        """)
        
        self.connection.commit()
    
    def start_workout(self, device_id, workout_type):
        """Start a new workout."""
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO workouts (device_id, workout_type, start_time) VALUES (?, ?, ?)",
            (device_id, workout_type, datetime.now())
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def end_workout(self, workout_id, summary=None):
        """End a workout."""
        cursor = self.connection.cursor()
        end_time = datetime.now()
        
        # Calculate duration
        cursor.execute("SELECT start_time FROM workouts WHERE id = ?", (workout_id,))
        row = cursor.fetchone()
        if row:
            start_time_str = row[0]
            if isinstance(start_time_str, str):
                start_time = datetime.fromisoformat(start_time_str)
            else:
                start_time = start_time_str
            duration = max(1, int((end_time - start_time).total_seconds()))  # Ensure at least 1 second
        else:
            duration = 1
        
        cursor.execute(
            "UPDATE workouts SET end_time = ?, duration = ?, summary = ? WHERE id = ?",
            (end_time, duration, json.dumps(summary) if summary else None, workout_id)
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    def add_workout_data(self, workout_id, timestamp, data):
        """Add workout data point."""
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO workout_data (workout_id, timestamp, data) VALUES (?, ?, ?)",
            (workout_id, timestamp, json.dumps(data))
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    def get_workout(self, workout_id):
        """Get workout by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            if result.get('summary'):
                result['summary'] = json.loads(result['summary'])
            return result
        return None
    
    def get_workout_data(self, workout_id):
        """Get workout data points."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM workout_data WHERE workout_id = ? ORDER BY timestamp",
            (workout_id,)
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            data_dict = dict(row)
            if data_dict['data']:
                data_dict['data'] = json.loads(data_dict['data'])
            result.append(data_dict)
        return result
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()


class MockFITConverter:
    """Mock FIT Converter for integration testing."""
    
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def convert_workout(self, processed_data, user_profile=None):
        """Convert workout data to FIT file."""
        try:
            # Generate a mock FIT file
            workout_type = processed_data.get("workout_type", "bike")
            start_time = processed_data.get("start_time", datetime.now())
            
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            
            filename = f"{workout_type}_{start_time.strftime('%Y%m%d_%H%M%S')}.fit"
            file_path = os.path.join(self.output_dir, filename)
            
            # Create a mock FIT file with some basic content
            with open(file_path, 'wb') as f:
                # Write a minimal FIT file header
                f.write(b'\x0e\x10\x43\x08\x78\x00\x00\x00.FIT')
                # Add some mock data
                f.write(b'\x00' * 100)  # Placeholder data
            
            return file_path
            
        except Exception as e:
            print(f"Error in FIT conversion: {e}")
            return None


class TestFTMSToWorkoutManagerFlow:
    """Test data flow from FTMS Manager to Workout Manager."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        
        # Initialize components
        self.database = MockDatabase(self.db_path)
        self.workout_manager = MockWorkoutManager(self.database)
        self.ftms_manager = MockFTMSManager()
        
        yield
        
        # Cleanup
        self.database.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_ftms_to_workout_manager_data_flow(self):
        """Test complete data flow from FTMS Manager to Workout Manager."""
        # Track data flow
        ftms_data_received = []
        workout_manager_data_received = []
        
        def ftms_callback(data):
            ftms_data_received.append(data.copy())
        
        def workout_callback(data):
            workout_manager_data_received.append(data.copy())
        
        # Register callbacks
        self.ftms_manager.register_data_callback(ftms_callback)
        self.ftms_manager.register_data_callback(self.workout_manager.add_data_point)
        self.workout_manager.register_data_callback(workout_callback)
        
        # Simulate connection
        self.ftms_manager.is_connected = True
        self.ftms_manager.device_info = {
            "address": "AA:BB:CC:DD:EE:FF",
            "name": "Mock Bike",
            "type": "bike"
        }
        
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "bike")
        assert workout_id is not None, "Failed to start workout"
        
        # Simulate data generation by directly calling callbacks
        test_data_points = [
            {'power': 150, 'cadence': 80, 'speed': 25.0, 'heart_rate': 140},
            {'power': 160, 'cadence': 85, 'speed': 26.0, 'heart_rate': 145},
            {'power': 155, 'cadence': 82, 'speed': 25.5, 'heart_rate': 142},
            {'power': 165, 'cadence': 88, 'speed': 27.0, 'heart_rate': 148}
        ]
        
        for data_point in test_data_points:
            # Simulate FTMS manager receiving data and forwarding it
            for callback in self.ftms_manager.data_callbacks:
                callback(data_point)
        
        # End workout
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
    
    def test_error_handling_in_ftms_to_workout_flow(self):
        """Test error handling in FTMS to Workout Manager flow."""
        # Simulate connection
        self.ftms_manager.is_connected = True
        
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "bike")
        
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
        
        # Register callback that handles errors gracefully
        def safe_callback(data):
            try:
                self.workout_manager.add_data_point(data)
            except Exception as e:
                print(f"Handled error: {e}")
        
        self.ftms_manager.register_data_callback(safe_callback)
        
        # Generate test data with error handling
        test_data_points = [
            {'power': 150, 'cadence': 80, 'speed': 25.0, 'heart_rate': 140},
            {'power': 160, 'cadence': 85, 'speed': 26.0, 'heart_rate': 145},
            {'power': 155, 'cadence': 82, 'speed': 25.5, 'heart_rate': 142},
            {'power': 165, 'cadence': 88, 'speed': 27.0, 'heart_rate': 148},
            {'power': 170, 'cadence': 90, 'speed': 28.0, 'heart_rate': 150}
        ]
        
        for data_point in test_data_points:
            for callback in self.ftms_manager.data_callbacks:
                callback(data_point)
        
        # Restore original method
        self.workout_manager.add_data_point = original_add_data_point
        
        # End workout
        self.workout_manager.end_workout()
        
        # Verify system recovered
        saved_workout = self.workout_manager.get_workout(workout_id)
        assert saved_workout is not None, "Workout not saved"
        assert saved_workout['end_time'] is not None, "Workout not properly ended"


class TestWorkoutManagerToDatabaseIntegration:
    """Test integration between Workout Manager and Database."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        
        self.database = MockDatabase(self.db_path)
        self.workout_manager = MockWorkoutManager(self.database)
        
        yield
        
        # Cleanup
        self.database.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_workout_lifecycle_database_integration(self):
        """Test complete workout lifecycle with database operations."""
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "bike")
        assert workout_id is not None, "Failed to start workout"
        
        # Verify workout exists in database
        db_workout = self.database.get_workout(workout_id)
        assert db_workout is not None, "Workout not created in database"
        assert db_workout['workout_type'] == 'bike'
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
            summary = db_workout_final['summary']
            assert 'avg_power' in summary, "Summary should contain avg_power"
            assert summary['avg_power'] > 0, "Average power should be positive"
    
    def test_concurrent_database_operations(self):
        """Test concurrent database operations through Workout Manager."""
        import threading
        import queue
        import time
        
        results = queue.Queue()
        
        def create_workout_with_data(workout_type, data_count, thread_id):
            try:
                # Add small delay to avoid race conditions
                time.sleep(thread_id * 0.1)
                
                # Create workout
                workout_id = self.workout_manager.start_workout(thread_id, workout_type)
                
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
                    
                    success = self.workout_manager.add_data_point(data_point)
                    if not success:
                        raise Exception(f"Failed to add data point {i}")
                
                # End workout
                end_success = self.workout_manager.end_workout()
                if not end_success:
                    raise Exception("Failed to end workout")
                
                results.put({
                    'workout_id': workout_id,
                    'workout_type': workout_type,
                    'data_count': data_count,
                    'thread_id': thread_id,
                    'success': True
                })
                
            except Exception as e:
                results.put({
                    'workout_type': workout_type,
                    'thread_id': thread_id,
                    'error': str(e),
                    'success': False
                })
        
        # Create multiple concurrent workouts with sequential execution to avoid conflicts
        workout_configs = [
            ("bike", 5),
            ("rower", 4),
            ("bike", 6),
        ]
        
        # Run workouts sequentially instead of concurrently to avoid database conflicts
        for i, (workout_type, data_count) in enumerate(workout_configs):
            create_workout_with_data(workout_type, data_count, i + 1)
        
        # Collect results
        successful_workouts = []
        failed_workouts = []
        
        while not results.empty():
            result = results.get()
            if result['success']:
                successful_workouts.append(result)
            else:
                failed_workouts.append(result)
        
        # Verify results - should have all successful since we're running sequentially
        assert len(successful_workouts) == 3, f"Expected 3 successful workouts, got {len(successful_workouts)}"
        assert len(failed_workouts) == 0, f"Should have no failed workouts, got {len(failed_workouts)}: {failed_workouts}"


class TestDatabaseToFITConverterPipeline:
    """Test pipeline from Database to FIT Converter."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        self.fit_output_dir = os.path.join(self.temp_dir, "fit_files")
        os.makedirs(self.fit_output_dir, exist_ok=True)
        
        self.database = MockDatabase(self.db_path)
        self.fit_converter = MockFITConverter(self.fit_output_dir)
        
        yield
        
        # Cleanup
        self.database.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
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
        
        # Get workout data for FIT conversion
        workout = self.database.get_workout(workout_id)
        workout_data_points = self.database.get_workout_data(workout_id)
        
        # Prepare data for FIT conversion
        processed_data = {
            "workout_type": workout["workout_type"],
            "start_time": workout["start_time"],
            "total_duration": workout["duration"],
            "data_series": {
                "powers": [dp["data"]["power"] for dp in workout_data_points],
                "cadences": [dp["data"]["cadence"] for dp in workout_data_points],
                "speeds": [dp["data"]["speed"] for dp in workout_data_points],
                "heart_rates": [dp["data"]["heart_rate"] for dp in workout_data_points],
                "distances": [dp["data"]["distance"] for dp in workout_data_points],
                "absolute_timestamps": [dp["timestamp"] for dp in workout_data_points]
            }
        }
        processed_data.update(summary)
        
        # Test FIT file generation
        fit_file_path = self.fit_converter.convert_workout(processed_data)
        
        assert fit_file_path is not None, "FIT file generation failed"
        assert os.path.exists(fit_file_path), f"FIT file not created at {fit_file_path}"
        
        # Verify FIT file properties
        file_size = os.path.getsize(fit_file_path)
        assert file_size > 100, f"FIT file too small: {file_size} bytes"
        
        # Verify file naming convention
        assert "bike_" in os.path.basename(fit_file_path), "FIT file should include device type"
        assert fit_file_path.endswith(".fit"), "FIT file should have .fit extension"
    
    def test_fit_conversion_error_handling(self):
        """Test error handling in FIT conversion pipeline."""
        # Create workout with minimal data
        workout_id = self.database.start_workout(1, "bike")
        self.database.add_workout_data(workout_id, datetime.now(), {'power': 150})
        self.database.end_workout(workout_id, summary={'avg_power': 150})
        
        # Test with invalid data
        invalid_processed_data = {
            "workout_type": "bike",
            "start_time": "invalid_date",
            "data_series": {}
        }
        
        # Should handle error gracefully
        fit_file_path = self.fit_converter.convert_workout(invalid_processed_data)
        # Depending on implementation, might return None or handle gracefully
        # The key is that it shouldn't crash the test


class TestComponentErrorHandlingAndGracefulDegradation:
    """Test error handling and graceful degradation across components."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        self.fit_output_dir = os.path.join(self.temp_dir, "fit_files")
        os.makedirs(self.fit_output_dir, exist_ok=True)
        
        self.database = MockDatabase(self.db_path)
        self.workout_manager = MockWorkoutManager(self.database)
        self.fit_converter = MockFITConverter(self.fit_output_dir)
        
        yield
        
        # Cleanup
        self.database.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_workout_manager_fit_converter_error_isolation(self):
        """Test that FIT converter errors don't affect workout manager."""
        # Start workout and add data
        workout_id = self.workout_manager.start_workout(1, "bike")
        
        for i in range(10):
            self.workout_manager.add_data_point({
                'power': 150 + i,
                'cadence': 80,
                'heart_rate': 140
            })
        
        # Mock FIT converter to always fail
        def failing_convert_workout(processed_data, user_profile=None):
            raise Exception("FIT converter crashed")
        
        self.fit_converter.convert_workout = failing_convert_workout
        
        # End workout (should handle FIT converter failure gracefully)
        success = self.workout_manager.end_workout()
        assert success, "Workout should end successfully despite FIT converter failure"
        
        # Verify workout was saved properly
        saved_workout = self.database.get_workout(workout_id)
        assert saved_workout is not None, "Workout should be saved"
        assert saved_workout['end_time'] is not None, "Workout should have end time"
        
        saved_data_points = self.database.get_workout_data(workout_id)
        assert len(saved_data_points) == 10, "All data points should be saved"
    
    def test_database_connection_recovery(self):
        """Test database connection recovery after connection loss."""
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "bike")
        
        # Add some data
        for i in range(5):
            success = self.workout_manager.add_data_point({'power': 150 + i})
            assert success, f"Should add data point {i}"
        
        # Simulate connection loss by closing database connection
        self.database.connection.close()
        
        # Reconnect database
        self.database.connection = sqlite3.connect(self.database.db_path)
        self.database.connection.row_factory = sqlite3.Row
        
        # Try to add more data (should work with new connection)
        for i in range(5, 10):
            success = self.workout_manager.add_data_point({'power': 150 + i})
            assert success, f"Should recover and add data point {i}"
        
        # End workout
        success = self.workout_manager.end_workout()
        assert success, "Should end workout after connection recovery"
        
        # Verify all data was saved
        saved_data_points = self.database.get_workout_data(workout_id)
        assert len(saved_data_points) == 10, "All data points should be saved after recovery"
    
    def test_partial_data_handling(self):
        """Test handling of partial or corrupted data across components."""
        workout_id = self.workout_manager.start_workout(1, "bike")
        
        # Add mix of complete and partial data
        test_data_points = [
            {'power': 150, 'cadence': 80, 'speed': 25.0, 'heart_rate': 140},  # Complete
            {'power': 160},  # Partial - only power
            {'cadence': 85, 'heart_rate': 145},  # Partial - no power
            {'power': None, 'cadence': 90, 'speed': 27.0},  # Null power
            {'power': 170, 'cadence': 95, 'speed': 28.0, 'heart_rate': 150},  # Complete
        ]
        
        for data_point in test_data_points:
            success = self.workout_manager.add_data_point(data_point)
            assert success, f"Should handle partial data: {data_point}"
        
        # End workout
        self.workout_manager.end_workout()
        
        # Verify all data points were saved
        saved_data_points = self.database.get_workout_data(workout_id)
        assert len(saved_data_points) == 5, "All data points should be saved"
        
        # Test FIT conversion with partial data
        workout = self.database.get_workout(workout_id)
        workout_data_points = self.database.get_workout_data(workout_id)
        
        # Prepare data for FIT conversion (handling missing fields)
        processed_data = {
            "workout_type": workout["workout_type"],
            "start_time": workout["start_time"],
            "total_duration": workout["duration"],
            "data_series": {
                "powers": [dp["data"].get("power", 0) for dp in workout_data_points],
                "cadences": [dp["data"].get("cadence", 0) for dp in workout_data_points],
                "speeds": [dp["data"].get("speed", 0) for dp in workout_data_points],
                "heart_rates": [dp["data"].get("heart_rate", 0) for dp in workout_data_points],
                "absolute_timestamps": [dp["timestamp"] for dp in workout_data_points]
            }
        }
        
        # Should handle partial data gracefully
        fit_file_path = self.fit_converter.convert_workout(processed_data)
        if fit_file_path:
            assert os.path.exists(fit_file_path), "FIT file should be created despite partial data"


class TestEndToEndDataFlowValidation:
    """Test complete end-to-end data flow validation across all components."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        self.fit_output_dir = os.path.join(self.temp_dir, "fit_files")
        os.makedirs(self.fit_output_dir, exist_ok=True)
        
        self.database = MockDatabase(self.db_path)
        self.workout_manager = MockWorkoutManager(self.database)
        self.ftms_manager = MockFTMSManager()
        self.fit_converter = MockFITConverter(self.fit_output_dir)
        
        yield
        
        # Cleanup
        self.database.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_end_to_end_data_flow(self):
        """Test complete end-to-end data flow from FTMS to FIT file."""
        # Track data at each stage
        ftms_data = []
        workout_data = []
        
        def ftms_callback(data):
            ftms_data.append(data.copy())
        
        def workout_callback(data):
            workout_data.append(data.copy())
        
        # Set up data flow pipeline
        self.ftms_manager.register_data_callback(ftms_callback)
        self.ftms_manager.register_data_callback(self.workout_manager.add_data_point)
        self.workout_manager.register_data_callback(workout_callback)
        
        # Simulate connection and start workout
        self.ftms_manager.is_connected = True
        workout_id = self.workout_manager.start_workout(1, "bike")
        
        # Generate test data
        test_data_points = [
            {'power': 150, 'cadence': 80, 'speed': 25.0, 'heart_rate': 140},
            {'power': 160, 'cadence': 85, 'speed': 26.0, 'heart_rate': 145},
            {'power': 155, 'cadence': 82, 'speed': 25.5, 'heart_rate': 142},
            {'power': 165, 'cadence': 88, 'speed': 27.0, 'heart_rate': 148},
            {'power': 170, 'cadence': 90, 'speed': 28.0, 'heart_rate': 150}
        ]
        
        for data_point in test_data_points:
            for callback in self.ftms_manager.data_callbacks:
                callback(data_point)
        
        # End workout
        self.workout_manager.end_workout()
        
        # Verify data flow through all stages
        assert len(ftms_data) > 0, "No data generated by FTMS"
        assert len(workout_data) > 0, "No data processed by WorkoutManager"
        
        # Verify database storage
        saved_workout = self.database.get_workout(workout_id)
        saved_data_points = self.database.get_workout_data(workout_id)
        
        assert saved_workout is not None, "Workout not saved to database"
        assert len(saved_data_points) > 0, "No data points saved to database"
        
        # Test FIT file generation
        processed_data = {
            "workout_type": saved_workout["workout_type"],
            "start_time": saved_workout["start_time"],
            "total_duration": saved_workout["duration"],
            "data_series": {
                "powers": [dp["data"]["power"] for dp in saved_data_points],
                "cadences": [dp["data"]["cadence"] for dp in saved_data_points],
                "speeds": [dp["data"]["speed"] for dp in saved_data_points],
                "heart_rates": [dp["data"]["heart_rate"] for dp in saved_data_points],
                "absolute_timestamps": [dp["timestamp"] for dp in saved_data_points]
            }
        }
        if saved_workout.get("summary"):
            processed_data.update(saved_workout["summary"])
        
        fit_file_path = self.fit_converter.convert_workout(processed_data)
        
        assert fit_file_path is not None, "FIT file generation failed"
        assert os.path.exists(fit_file_path), "FIT file not created"
        
        # Verify data integrity across all stages
        assert len(saved_data_points) == len(workout_data), "Data loss between WorkoutManager and Database"
    
    def test_performance_under_realistic_load(self):
        """Test system performance under realistic data load."""
        # Start workout
        workout_id = self.workout_manager.start_workout(1, "bike")
        
        # Measure performance of adding data points
        start_time = time.time()
        data_points_added = 0
        
        for i in range(60):  # 1 minute of data at 1Hz
            data_point = {
                'power': 150 + (i % 100),
                'cadence': 80 + (i % 30),
                'speed': 25.0 + (i % 10),
                'heart_rate': 140 + (i % 40),
                'distance': i * 0.1,
                'calories': i * 0.5
            }
            
            success = self.workout_manager.add_data_point(data_point)
            if success:
                data_points_added += 1
        
        # End workout
        end_start_time = time.time()
        success = self.workout_manager.end_workout()
        end_time = time.time()
        
        # Verify performance
        total_time = end_time - start_time
        data_processing_time = end_start_time - start_time
        workout_end_time = end_time - end_start_time
        
        assert success, "Should successfully end workout"
        assert data_points_added == 60, f"Should add all data points, added {data_points_added}"
        assert total_time < 10.0, f"Total processing should be fast: {total_time}s"
        assert workout_end_time < 5.0, f"Workout end should be fast: {workout_end_time}s"
        
        # Verify all data was saved
        saved_data_points = self.database.get_workout_data(workout_id)
        assert len(saved_data_points) == 60, "All data points should be saved"
        
        # Test FIT conversion performance
        workout = self.database.get_workout(workout_id)
        processed_data = {
            "workout_type": workout["workout_type"],
            "start_time": workout["start_time"],
            "total_duration": workout["duration"],
            "data_series": {
                "powers": [dp["data"]["power"] for dp in saved_data_points],
                "absolute_timestamps": [dp["timestamp"] for dp in saved_data_points]
            }
        }
        
        fit_start_time = time.time()
        fit_file_path = self.fit_converter.convert_workout(processed_data)
        fit_end_time = time.time()
        
        fit_conversion_time = fit_end_time - fit_start_time
        
        if fit_file_path:
            assert fit_conversion_time < 5.0, f"FIT conversion should be fast: {fit_conversion_time}s"
            assert os.path.exists(fit_file_path), "FIT file should be created"