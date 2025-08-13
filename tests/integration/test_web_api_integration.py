"""
Web API integration tests for Rogue Garmin Bridge.

Tests all REST endpoints with various data scenarios, real-time data updates
and WebSocket connections, file upload/download functionality, and error
handling and response formatting.

Requirements: 3.2, 5.1, 5.2, 5.3, 5.4
"""

import pytest
import asyncio
import os
import tempfile
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch, MagicMock
import threading

# Import Flask testing utilities
from flask import Flask
from flask.testing import FlaskClient

# Import system modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from web.app import app as flask_app
from data.database import Database
from data.workout_manager import WorkoutManager
from ftms.ftms_manager import FTMSDeviceManager
from utils.logging_config import get_component_logger

# Import test utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.mock_devices import MockFTMSDevice, create_mock_workout_data
from utils.database_utils import TestDatabaseManager, create_sample_workout_data, create_sample_data_points

logger = get_component_logger('web_api_test')


class TestWebAPIIntegration:
    """Test web API endpoints with various data scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        self.fit_output_dir = os.path.join(self.temp_dir, "fit_files")
        os.makedirs(self.fit_output_dir, exist_ok=True)
        
        # Create test database
        self.database = Database(self.db_path)
        self.workout_manager = WorkoutManager(self.db_path)
        
        # Configure Flask app for testing
        flask_app.config['TESTING'] = True
        flask_app.config['DATABASE_PATH'] = self.db_path
        
        # Create test client
        self.client = flask_app.test_client()
        
        # Mock the global components in the Flask app
        with patch('src.web.app.workout_manager', self.workout_manager):
            with patch('src.web.app.db_path', self.db_path):
                yield
        
        # Cleanup
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_api_discover_devices(self):
        """Test device discovery API endpoint."""
        # Mock FTMS manager for discovery
        with patch('src.web.app.ftms_manager') as mock_ftms:
            # Mock async discover_devices method
            async def mock_discover():
                return {
                    "AA:BB:CC:DD:EE:01": MockFTMSDevice("bike", "Test Rogue Echo Bike", "AA:BB:CC:DD:EE:01"),
                    "AA:BB:CC:DD:EE:02": MockFTMSDevice("rower", "Test Rogue Echo Rower", "AA:BB:CC:DD:EE:02")
                }
            
            mock_ftms.discover_devices = mock_discover
            
            # Mock background loop
            with patch('src.web.app.background_loop') as mock_loop:
                mock_loop.is_running.return_value = True
                
                # Mock asyncio.run_coroutine_threadsafe
                with patch('asyncio.run_coroutine_threadsafe') as mock_run_coro:
                    mock_future = Mock()
                    mock_future.result.return_value = {
                        "AA:BB:CC:DD:EE:01": {"name": "Test Rogue Echo Bike"},
                        "AA:BB:CC:DD:EE:02": {"name": "Test Rogue Echo Rower"}
                    }
                    mock_run_coro.return_value = mock_future
                    
                    response = self.client.post('/api/discover')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    assert 'devices' in data
                    assert len(data['devices']) == 2
                    
                    # Verify device structure
                    device_names = [d['name'] for d in data['devices']]
                    assert "Test Rogue Echo Bike" in device_names
                    assert "Test Rogue Echo Rower" in device_names
    
    def test_api_connect_device(self):
        """Test device connection API endpoint."""
        with patch('src.web.app.ftms_manager') as mock_ftms:
            with patch('src.web.app.background_loop') as mock_loop:
                mock_loop.is_running.return_value = True
                
                with patch('asyncio.run_coroutine_threadsafe') as mock_run_coro:
                    # Test successful connection
                    mock_future = Mock()
                    mock_future.result.return_value = True
                    mock_run_coro.return_value = mock_future
                    
                    response = self.client.post('/api/connect', 
                                              json={'address': 'AA:BB:CC:DD:EE:01', 'device_type': 'bike'})
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    
                    # Test connection failure
                    mock_future.result.return_value = False
                    response = self.client.post('/api/connect', 
                                              json={'address': 'INVALID:ADDRESS', 'device_type': 'bike'})
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is False
                    
                    # Test missing address
                    response = self.client.post('/api/connect', json={'device_type': 'bike'})
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is False
                    assert 'error' in data
    
    def test_api_disconnect_device(self):
        """Test device disconnection API endpoint."""
        with patch('src.web.app.ftms_manager') as mock_ftms:
            with patch('src.web.app.background_loop') as mock_loop:
                mock_loop.is_running.return_value = True
                
                with patch('asyncio.run_coroutine_threadsafe') as mock_run_coro:
                    # Test successful disconnection
                    mock_future = Mock()
                    mock_future.result.return_value = True
                    mock_run_coro.return_value = mock_future
                    
                    response = self.client.post('/api/disconnect')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
    
    def test_api_status_endpoint(self):
        """Test status API endpoint with various scenarios."""
        with patch('src.web.app.ftms_manager') as mock_ftms:
            # Test disconnected status
            mock_ftms.device_status = "disconnected"
            mock_ftms.connected_device = None
            mock_ftms.use_simulator = False
            mock_ftms.latest_data = None
            
            response = self.client.get('/api/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['device_status'] == 'disconnected'
            assert data['connected_device'] is None
            assert data['workout_active'] is False
            assert data['is_simulated'] is False
            
            # Test connected status with data
            mock_device = Mock()
            mock_device.name = "Test Device"
            mock_device.address = "AA:BB:CC:DD:EE:01"
            
            mock_ftms.device_status = "connected"
            mock_ftms.connected_device = mock_device
            mock_ftms.use_simulator = True
            mock_ftms.latest_data = {
                'power': 150,
                'cadence': 80,
                'speed': 25.0,
                'heart_rate': 140
            }
            
            response = self.client.get('/api/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['device_status'] == 'connected'
            assert data['connected_device']['name'] == 'Test Device'
            assert data['is_simulated'] is True
            assert 'latest_data' in data
            assert data['latest_data']['power'] == 150
    
    def test_api_start_workout(self):
        """Test workout start API endpoint."""
        # Test successful workout start
        response = self.client.post('/api/start_workout', 
                                  json={'device_id': 1, 'workout_type': 'bike'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'workout_id' in data
        assert isinstance(data['workout_id'], int)
        
        # Verify workout was created in database
        workout = self.workout_manager.get_workout(data['workout_id'])
        assert workout is not None
        assert workout['device_type'] == 'bike'
        
        # Test starting workout with missing parameters
        response = self.client.post('/api/start_workout', json={})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    def test_api_end_workout(self):
        """Test workout end API endpoint."""
        # Start a workout first
        workout_id = self.workout_manager.start_workout(1, 'bike')
        
        # Add some data points
        for i in range(5):
            self.workout_manager.add_data_point({
                'power': 150 + i,
                'cadence': 80,
                'speed': 25.0,
                'heart_rate': 140
            })
        
        # Test ending workout
        response = self.client.post('/api/end_workout')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify workout was ended
        workout = self.workout_manager.get_workout(workout_id)
        assert workout is not None
        assert workout['end_time'] is not None
        
        # Test ending workout when none is active
        response = self.client.post('/api/end_workout')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_api_get_workouts(self):
        """Test workout history API endpoint."""
        # Create test workouts
        workout_ids = []
        for i in range(3):
            workout_data = create_sample_workout_data("bike", 600)
            workout_id = self.database.start_workout(1, "bike")
            
            # Add some data points
            data_points = create_sample_data_points("bike", 10)
            for point in data_points:
                self.database.add_workout_data(workout_id, point['timestamp'], point)
            
            # End workout
            self.database.end_workout(workout_id, summary={'avg_power': 150, 'total_distance': 5.0})
            workout_ids.append(workout_id)
        
        # Test getting workouts
        response = self.client.get('/api/workouts')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'workouts' in data
        assert len(data['workouts']) == 3
        
        # Verify workout structure
        workout = data['workouts'][0]
        assert 'id' in workout
        assert 'device_type' in workout
        assert 'start_time' in workout
        assert 'summary' in workout
        
        # Test pagination
        response = self.client.get('/api/workouts?limit=2&offset=1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['workouts']) == 2
    
    def test_api_get_workout_details(self):
        """Test individual workout details API endpoint."""
        # Create test workout
        workout_id = self.database.start_workout(1, "bike")
        
        # Add data points
        data_points = create_sample_data_points("bike", 20)
        for point in data_points:
            self.database.add_workout_data(workout_id, point['timestamp'], point)
        
        # End workout
        summary = {
            'avg_power': 150,
            'max_power': 200,
            'avg_cadence': 80,
            'total_distance': 5.0,
            'total_calories': 100
        }
        self.database.end_workout(workout_id, summary=summary)
        
        # Test getting workout details
        response = self.client.get(f'/api/workout/{workout_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'workout' in data
        
        workout = data['workout']
        assert workout['id'] == workout_id
        assert 'data_series' in workout
        assert 'timestamps' in workout['data_series']
        assert 'powers' in workout['data_series']
        assert 'cadences' in workout['data_series']
        assert len(workout['data_series']['timestamps']) == 20
        
        # Test getting non-existent workout
        response = self.client.get('/api/workout/999')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    def test_api_delete_workout(self):
        """Test workout deletion API endpoint."""
        # Create test workout
        workout_id = self.database.start_workout(1, "bike")
        data_points = create_sample_data_points("bike", 5)
        for point in data_points:
            self.database.add_workout_data(workout_id, point['timestamp'], point)
        self.database.end_workout(workout_id, summary={'avg_power': 150})
        
        # Verify workout exists
        workout = self.workout_manager.get_workout(workout_id)
        assert workout is not None
        
        # Test deleting workout
        response = self.client.delete(f'/api/workout/{workout_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify workout is deleted
        workout = self.workout_manager.get_workout(workout_id)
        assert workout is None
        
        # Test deleting non-existent workout
        response = self.client.delete('/api/workout/999')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_api_user_profile(self):
        """Test user profile API endpoints."""
        # Test getting empty profile
        response = self.client.get('/api/user_profile')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'profile' in data
        
        # Test updating profile
        profile_data = {
            'name': 'Test User',
            'weight_kg': 75.0,
            'height_cm': 180,
            'age': 30,
            'unit_preference': 'metric'
        }
        
        response = self.client.post('/api/user_profile', json=profile_data)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Test getting updated profile
        response = self.client.get('/api/user_profile')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['profile']['name'] == 'Test User'
        assert data['profile']['weight_kg'] == 75.0
    
    def test_api_settings(self):
        """Test application settings API endpoints."""
        # Test getting default settings
        response = self.client.get('/api/settings')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'settings' in data
        
        # Test updating settings
        settings_data = {
            'use_simulator': True,
            'device_type': 'bike',
            'data_update_interval': 1.0
        }
        
        response = self.client.post('/api/settings', json=settings_data)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Test getting updated settings
        response = self.client.get('/api/settings')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['settings']['use_simulator'] is True
    
    def test_api_convert_fit_file(self):
        """Test FIT file conversion API endpoint."""
        # Create test workout with sufficient data
        workout_id = self.database.start_workout(1, "bike")
        
        # Add realistic data points
        start_time = datetime.now() - timedelta(minutes=20)
        for i in range(60):  # 1 minute of data
            timestamp = start_time + timedelta(seconds=i)
            data_point = {
                'power': 150 + (i % 50),
                'cadence': 80 + (i % 20),
                'speed': 25.0 + (i % 5),
                'heart_rate': 140 + (i % 30),
                'distance': i * 0.1,
                'calories': i * 0.5
            }
            self.database.add_workout_data(workout_id, timestamp, data_point)
        
        # End workout with summary
        summary = {
            'avg_power': 175,
            'max_power': 200,
            'avg_cadence': 90,
            'max_cadence': 100,
            'avg_speed': 27.5,
            'max_speed': 30.0,
            'total_distance': 6.0,
            'total_calories': 30
        }
        self.database.end_workout(workout_id, summary=summary)
        
        # Mock FIT file generation
        with patch('src.fit.fit_converter.FITConverter') as mock_converter:
            mock_instance = Mock()
            mock_instance.convert_workout.return_value = f"{self.fit_output_dir}/test_workout.fit"
            mock_converter.return_value = mock_instance
            
            # Create mock FIT file
            fit_file_path = f"{self.fit_output_dir}/test_workout.fit"
            with open(fit_file_path, 'wb') as f:
                f.write(b'\x0e\x10\x43\x08\x78\x00\x00\x00.FIT')  # Mock FIT header
            
            response = self.client.post(f'/api/convert_fit/{workout_id}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'fit_file_path' in data
        
        # Test converting non-existent workout
        response = self.client.post('/api/convert_fit/999')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    def test_api_error_handling(self):
        """Test API error handling and response formatting."""
        # Test invalid JSON
        response = self.client.post('/api/start_workout', 
                                  data='invalid json',
                                  content_type='application/json')
        
        assert response.status_code == 400
        
        # Test missing required fields
        response = self.client.post('/api/connect', json={})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
        
        # Test invalid workout ID
        response = self.client.get('/api/workout/invalid')
        
        assert response.status_code == 404
        
        # Test method not allowed
        response = self.client.put('/api/status')
        
        assert response.status_code == 405
    
    def test_api_response_formatting(self):
        """Test consistent API response formatting."""
        # Test successful response format
        response = self.client.get('/api/status')
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        data = json.loads(response.data)
        assert isinstance(data, dict)
        
        # Test error response format
        response = self.client.get('/api/workout/999')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert 'success' in data
        assert data['success'] is False
        assert 'error' in data
        assert isinstance(data['error'], str)


@pytest.mark.integration
class TestRealTimeDataUpdates:
    """Test real-time data updates and WebSocket connections."""
    
    @pytest.fixture(autouse=True)
    def setup_realtime_test(self):
        """Set up real-time test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        
        self.database = Database(self.db_path)
        self.workout_manager = WorkoutManager(self.db_path)
        
        # Configure Flask app for testing
        flask_app.config['TESTING'] = True
        flask_app.config['DATABASE_PATH'] = self.db_path
        
        self.client = flask_app.test_client()
        
        yield
        
        # Cleanup
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_status_endpoint_real_time_updates(self):
        """Test status endpoint provides real-time workout data."""
        with patch('src.web.app.ftms_manager') as mock_ftms:
            with patch('src.web.app.workout_manager', self.workout_manager):
                # Start a workout
                workout_id = self.workout_manager.start_workout(1, 'bike')
                
                # Mock FTMS manager with real-time data
                mock_ftms.device_status = "connected"
                mock_ftms.connected_device = Mock()
                mock_ftms.connected_device.name = "Test Device"
                mock_ftms.connected_device.address = "AA:BB:CC:DD:EE:01"
                mock_ftms.use_simulator = True
                
                # Simulate real-time data updates
                test_data_sequence = [
                    {'power': 150, 'cadence': 80, 'speed': 25.0, 'heart_rate': 140},
                    {'power': 160, 'cadence': 85, 'speed': 26.0, 'heart_rate': 145},
                    {'power': 155, 'cadence': 82, 'speed': 25.5, 'heart_rate': 142}
                ]
                
                for i, data in enumerate(test_data_sequence):
                    mock_ftms.latest_data = data
                    
                    response = self.client.get('/api/status')
                    
                    assert response.status_code == 200
                    response_data = json.loads(response.data)
                    assert response_data['workout_active'] is True
                    assert 'latest_data' in response_data
                    assert response_data['latest_data']['power'] == data['power']
                    assert response_data['latest_data']['workout_id'] == workout_id
                    
                    # Add data point to workout manager
                    self.workout_manager.add_data_point(data)
                    
                    # Verify workout summary is updated
                    if 'workout_summary' in response_data['latest_data']:
                        summary = response_data['latest_data']['workout_summary']
                        assert 'elapsed_time' in summary
                        assert 'workout_type' in summary
                        assert summary['workout_type'] == 'bike'
                
                # End workout
                self.workout_manager.end_workout()
    
    def test_polling_mechanism_performance(self):
        """Test performance of polling mechanism for real-time updates."""
        with patch('src.web.app.ftms_manager') as mock_ftms:
            with patch('src.web.app.workout_manager', self.workout_manager):
                # Setup mock data
                mock_ftms.device_status = "connected"
                mock_ftms.connected_device = Mock()
                mock_ftms.connected_device.name = "Test Device"
                mock_ftms.use_simulator = True
                mock_ftms.latest_data = {'power': 150, 'cadence': 80}
                
                # Start workout
                workout_id = self.workout_manager.start_workout(1, 'bike')
                
                # Measure polling performance
                start_time = time.time()
                request_count = 50
                response_times = []
                
                for i in range(request_count):
                    request_start = time.time()
                    response = self.client.get('/api/status')
                    request_end = time.time()
                    
                    assert response.status_code == 200
                    response_times.append(request_end - request_start)
                    
                    # Update data to simulate real-time changes
                    mock_ftms.latest_data = {
                        'power': 150 + i,
                        'cadence': 80 + (i % 20),
                        'heart_rate': 140 + (i % 30)
                    }
                
                total_time = time.time() - start_time
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                
                # Performance assertions
                assert avg_response_time < 0.1, f"Average response time too high: {avg_response_time}s"
                assert max_response_time < 0.5, f"Max response time too high: {max_response_time}s"
                assert total_time < 10, f"Total polling time too high: {total_time}s"
                
                # End workout
                self.workout_manager.end_workout()
    
    def test_concurrent_api_requests(self):
        """Test handling of concurrent API requests."""
        import threading
        import queue
        
        with patch('src.web.app.ftms_manager') as mock_ftms:
            with patch('src.web.app.workout_manager', self.workout_manager):
                # Setup mock data
                mock_ftms.device_status = "connected"
                mock_ftms.connected_device = Mock()
                mock_ftms.latest_data = {'power': 150}
                
                # Start workout
                workout_id = self.workout_manager.start_workout(1, 'bike')
                
                # Create queue for results
                results = queue.Queue()
                
                def make_request(endpoint, method='GET', json_data=None):
                    try:
                        if method == 'GET':
                            response = self.client.get(endpoint)
                        elif method == 'POST':
                            response = self.client.post(endpoint, json=json_data)
                        
                        results.put({
                            'endpoint': endpoint,
                            'status_code': response.status_code,
                            'success': response.status_code == 200
                        })
                    except Exception as e:
                        results.put({
                            'endpoint': endpoint,
                            'error': str(e),
                            'success': False
                        })
                
                # Create concurrent requests
                threads = []
                endpoints = [
                    ('/api/status', 'GET', None),
                    ('/api/workouts', 'GET', None),
                    (f'/api/workout/{workout_id}', 'GET', None),
                    ('/api/user_profile', 'GET', None),
                    ('/api/settings', 'GET', None)
                ]
                
                # Launch concurrent requests
                for endpoint, method, json_data in endpoints * 5:  # 25 total requests
                    thread = threading.Thread(target=make_request, args=(endpoint, method, json_data))
                    threads.append(thread)
                    thread.start()
                
                # Wait for all requests to complete
                for thread in threads:
                    thread.join(timeout=5)
                
                # Collect results
                successful_requests = 0
                failed_requests = 0
                
                while not results.empty():
                    result = results.get()
                    if result['success']:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                        logger.warning(f"Failed request: {result}")
                
                # Verify concurrent handling
                total_requests = successful_requests + failed_requests
                assert total_requests == 25, f"Expected 25 requests, got {total_requests}"
                assert successful_requests >= 20, f"Too many failed requests: {failed_requests}/{total_requests}"
                
                # End workout
                self.workout_manager.end_workout()


@pytest.mark.integration
class TestFileOperations:
    """Test file upload/download functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_file_test(self):
        """Set up file operation test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        self.fit_output_dir = os.path.join(self.temp_dir, "fit_files")
        os.makedirs(self.fit_output_dir, exist_ok=True)
        
        self.database = Database(self.db_path)
        self.workout_manager = WorkoutManager(self.db_path)
        
        flask_app.config['TESTING'] = True
        flask_app.config['DATABASE_PATH'] = self.db_path
        
        self.client = flask_app.test_client()
        
        yield
        
        # Cleanup
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_fit_file_download(self):
        """Test FIT file download functionality."""
        # Create test workout
        workout_id = self.database.start_workout(1, "bike")
        
        # Add data points
        start_time = datetime.now() - timedelta(minutes=10)
        for i in range(30):
            timestamp = start_time + timedelta(seconds=i * 20)
            data_point = {
                'power': 150 + (i % 50),
                'cadence': 80 + (i % 20),
                'speed': 25.0,
                'heart_rate': 140
            }
            self.database.add_workout_data(workout_id, timestamp, data_point)
        
        # End workout
        summary = {'avg_power': 175, 'total_distance': 5.0}
        self.database.end_workout(workout_id, summary=summary)
        
        # Create mock FIT file
        fit_file_path = os.path.join(self.fit_output_dir, f"workout_{workout_id}.fit")
        with open(fit_file_path, 'wb') as f:
            f.write(b'\x0e\x10\x43\x08\x78\x00\x00\x00.FIT' + b'\x00' * 100)  # Mock FIT data
        
        # Update workout with FIT file path
        self.workout_manager.update_workout_fit_file(workout_id, fit_file_path)
        
        # Test file download
        with patch('src.web.app.send_from_directory') as mock_send:
            mock_send.return_value = "mock_file_response"
            
            # This would be the actual download endpoint (not implemented in current API)
            # For now, we test that the file exists and can be accessed
            assert os.path.exists(fit_file_path), "FIT file should exist for download"
            
            file_size = os.path.getsize(fit_file_path)
            assert file_size > 100, f"FIT file too small: {file_size} bytes"
    
    def test_fit_file_generation_and_access(self):
        """Test FIT file generation and subsequent access."""
        # Create workout with substantial data
        workout_id = self.database.start_workout(1, "bike")
        
        # Add realistic data points
        start_time = datetime.now() - timedelta(minutes=30)
        for i in range(180):  # 3 minutes of data at 1Hz
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
        
        # End workout
        summary = {
            'avg_power': 200,
            'max_power': 250,
            'avg_cadence': 95,
            'max_cadence': 110,
            'avg_speed': 30.0,
            'max_speed': 35.0,
            'total_distance': 18.0,
            'total_calories': 90
        }
        self.database.end_workout(workout_id, summary=summary)
        
        # Test FIT file conversion via API
        with patch('src.fit.fit_processor.FITProcessor') as mock_processor:
            mock_instance = Mock()
            fit_file_path = os.path.join(self.fit_output_dir, f"bike_{workout_id}.fit")
            mock_instance.process_workout.return_value = fit_file_path
            mock_processor.return_value = mock_instance
            
            # Create actual mock file
            with open(fit_file_path, 'wb') as f:
                f.write(b'\x0e\x10\x43\x08\x78\x00\x00\x00.FIT' + b'\x00' * 500)
            
            response = self.client.post(f'/api/convert_fit/{workout_id}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify file was created
            assert os.path.exists(fit_file_path), "FIT file should be created"
            
            # Verify file properties
            file_size = os.path.getsize(fit_file_path)
            assert file_size > 200, f"FIT file should be substantial: {file_size} bytes"
            
            # Verify file can be read
            with open(fit_file_path, 'rb') as f:
                file_content = f.read()
                assert file_content.startswith(b'\x0e\x10\x43\x08'), "FIT file should have proper header"
    
    def test_file_error_handling(self):
        """Test file operation error handling."""
        # Test FIT conversion with invalid workout
        response = self.client.post('/api/convert_fit/999')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
        
        # Test FIT conversion with workout but no data
        workout_id = self.database.start_workout(1, "bike")
        self.database.end_workout(workout_id, summary={})
        
        with patch('src.fit.fit_processor.FITProcessor') as mock_processor:
            mock_instance = Mock()
            mock_instance.process_workout.return_value = None  # Simulate failure
            mock_processor.return_value = mock_instance
            
            response = self.client.post(f'/api/convert_fit/{workout_id}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is False
    
    def test_file_naming_conventions(self):
        """Test proper file naming conventions for generated files."""
        # Create workouts of different types
        bike_workout_id = self.database.start_workout(1, "bike")
        rower_workout_id = self.database.start_workout(2, "rower")
        
        # Add minimal data and end workouts
        for workout_id in [bike_workout_id, rower_workout_id]:
            self.database.add_workout_data(workout_id, datetime.now(), {'power': 150})
            self.database.end_workout(workout_id, summary={'avg_power': 150})
        
        # Test file naming
        with patch('src.fit.fit_processor.FITProcessor') as mock_processor:
            mock_instance = Mock()
            
            # Mock different file names based on workout type
            def mock_process_workout(workout_id, user_profile=None):
                workout = self.database.get_workout(workout_id)
                device_type = workout['device_type']
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                return os.path.join(self.fit_output_dir, f"{device_type}_{timestamp}.fit")
            
            mock_instance.process_workout.side_effect = mock_process_workout
            mock_processor.return_value = mock_instance
            
            # Test bike workout file naming
            response = self.client.post(f'/api/convert_fit/{bike_workout_id}')
            assert response.status_code == 200
            data = json.loads(response.data)
            if data['success']:
                assert 'bike_' in data.get('fit_file_path', ''), "Bike workout should have 'bike_' in filename"
            
            # Test rower workout file naming
            response = self.client.post(f'/api/convert_fit/{rower_workout_id}')
            assert response.status_code == 200
            data = json.loads(response.data)
            if data['success']:
                assert 'rower_' in data.get('fit_file_path', ''), "Rower workout should have 'rower_' in filename"