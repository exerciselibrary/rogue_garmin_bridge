#!/usr/bin/env python3
"""
Unit tests for FTMS Manager Module

Tests device discovery, connection management, data callbacks, and error handling.
"""

import pytest
import asyncio
import unittest.mock as mock
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.ftms.ftms_manager import FTMSDeviceManager
from src.ftms.ftms_connector import FTMSConnector
from src.ftms.ftms_simulator import FTMSDeviceSimulator


class TestFTMSDeviceManager:
    """Test cases for FTMSDeviceManager class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_workout_manager = Mock()
        self.mock_workout_manager.active_workout_id = None
        
    def test_init_with_simulator(self):
        """Test initialization with simulator."""
        manager = FTMSDeviceManager(
            workout_manager=self.mock_workout_manager,
            use_simulator=True,
            device_type="bike"
        )
        
        assert manager.workout_manager == self.mock_workout_manager
        assert manager.use_simulator is True
        assert manager.device_status == "disconnected"
        assert manager.connected_device is None
        assert isinstance(manager.connector, FTMSDeviceSimulator)
        assert len(manager.data_callbacks) == 0
        assert len(manager.status_callbacks) == 0
    
    def test_init_with_real_device(self):
        """Test initialization with real device connector."""
        manager = FTMSDeviceManager(
            workout_manager=self.mock_workout_manager,
            use_simulator=False,
            device_type="rower"
        )
        
        assert manager.workout_manager == self.mock_workout_manager
        assert manager.use_simulator is False
        assert manager.device_status == "disconnected"
        assert manager.connected_device is None
        assert isinstance(manager.connector, FTMSConnector)
    
    def test_register_data_callback(self):
        """Test registering data callbacks."""
        manager = FTMSDeviceManager(use_simulator=True)
        callback1 = Mock()
        callback2 = Mock()
        
        manager.register_data_callback(callback1)
        manager.register_data_callback(callback2)
        
        assert len(manager.data_callbacks) == 2
        assert callback1 in manager.data_callbacks
        assert callback2 in manager.data_callbacks
    
    def test_register_status_callback(self):
        """Test registering status callbacks."""
        manager = FTMSDeviceManager(use_simulator=True)
        callback1 = Mock()
        callback2 = Mock()
        
        manager.register_status_callback(callback1)
        manager.register_status_callback(callback2)
        
        assert len(manager.status_callbacks) == 2
        assert callback1 in manager.status_callbacks
        assert callback2 in manager.status_callbacks
    
    def test_handle_data_with_callbacks(self):
        """Test data handling with registered callbacks."""
        manager = FTMSDeviceManager(use_simulator=True)
        callback1 = Mock()
        callback2 = Mock()
        manager.register_data_callback(callback1)
        manager.register_data_callback(callback2)
        
        test_data = {
            'instantaneous_power': 150,
            'heart_rate': 140,
            'cadence': 85
        }
        
        manager._handle_data(test_data)
        
        # Check that data was stored
        assert manager.latest_data == test_data
        
        # Check that callbacks were called
        callback1.assert_called_once_with(test_data)
        callback2.assert_called_once_with(test_data)
    
    def test_handle_data_callback_error(self):
        """Test data handling when callback raises exception."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Create a callback that raises an exception
        error_callback = Mock(side_effect=Exception("Callback error"))
        good_callback = Mock()
        
        manager.register_data_callback(error_callback)
        manager.register_data_callback(good_callback)
        
        test_data = {'power': 100}
        
        # Should not raise exception despite callback error
        manager._handle_data(test_data)
        
        # Good callback should still be called
        good_callback.assert_called_once_with(test_data)
        error_callback.assert_called_once_with(test_data)
    
    def test_handle_status_connected_simulated_device(self):
        """Test status handling for connected simulated device."""
        manager = FTMSDeviceManager(use_simulator=True)
        status_callback = Mock()
        manager.register_status_callback(status_callback)
        
        # Mock simulated device with to_dict method
        mock_device = Mock()
        mock_device.to_dict.return_value = {
            'address': 'AA:BB:CC:DD:EE:FF',
            'name': 'Test Bike',
            'rssi': -50,
            'metadata': {}
        }
        
        manager._handle_status("connected", mock_device)
        
        assert manager.device_status == "connected"
        assert manager.connected_device == mock_device.to_dict.return_value
        assert manager.connected_device_address == 'AA:BB:CC:DD:EE:FF'
        status_callback.assert_called_once_with("connected", mock_device)
    
    def test_handle_status_connected_real_device(self):
        """Test status handling for connected real BLE device."""
        manager = FTMSDeviceManager(use_simulator=False)
        status_callback = Mock()
        manager.register_status_callback(status_callback)
        
        # Mock real BLE device without to_dict method
        mock_device = Mock()
        mock_device.address = 'AA:BB:CC:DD:EE:FF'
        mock_device.name = 'Real Bike'
        mock_device.rssi = -45
        mock_device.metadata = {'manufacturer': 'Test'}
        # Remove to_dict method to simulate real BLE device
        del mock_device.to_dict
        
        manager._handle_status("connected", mock_device)
        
        assert manager.device_status == "connected"
        expected_device = {
            'address': 'AA:BB:CC:DD:EE:FF',
            'name': 'Real Bike',
            'rssi': -45,
            'metadata': {'manufacturer': 'Test'}
        }
        assert manager.connected_device == expected_device
        assert manager.connected_device_address == 'AA:BB:CC:DD:EE:FF'
        status_callback.assert_called_once_with("connected", mock_device)
    
    def test_handle_status_disconnected(self):
        """Test status handling for disconnected device."""
        manager = FTMSDeviceManager(use_simulator=True)
        status_callback = Mock()
        manager.register_status_callback(status_callback)
        
        # Set up initial connected state
        manager.device_status = "connected"
        manager.connected_device = {'address': 'test'}
        manager.connected_device_address = 'test'
        manager.latest_data = {'power': 100}
        
        manager._handle_status("disconnected", None)
        
        assert manager.device_status == "disconnected"
        assert manager.connected_device is None
        assert manager.connected_device_address is None
        assert manager.latest_data is None
        status_callback.assert_called_once_with("disconnected", None)
    
    def test_handle_status_workout_started(self):
        """Test status handling for workout started by device."""
        manager = FTMSDeviceManager(
            workout_manager=self.mock_workout_manager,
            use_simulator=True
        )
        
        # Mock connected device
        manager.connected_device = {'name': 'Test Bike'}
        
        manager._handle_status("workout_started", None)
        
        # Should start workout with bike type
        self.mock_workout_manager.start_workout.assert_called_once_with("bike")
    
    def test_handle_status_workout_started_rower(self):
        """Test status handling for workout started by rower device."""
        manager = FTMSDeviceManager(
            workout_manager=self.mock_workout_manager,
            use_simulator=True
        )
        
        # Mock connected rower device
        manager.connected_device = {'name': 'Test Rower'}
        
        manager._handle_status("workout_started", None)
        
        # Should start workout with rower type
        self.mock_workout_manager.start_workout.assert_called_once_with("rower")
    
    def test_handle_status_workout_started_already_active(self):
        """Test status handling for workout started when workout already active."""
        self.mock_workout_manager.active_workout_id = 123
        manager = FTMSDeviceManager(
            workout_manager=self.mock_workout_manager,
            use_simulator=True
        )
        
        manager._handle_status("workout_started", None)
        
        # Should not start new workout
        self.mock_workout_manager.start_workout.assert_not_called()
    
    def test_handle_status_workout_stopped(self):
        """Test status handling for workout stopped by device."""
        self.mock_workout_manager.active_workout_id = 123
        manager = FTMSDeviceManager(
            workout_manager=self.mock_workout_manager,
            use_simulator=True
        )
        
        manager._handle_status("workout_stopped", None)
        
        # Should end workout
        self.mock_workout_manager.end_workout.assert_called_once()
    
    def test_handle_status_workout_stopped_no_active(self):
        """Test status handling for workout stopped when no active workout."""
        manager = FTMSDeviceManager(
            workout_manager=self.mock_workout_manager,
            use_simulator=True
        )
        
        manager._handle_status("workout_stopped", None)
        
        # Should not try to end workout
        self.mock_workout_manager.end_workout.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_discover_devices_success(self):
        """Test successful device discovery."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        expected_devices = {
            'AA:BB:CC:DD:EE:FF': {'name': 'Test Bike', 'rssi': -50}
        }
        
        # Mock the connector's discover_devices method
        manager.connector.discover_devices = AsyncMock(return_value=expected_devices)
        
        devices = await manager.discover_devices()
        
        assert devices == expected_devices
        manager.connector.discover_devices.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_discover_devices_error(self):
        """Test device discovery with error."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Mock the connector's discover_devices method to raise exception
        manager.connector.discover_devices = AsyncMock(side_effect=Exception("Discovery error"))
        
        devices = await manager.discover_devices()
        
        assert devices == {}
    
    @pytest.mark.asyncio
    async def test_discover_devices_no_method(self):
        """Test device discovery when connector doesn't have discover_devices method."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Remove the discover_devices method
        delattr(manager.connector, 'discover_devices')
        
        devices = await manager.discover_devices()
        
        assert devices == {}
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful device connection."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Mock the connector's connect method
        manager.connector.connect = AsyncMock(return_value=True)
        manager.connector.set_device_type = Mock()
        
        result = await manager.connect('AA:BB:CC:DD:EE:FF', 'bike')
        
        assert result is True
        manager.connector.set_device_type.assert_called_once_with('bike')
        manager.connector.connect.assert_called_once_with('AA:BB:CC:DD:EE:FF')
    
    @pytest.mark.asyncio
    async def test_connect_timeout(self):
        """Test device connection timeout."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Mock the connector's connect method to timeout
        async def slow_connect(address):
            await asyncio.sleep(35)  # Longer than 30s timeout
            return True
        
        manager.connector.connect = slow_connect
        
        result = await manager.connect('AA:BB:CC:DD:EE:FF')
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test device connection failure."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Mock the connector's connect method to return False
        manager.connector.connect = AsyncMock(return_value=False)
        
        result = await manager.connect('AA:BB:CC:DD:EE:FF')
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_connect_exception(self):
        """Test device connection with exception."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Mock the connector's connect method to raise exception
        manager.connector.connect = AsyncMock(side_effect=Exception("Connection error"))
        
        result = await manager.connect('AA:BB:CC:DD:EE:FF')
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """Test successful device disconnection."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Mock the connector's disconnect method
        manager.connector.disconnect = AsyncMock(return_value=True)
        
        result = await manager.disconnect()
        
        assert result is True
        manager.connector.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_error(self):
        """Test device disconnection with error."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Mock the connector's disconnect method to raise exception
        manager.connector.disconnect = AsyncMock(side_effect=Exception("Disconnect error"))
        
        result = await manager.disconnect()
        
        assert result is False
    
    def test_notify_workout_start_success(self):
        """Test successful workout start notification."""
        manager = FTMSDeviceManager(use_simulator=True)
        manager.connector.start_workout = Mock()
        
        result = manager.notify_workout_start(123, "bike")
        
        assert result is True
        manager.connector.start_workout.assert_called_once()
    
    def test_notify_workout_start_no_method(self):
        """Test workout start notification when connector doesn't have start_workout method."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Remove the start_workout method
        delattr(manager.connector, 'start_workout')
        
        result = manager.notify_workout_start(123, "bike")
        
        assert result is False
    
    def test_notify_workout_start_error(self):
        """Test workout start notification with error."""
        manager = FTMSDeviceManager(use_simulator=True)
        manager.connector.start_workout = Mock(side_effect=Exception("Start error"))
        
        result = manager.notify_workout_start(123, "bike")
        
        assert result is False
    
    def test_notify_workout_end_success(self):
        """Test successful workout end notification."""
        manager = FTMSDeviceManager(use_simulator=True)
        manager.connector.end_workout = Mock()
        
        result = manager.notify_workout_end(123)
        
        assert result is True
        manager.connector.end_workout.assert_called_once()
    
    def test_notify_workout_end_no_method(self):
        """Test workout end notification when connector doesn't have end_workout method."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Remove the end_workout method
        delattr(manager.connector, 'end_workout')
        
        result = manager.notify_workout_end(123)
        
        assert result is False
    
    def test_notify_workout_end_error(self):
        """Test workout end notification with error."""
        manager = FTMSDeviceManager(use_simulator=True)
        manager.connector.end_workout = Mock(side_effect=Exception("End error"))
        
        result = manager.notify_workout_end(123)
        
        assert result is False
    
    def test_handle_ftms_data_with_active_workout(self):
        """Test FTMS data handling with active workout."""
        self.mock_workout_manager.active_workout_id = 123
        manager = FTMSDeviceManager(
            workout_manager=self.mock_workout_manager,
            use_simulator=True
        )
        manager.connected_device = {'address': 'test'}
        
        test_data = {'power': 150, 'heart_rate': 140}
        
        manager._handle_ftms_data(test_data)
        
        # Should pass data to workout manager
        self.mock_workout_manager.add_data_point.assert_called_once_with(test_data)
        # Should update latest data
        assert manager.latest_data == test_data
    
    def test_handle_ftms_data_no_active_workout(self):
        """Test FTMS data handling without active workout."""
        manager = FTMSDeviceManager(
            workout_manager=self.mock_workout_manager,
            use_simulator=True
        )
        
        test_data = {'power': 150, 'heart_rate': 140}
        
        manager._handle_ftms_data(test_data)
        
        # Should not pass data to workout manager
        self.mock_workout_manager.add_data_point.assert_not_called()
        # Should still update latest data
        assert manager.latest_data == test_data
    
    def test_handle_ftms_data_with_weight_conversion_metric(self):
        """Test FTMS data handling with weight conversion for metric users."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Mock user profile loading to return metric preference
        with patch.object(manager, '_get_user_unit_preference', return_value='metric'):
            test_data = {'user_weight': 75.0, 'power': 150}
            
            manager._handle_ftms_data(test_data)
            
            assert manager.latest_data['user_weight'] == 75.0
            assert manager.latest_data['user_weight_display'] == 75.0
            assert manager.latest_data['user_weight_unit'] == 'kg'
            assert manager.latest_data['original_weight_kg'] == 75.0
    
    def test_handle_ftms_data_with_weight_conversion_imperial(self):
        """Test FTMS data handling with weight conversion for imperial users."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        # Mock user profile loading to return imperial preference
        with patch.object(manager, '_get_user_unit_preference', return_value='imperial'):
            test_data = {'user_weight': 75.0, 'power': 150}
            
            manager._handle_ftms_data(test_data)
            
            assert manager.latest_data['user_weight'] == 75.0
            assert abs(manager.latest_data['user_weight_display'] - 165.35) < 0.1  # 75kg * 2.20462
            assert manager.latest_data['user_weight_unit'] == 'lbs'
            assert manager.latest_data['original_weight_kg'] == 75.0
    
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('json.load')
    def test_get_user_unit_preference_metric(self, mock_json_load, mock_open, mock_exists):
        """Test getting user unit preference - metric."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        mock_exists.return_value = True
        mock_json_load.return_value = {'unit_preference': 'metric'}
        
        result = manager._get_user_unit_preference()
        
        assert result == 'metric'
    
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('json.load')
    def test_get_user_unit_preference_imperial(self, mock_json_load, mock_open, mock_exists):
        """Test getting user unit preference - imperial."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        mock_exists.return_value = True
        mock_json_load.return_value = {'unit_preference': 'imperial'}
        
        result = manager._get_user_unit_preference()
        
        assert result == 'imperial'
    
    @patch('os.path.exists')
    def test_get_user_unit_preference_no_profile(self, mock_exists):
        """Test getting user unit preference when no profile exists."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        mock_exists.return_value = False
        
        result = manager._get_user_unit_preference()
        
        assert result == 'metric'  # Default
    
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('json.load')
    def test_get_user_unit_preference_error(self, mock_json_load, mock_open, mock_exists):
        """Test getting user unit preference with error."""
        manager = FTMSDeviceManager(use_simulator=True)
        
        mock_exists.return_value = True
        mock_json_load.side_effect = Exception("JSON error")
        
        result = manager._get_user_unit_preference()
        
        assert result == 'metric'  # Default on error


if __name__ == '__main__':
    pytest.main([__file__])