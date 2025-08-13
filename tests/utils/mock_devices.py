"""
Mock FTMS devices and Bluetooth utilities for testing.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from unittest.mock import Mock, MagicMock, AsyncMock
import json
import os


class MockFTMSDevice:
    """Mock FTMS device that simulates realistic workout data."""
    
    def __init__(self, device_type: str = "bike", name: str = None, address: str = None):
        self.device_type = device_type
        self.name = name or f"Mock Rogue Echo {device_type.title()}"
        self.address = address or f"AA:BB:CC:DD:EE:{random.randint(10, 99):02X}"
        self.is_connected = False
        self.is_active = False
        
        # Device state
        self.workout_start_time = None
        self.current_data = self._initialize_data()
        self.callbacks = []
        
        # Simulation parameters
        self.data_update_interval = 1.0  # 1 Hz
        self.noise_factor = 0.1
        self.workout_phase = "idle"
        
        # Task for data generation
        self._data_task = None
        
    def _initialize_data(self) -> Dict[str, Any]:
        """Initialize device data based on type."""
        base_data = {
            "timestamp": datetime.now(),
            "power": 0,
            "heart_rate": 0,
            "calories": 0,
            "distance": 0.0
        }
        
        if self.device_type == "bike":
            base_data.update({
                "cadence": 0,
                "speed": 0.0
            })
        elif self.device_type == "rower":
            base_data.update({
                "stroke_rate": 0,
                "stroke_count": 0
            })
            
        return base_data
    
    async def connect(self) -> bool:
        """Simulate device connection."""
        await asyncio.sleep(0.1)  # Simulate connection delay
        self.is_connected = True
        return True
    
    async def disconnect(self) -> bool:
        """Simulate device disconnection."""
        if self._data_task:
            self._data_task.cancel()
            self._data_task = None
        self.is_connected = False
        self.is_active = False
        return True
    
    def start_workout(self):
        """Start workout data generation."""
        if not self.is_connected:
            raise RuntimeError("Device not connected")
            
        self.is_active = True
        self.workout_start_time = datetime.now()
        self.workout_phase = "warmup"
        
        # Start data generation task
        if not self._data_task or self._data_task.done():
            self._data_task = asyncio.create_task(self._generate_data())
    
    def stop_workout(self):
        """Stop workout data generation."""
        self.is_active = False
        self.workout_phase = "idle"
        if self._data_task:
            self._data_task.cancel()
            self._data_task = None
    
    def register_callback(self, callback: Callable):
        """Register callback for data updates."""
        self.callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """Unregister callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def _generate_data(self):
        """Generate realistic workout data."""
        try:
            while self.is_active:
                # Update workout phase based on elapsed time
                elapsed = (datetime.now() - self.workout_start_time).total_seconds()
                self._update_workout_phase(elapsed)
                
                # Generate data based on current phase
                self._update_current_data(elapsed)
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(self.current_data.copy())
                        else:
                            callback(self.current_data.copy())
                    except Exception as e:
                        print(f"Error in callback: {e}")
                
                await asyncio.sleep(self.data_update_interval)
                
        except asyncio.CancelledError:
            pass
    
    def _update_workout_phase(self, elapsed_seconds: float):
        """Update workout phase based on elapsed time."""
        if elapsed_seconds < 300:  # First 5 minutes
            self.workout_phase = "warmup"
        elif elapsed_seconds < 1200:  # Next 15 minutes
            self.workout_phase = "main"
        elif elapsed_seconds < 1500:  # Last 5 minutes
            self.workout_phase = "cooldown"
        else:
            self.workout_phase = "complete"
    
    def _update_current_data(self, elapsed_seconds: float):
        """Update current data based on workout phase and device type."""
        self.current_data["timestamp"] = datetime.now()
        
        # Base intensity based on phase
        phase_intensity = {
            "idle": 0.0,
            "warmup": 0.4,
            "main": 0.8,
            "cooldown": 0.3,
            "complete": 0.0
        }
        
        intensity = phase_intensity.get(self.workout_phase, 0.0)
        
        # Add some variation
        variation = 1.0 + (random.random() - 0.5) * self.noise_factor
        
        if self.device_type == "bike":
            self._update_bike_data(intensity, variation, elapsed_seconds)
        elif self.device_type == "rower":
            self._update_rower_data(intensity, variation, elapsed_seconds)
    
    def _update_bike_data(self, intensity: float, variation: float, elapsed_seconds: float):
        """Update bike-specific data."""
        base_power = 200
        base_cadence = 85
        base_speed = 25.0
        base_hr = 150
        
        self.current_data["power"] = max(0, int(base_power * intensity * variation))
        self.current_data["cadence"] = max(0, int(base_cadence * intensity * variation))
        self.current_data["speed"] = max(0.0, base_speed * intensity * variation)
        self.current_data["heart_rate"] = max(0, int(base_hr + (intensity - 0.5) * 40 * variation))
        
        # Accumulate distance and calories
        if elapsed_seconds > 0:
            distance_increment = self.current_data["speed"] / 3600  # km per second
            self.current_data["distance"] += distance_increment
            
            calorie_rate = self.current_data["power"] * 0.01  # Rough approximation
            self.current_data["calories"] += calorie_rate / 3600  # Per second
    
    def _update_rower_data(self, intensity: float, variation: float, elapsed_seconds: float):
        """Update rower-specific data."""
        base_power = 220
        base_stroke_rate = 24
        base_hr = 155
        
        self.current_data["power"] = max(0, int(base_power * intensity * variation))
        self.current_data["stroke_rate"] = max(0, int(base_stroke_rate * intensity * variation))
        self.current_data["heart_rate"] = max(0, int(base_hr + (intensity - 0.5) * 35 * variation))
        
        # Accumulate distance, calories, and stroke count
        if elapsed_seconds > 0:
            # Rough distance calculation for rower (meters)
            distance_increment = self.current_data["power"] * 0.1 / 3600
            self.current_data["distance"] += distance_increment
            
            calorie_rate = self.current_data["power"] * 0.012
            self.current_data["calories"] += calorie_rate / 3600
            
            # Stroke count based on stroke rate
            if self.current_data["stroke_rate"] > 0:
                self.current_data["stroke_count"] += self.current_data["stroke_rate"] / 60


class MockBluetoothAdapter:
    """Mock Bluetooth adapter for testing."""
    
    def __init__(self):
        self.is_powered = True
        self.is_scanning = False
        self.discovered_devices = []
        self.scan_callbacks = []
    
    async def start_scan(self, callback: Callable = None):
        """Start scanning for devices."""
        self.is_scanning = True
        if callback:
            self.scan_callbacks.append(callback)
        
        # Simulate discovering devices
        await asyncio.sleep(0.1)
        mock_devices = [
            MockFTMSDevice("bike", "Mock Rogue Echo Bike", "AA:BB:CC:DD:EE:01"),
            MockFTMSDevice("rower", "Mock Rogue Echo Rower", "AA:BB:CC:DD:EE:02")
        ]
        
        for device in mock_devices:
            self.discovered_devices.append(device)
            for cb in self.scan_callbacks:
                if asyncio.iscoroutinefunction(cb):
                    await cb(device)
                else:
                    cb(device)
    
    async def stop_scan(self):
        """Stop scanning for devices."""
        self.is_scanning = False
        self.scan_callbacks.clear()
    
    def get_discovered_devices(self) -> List[MockFTMSDevice]:
        """Get list of discovered devices."""
        return self.discovered_devices.copy()


class MockFTMSManager:
    """Mock FTMS Manager for testing."""
    
    def __init__(self):
        self.adapter = MockBluetoothAdapter()
        self.connected_devices = []
        self.callbacks = []
        self.is_scanning = False
    
    async def start_scanning(self):
        """Start scanning for FTMS devices."""
        self.is_scanning = True
        await self.adapter.start_scan()
    
    async def stop_scanning(self):
        """Stop scanning for FTMS devices."""
        self.is_scanning = False
        await self.adapter.stop_scan()
    
    async def connect_device(self, device: MockFTMSDevice) -> bool:
        """Connect to a device."""
        success = await device.connect()
        if success and device not in self.connected_devices:
            self.connected_devices.append(device)
            device.register_callback(self._device_data_callback)
        return success
    
    async def disconnect_device(self, device: MockFTMSDevice) -> bool:
        """Disconnect from a device."""
        success = await device.disconnect()
        if success and device in self.connected_devices:
            self.connected_devices.remove(device)
            device.unregister_callback(self._device_data_callback)
        return success
    
    def register_callback(self, callback: Callable):
        """Register callback for device data."""
        self.callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """Unregister callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def get_discovered_devices(self) -> List[MockFTMSDevice]:
        """Get discovered devices."""
        return self.adapter.get_discovered_devices()
    
    def get_connected_devices(self) -> List[MockFTMSDevice]:
        """Get connected devices."""
        return self.connected_devices.copy()
    
    async def _device_data_callback(self, data: Dict[str, Any]):
        """Handle data from connected devices."""
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                print(f"Error in FTMS Manager callback: {e}")


def create_mock_workout_data(device_type: str, duration: int = 600) -> List[Dict[str, Any]]:
    """Create mock workout data for testing."""
    data_points = []
    start_time = datetime.now() - timedelta(seconds=duration)
    
    for i in range(duration):
        timestamp = start_time + timedelta(seconds=i)
        
        # Create realistic data progression
        progress = i / duration
        intensity = 0.5 + 0.3 * (1 - abs(progress - 0.5) * 2)  # Peak in middle
        
        base_data = {
            "timestamp": timestamp,
            "power": int(200 * intensity + random.randint(-20, 20)),
            "heart_rate": int(150 + intensity * 30 + random.randint(-5, 5)),
            "calories": i * 0.5,
            "distance": i * 0.1
        }
        
        if device_type == "bike":
            base_data.update({
                "cadence": int(80 * intensity + random.randint(-10, 10)),
                "speed": 25.0 * intensity + random.uniform(-2, 2)
            })
        elif device_type == "rower":
            base_data.update({
                "stroke_rate": int(24 * intensity + random.randint(-3, 3)),
                "stroke_count": i // 2
            })
        
        data_points.append(base_data)
    
    return data_points


def inject_data_errors(data_points: List[Dict[str, Any]], error_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Inject errors into workout data for testing error handling."""
    modified_data = data_points.copy()
    
    if "missing_intervals" in error_config:
        for interval in error_config["missing_intervals"]:
            start_idx = interval["start"]
            end_idx = interval["end"]
            # Remove data points in the interval
            modified_data = [dp for i, dp in enumerate(modified_data) 
                           if not (start_idx <= i <= end_idx)]
    
    if "invalid_data_points" in error_config:
        for invalid_point in error_config["invalid_data_points"]:
            timestamp_idx = invalid_point["timestamp"]
            if timestamp_idx < len(modified_data):
                field = invalid_point["field"]
                value = invalid_point["value"]
                modified_data[timestamp_idx][field] = value
    
    if "connection_drops" in error_config:
        for drop in error_config["connection_drops"]:
            start_idx = drop["start"]
            duration = drop["duration"]
            # Mark data points as having connection issues
            for i in range(start_idx, min(start_idx + duration, len(modified_data))):
                modified_data[i]["connection_quality"] = "poor"
    
    return modified_data


class MockDatabaseOperations:
    """Mock database operations for testing."""
    
    def __init__(self):
        self.workouts = {}
        self.data_points = {}
        self.next_workout_id = 1
        self.next_data_point_id = 1
    
    def create_workout(self, workout_data: Dict[str, Any]) -> int:
        """Create a new workout record."""
        workout_id = self.next_workout_id
        self.next_workout_id += 1
        
        workout = {
            "id": workout_id,
            "device_type": workout_data.get("device_type", "bike"),
            "start_time": workout_data.get("start_time", datetime.now()),
            "end_time": workout_data.get("end_time"),
            "duration": workout_data.get("duration", 0),
            "total_distance": workout_data.get("total_distance", 0.0),
            "total_calories": workout_data.get("total_calories", 0),
            "avg_power": workout_data.get("avg_power", 0),
            "max_power": workout_data.get("max_power", 0),
            "avg_heart_rate": workout_data.get("avg_heart_rate", 0),
            "max_heart_rate": workout_data.get("max_heart_rate", 0)
        }
        
        self.workouts[workout_id] = workout
        return workout_id
    
    def add_data_point(self, workout_id: int, data_point: Dict[str, Any]) -> int:
        """Add a data point to a workout."""
        data_point_id = self.next_data_point_id
        self.next_data_point_id += 1
        
        if workout_id not in self.data_points:
            self.data_points[workout_id] = []
        
        point = {
            "id": data_point_id,
            "workout_id": workout_id,
            **data_point
        }
        
        self.data_points[workout_id].append(point)
        return data_point_id
    
    def get_workout(self, workout_id: int) -> Optional[Dict[str, Any]]:
        """Get workout by ID."""
        return self.workouts.get(workout_id)
    
    def get_workout_data_points(self, workout_id: int) -> List[Dict[str, Any]]:
        """Get data points for a workout."""
        return self.data_points.get(workout_id, [])
    
    def get_all_workouts(self) -> List[Dict[str, Any]]:
        """Get all workouts."""
        return list(self.workouts.values())
    
    def delete_workout(self, workout_id: int) -> bool:
        """Delete a workout and its data points."""
        if workout_id in self.workouts:
            del self.workouts[workout_id]
            if workout_id in self.data_points:
                del self.data_points[workout_id]
            return True
        return False
    
    def clear_all_data(self):
        """Clear all data (for test cleanup)."""
        self.workouts.clear()
        self.data_points.clear()
        self.next_workout_id = 1
        self.next_data_point_id = 1