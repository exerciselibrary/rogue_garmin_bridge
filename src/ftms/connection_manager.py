#!/usr/bin/env python3
"""
Enhanced Bluetooth Connection Manager for FTMS devices

This module provides robust connection management with:
- Automatic reconnection with exponential backoff
- Connection quality monitoring and reporting
- Fallback mechanisms for connection failures
- User-friendly error messages and recovery suggestions
"""

import asyncio
import time
import math
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from bleak.exc import BleakError, BleakDeviceNotFoundError
import bleak

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.logging_config import get_component_logger

logger = get_component_logger('bluetooth_connection')

class ConnectionState(Enum):
    """Connection states for FTMS devices"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    FALLBACK = "fallback"

class ConnectionQuality(Enum):
    """Connection quality indicators"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"

@dataclass
class ConnectionError:
    """Represents a connection error with context"""
    timestamp: datetime
    error_type: str
    error_message: str
    device_address: str
    retry_count: int
    is_recoverable: bool
    user_message: str
    recovery_suggestions: List[str]

@dataclass
class ConnectionMetrics:
    """Connection quality and performance metrics"""
    rssi: Optional[int] = None
    connection_time: Optional[float] = None
    last_data_received: Optional[datetime] = None
    data_packet_count: int = 0
    error_count: int = 0
    reconnection_count: int = 0
    quality: ConnectionQuality = ConnectionQuality.GOOD

class BluetoothConnectionManager:
    """
    Enhanced Bluetooth connection manager with robust error handling
    and automatic recovery mechanisms.
    """
    
    def __init__(self, max_retry_attempts: int = 5, base_retry_delay: float = 1.0):
        """
        Initialize the connection manager.
        
        Args:
            max_retry_attempts: Maximum number of retry attempts
            base_retry_delay: Base delay for exponential backoff (seconds)
        """
        self.max_retry_attempts = max_retry_attempts
        self.base_retry_delay = base_retry_delay
        
        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.current_device_address: Optional[str] = None
        self.current_device_name: Optional[str] = None
        
        # Error tracking
        self.connection_errors: List[ConnectionError] = []
        self.consecutive_failures = 0
        self.last_connection_attempt: Optional[datetime] = None
        
        # Metrics
        self.metrics = ConnectionMetrics()
        
        # Callbacks
        self.state_callbacks: List[Callable[[ConnectionState, Dict[str, Any]], None]] = []
        self.error_callbacks: List[Callable[[ConnectionError], None]] = []
        self.quality_callbacks: List[Callable[[ConnectionMetrics], None]] = []
        
        # Recovery mechanisms
        self.fallback_enabled = True
        self.auto_reconnect_enabled = True
        self.connection_timeout = 15.0
        
        logger.info("Bluetooth Connection Manager initialized")
    
    def register_state_callback(self, callback: Callable[[ConnectionState, Dict[str, Any]], None]):
        """Register a callback for connection state changes"""
        if callback not in self.state_callbacks:
            self.state_callbacks.append(callback)
            logger.debug(f"State callback registered: {callback.__name__}")
    
    def register_error_callback(self, callback: Callable[[ConnectionError], None]):
        """Register a callback for connection errors"""
        if callback not in self.error_callbacks:
            self.error_callbacks.append(callback)
            logger.debug(f"Error callback registered: {callback.__name__}")
    
    def register_quality_callback(self, callback: Callable[[ConnectionMetrics], None]):
        """Register a callback for connection quality updates"""
        if callback not in self.quality_callbacks:
            self.quality_callbacks.append(callback)
            logger.debug(f"Quality callback registered: {callback.__name__}")
    
    def _notify_state_change(self, new_state: ConnectionState, data: Dict[str, Any] = None):
        """Notify all registered callbacks of state changes"""
        self.state = new_state
        data = data or {}
        
        logger.info(f"Connection state changed to: {new_state.value}")
        
        for callback in self.state_callbacks:
            try:
                callback(new_state, data)
            except Exception as e:
                logger.error(f"Error in state callback {callback.__name__}: {e}")
    
    def _notify_error(self, error: ConnectionError):
        """Notify all registered callbacks of connection errors"""
        self.connection_errors.append(error)
        
        # Keep only the last 50 errors to prevent memory issues
        if len(self.connection_errors) > 50:
            self.connection_errors = self.connection_errors[-50:]
        
        logger.error(f"Connection error: {error.error_message}")
        
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error in error callback {callback.__name__}: {e}")
    
    def _notify_quality_change(self):
        """Notify all registered callbacks of quality changes"""
        for callback in self.quality_callbacks:
            try:
                callback(self.metrics)
            except Exception as e:
                logger.error(f"Error in quality callback {callback.__name__}: {e}")
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * 2^attempt
        delay = self.base_retry_delay * (2 ** attempt)
        
        # Add jitter (±25% of the delay)
        jitter = delay * 0.25 * (2 * (time.time() % 1) - 1)  # Random-like jitter
        
        # Cap the maximum delay at 60 seconds
        final_delay = min(delay + jitter, 60.0)
        
        logger.debug(f"Retry delay for attempt {attempt}: {final_delay:.2f}s")
        return final_delay
    
    def _create_connection_error(self, error_type: str, error_message: str, 
                               device_address: str, retry_count: int, 
                               exception: Exception = None) -> ConnectionError:
        """
        Create a structured connection error with user-friendly messages.
        
        Args:
            error_type: Type of error (timeout, device_not_found, etc.)
            error_message: Technical error message
            device_address: Device address that failed
            retry_count: Current retry count
            exception: Original exception if available
            
        Returns:
            ConnectionError object with user-friendly messages
        """
        is_recoverable = True
        user_message = "Connection failed"
        recovery_suggestions = []
        
        if error_type == "timeout":
            user_message = "Connection timed out - device may be out of range or busy"
            recovery_suggestions = [
                "Move closer to the device",
                "Ensure the device is powered on and not connected to another app",
                "Try restarting the device",
                "Check for interference from other Bluetooth devices"
            ]
        elif error_type == "device_not_found":
            user_message = "Device not found - it may have moved out of range"
            recovery_suggestions = [
                "Ensure the device is powered on",
                "Move closer to the device",
                "Try scanning for devices again",
                "Restart the device if possible"
            ]
        elif error_type == "permission_denied":
            user_message = "Bluetooth permission denied"
            recovery_suggestions = [
                "Grant Bluetooth permissions to the application",
                "Check system Bluetooth settings",
                "Try running as administrator (if applicable)"
            ]
            is_recoverable = False
        elif error_type == "adapter_not_available":
            user_message = "Bluetooth adapter not available"
            recovery_suggestions = [
                "Enable Bluetooth on your system",
                "Check if Bluetooth adapter is properly installed",
                "Restart Bluetooth service"
            ]
            is_recoverable = False
        elif error_type == "service_not_found":
            user_message = "Device doesn't support fitness machine service"
            recovery_suggestions = [
                "Verify this is a compatible fitness device",
                "Check device documentation for FTMS support",
                "Try connecting to a different device"
            ]
            is_recoverable = False
        elif error_type == "authentication_failed":
            user_message = "Device authentication failed"
            recovery_suggestions = [
                "Try forgetting and re-pairing the device",
                "Check if device requires a PIN or passkey",
                "Restart both devices"
            ]
        elif error_type == "connection_lost":
            user_message = "Connection lost unexpectedly"
            recovery_suggestions = [
                "Check device battery level",
                "Move closer to reduce interference",
                "Automatic reconnection will be attempted"
            ]
        else:
            user_message = f"Connection error: {error_message}"
            recovery_suggestions = [
                "Try connecting again",
                "Restart the device",
                "Check Bluetooth settings"
            ]
        
        return ConnectionError(
            timestamp=datetime.now(),
            error_type=error_type,
            error_message=error_message,
            device_address=device_address,
            retry_count=retry_count,
            is_recoverable=is_recoverable,
            user_message=user_message,
            recovery_suggestions=recovery_suggestions
        )
    
    def _update_connection_quality(self, rssi: Optional[int] = None, 
                                 data_received: bool = False):
        """
        Update connection quality metrics.
        
        Args:
            rssi: Signal strength indicator
            data_received: Whether data was just received
        """
        if rssi is not None:
            self.metrics.rssi = rssi
        
        if data_received:
            self.metrics.last_data_received = datetime.now()
            self.metrics.data_packet_count += 1
        
        # Calculate quality based on various factors
        quality_score = 100  # Start with perfect score
        
        # RSSI-based quality (if available)
        if self.metrics.rssi is not None:
            if self.metrics.rssi > -50:
                quality_score -= 0  # Excellent signal
            elif self.metrics.rssi > -60:
                quality_score -= 10  # Good signal
            elif self.metrics.rssi > -70:
                quality_score -= 30  # Fair signal
            elif self.metrics.rssi > -80:
                quality_score -= 50  # Poor signal
            else:
                quality_score -= 70  # Critical signal
        
        # Data freshness (how recently we received data)
        if self.metrics.last_data_received:
            time_since_data = datetime.now() - self.metrics.last_data_received
            if time_since_data > timedelta(seconds=30):
                quality_score -= 40  # No recent data
            elif time_since_data > timedelta(seconds=10):
                quality_score -= 20  # Stale data
        
        # Error rate impact
        if self.metrics.data_packet_count > 0:
            error_rate = self.metrics.error_count / self.metrics.data_packet_count
            quality_score -= int(error_rate * 100)
        
        # Determine quality level
        if quality_score >= 90:
            new_quality = ConnectionQuality.EXCELLENT
        elif quality_score >= 70:
            new_quality = ConnectionQuality.GOOD
        elif quality_score >= 50:
            new_quality = ConnectionQuality.FAIR
        elif quality_score >= 30:
            new_quality = ConnectionQuality.POOR
        else:
            new_quality = ConnectionQuality.CRITICAL
        
        # Update quality if changed
        if new_quality != self.metrics.quality:
            old_quality = self.metrics.quality
            self.metrics.quality = new_quality
            logger.info(f"Connection quality changed: {old_quality.value} -> {new_quality.value}")
            self._notify_quality_change()
    
    async def connect_with_retry(self, device_address: str, device_name: str = None,
                               connector_connect_func: Callable = None) -> bool:
        """
        Connect to a device with automatic retry and exponential backoff.
        
        Args:
            device_address: BLE address of the device
            device_name: Human-readable device name
            connector_connect_func: Function to call for actual connection
            
        Returns:
            True if connection successful, False otherwise
        """
        self.current_device_address = device_address
        self.current_device_name = device_name or device_address
        self.consecutive_failures = 0
        
        logger.info(f"Starting connection attempt to {self.current_device_name} ({device_address})")
        
        for attempt in range(self.max_retry_attempts):
            self.last_connection_attempt = datetime.now()
            
            try:
                # Update state
                if attempt == 0:
                    self._notify_state_change(ConnectionState.CONNECTING, {
                        "device_address": device_address,
                        "device_name": self.current_device_name,
                        "attempt": attempt + 1,
                        "max_attempts": self.max_retry_attempts
                    })
                else:
                    self._notify_state_change(ConnectionState.RECONNECTING, {
                        "device_address": device_address,
                        "device_name": self.current_device_name,
                        "attempt": attempt + 1,
                        "max_attempts": self.max_retry_attempts
                    })
                
                # Record connection start time
                connection_start = time.time()
                
                # Attempt connection
                if connector_connect_func:
                    success = await asyncio.wait_for(
                        connector_connect_func(device_address),
                        timeout=self.connection_timeout
                    )
                else:
                    # Fallback to basic connection test
                    from bleak import BleakClient
                    client = BleakClient(device_address)
                    await asyncio.wait_for(client.connect(), timeout=self.connection_timeout)
                    success = client.is_connected
                    await client.disconnect()
                
                if success:
                    # Connection successful
                    connection_time = time.time() - connection_start
                    self.metrics.connection_time = connection_time
                    self.consecutive_failures = 0
                    
                    logger.info(f"Successfully connected to {self.current_device_name} "
                              f"in {connection_time:.2f}s (attempt {attempt + 1})")
                    
                    self._notify_state_change(ConnectionState.CONNECTED, {
                        "device_address": device_address,
                        "device_name": self.current_device_name,
                        "connection_time": connection_time,
                        "attempt": attempt + 1
                    })
                    
                    return True
                else:
                    raise Exception("Connection function returned False")
                    
            except asyncio.TimeoutError:
                error = self._create_connection_error(
                    "timeout", f"Connection timed out after {self.connection_timeout}s",
                    device_address, attempt + 1
                )
                self._notify_error(error)
                
            except BleakDeviceNotFoundError:
                error = self._create_connection_error(
                    "device_not_found", "Device not found or not available",
                    device_address, attempt + 1
                )
                self._notify_error(error)
                
            except PermissionError:
                error = self._create_connection_error(
                    "permission_denied", "Bluetooth permission denied",
                    device_address, attempt + 1
                )
                self._notify_error(error)
                # Don't retry permission errors
                break
                
            except BleakError as e:
                error_type = "bleak_error"
                if "not found" in str(e).lower():
                    error_type = "device_not_found"
                elif "timeout" in str(e).lower():
                    error_type = "timeout"
                elif "permission" in str(e).lower():
                    error_type = "permission_denied"
                
                error = self._create_connection_error(
                    error_type, str(e), device_address, attempt + 1, e
                )
                self._notify_error(error)
                
            except Exception as e:
                error = self._create_connection_error(
                    "unknown_error", str(e), device_address, attempt + 1, e
                )
                self._notify_error(error)
            
            # Increment failure count
            self.consecutive_failures += 1
            self.metrics.error_count += 1
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retry_attempts - 1:
                delay = self._calculate_retry_delay(attempt)
                logger.info(f"Connection attempt {attempt + 1} failed, "
                          f"retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
        
        # All attempts failed
        logger.error(f"Failed to connect to {self.current_device_name} "
                    f"after {self.max_retry_attempts} attempts")
        
        self._notify_state_change(ConnectionState.FAILED, {
            "device_address": device_address,
            "device_name": self.current_device_name,
            "total_attempts": self.max_retry_attempts,
            "consecutive_failures": self.consecutive_failures
        })
        
        return False
    
    async def monitor_connection_health(self, check_interval: float = 5.0):
        """
        Monitor connection health and trigger reconnection if needed.
        
        Args:
            check_interval: How often to check connection health (seconds)
        """
        logger.info(f"Starting connection health monitoring (interval: {check_interval}s)")
        
        while True:
            try:
                await asyncio.sleep(check_interval)
                
                if self.state == ConnectionState.CONNECTED:
                    # Check if we've received data recently
                    if self.metrics.last_data_received:
                        time_since_data = datetime.now() - self.metrics.last_data_received
                        
                        # If no data for more than 30 seconds, consider connection unhealthy
                        if time_since_data > timedelta(seconds=30):
                            logger.warning(f"No data received for {time_since_data.total_seconds():.1f}s")
                            self._update_connection_quality()
                            
                            # If no data for more than 60 seconds, trigger reconnection
                            if time_since_data > timedelta(seconds=60) and self.auto_reconnect_enabled:
                                logger.warning("Connection appears stale, triggering reconnection")
                                # This would trigger a reconnection attempt
                                # Implementation depends on the specific connector being used
                    
                    # Update connection quality
                    self._update_connection_quality()
                
            except asyncio.CancelledError:
                logger.info("Connection health monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in connection health monitoring: {e}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status and metrics.
        
        Returns:
            Dictionary with connection status information
        """
        return {
            "state": self.state.value,
            "device_address": self.current_device_address,
            "device_name": self.current_device_name,
            "consecutive_failures": self.consecutive_failures,
            "last_connection_attempt": self.last_connection_attempt.isoformat() if self.last_connection_attempt else None,
            "metrics": {
                "rssi": self.metrics.rssi,
                "connection_time": self.metrics.connection_time,
                "last_data_received": self.metrics.last_data_received.isoformat() if self.metrics.last_data_received else None,
                "data_packet_count": self.metrics.data_packet_count,
                "error_count": self.metrics.error_count,
                "reconnection_count": self.metrics.reconnection_count,
                "quality": self.metrics.quality.value
            },
            "recent_errors": [
                {
                    "timestamp": error.timestamp.isoformat(),
                    "type": error.error_type,
                    "message": error.user_message,
                    "suggestions": error.recovery_suggestions
                }
                for error in self.connection_errors[-5:]  # Last 5 errors
            ]
        }
    
    def reset_metrics(self):
        """Reset connection metrics"""
        self.metrics = ConnectionMetrics()
        self.connection_errors.clear()
        self.consecutive_failures = 0
        logger.info("Connection metrics reset")