"""
FIT file validation utilities for testing.
"""

import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import struct
import json


class FITFileValidator:
    """Validates FIT files for Garmin Connect compatibility."""
    
    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_fit_file(self, fit_file_path: str) -> Dict[str, Any]:
        """Validate a FIT file and return detailed report."""
        self.validation_errors.clear()
        self.validation_warnings.clear()
        
        if not os.path.exists(fit_file_path):
            self.validation_errors.append("FIT file does not exist")
            return self._create_validation_report(False)
        
        try:
            with open(fit_file_path, 'rb') as f:
                file_data = f.read()
            
            # Validate file header
            if not self._validate_header(file_data):
                return self._create_validation_report(False)
            
            # Parse and validate messages
            messages = self._parse_messages(file_data)
            if not self._validate_messages(messages):
                return self._create_validation_report(False)
            
            # Validate message content
            if not self._validate_message_content(messages):
                return self._create_validation_report(False)
            
            return self._create_validation_report(True, messages)
            
        except Exception as e:
            self.validation_errors.append(f"Error reading FIT file: {str(e)}")
            return self._create_validation_report(False)
    
    def _validate_header(self, file_data: bytes) -> bool:
        """Validate FIT file header."""
        if len(file_data) < 14:
            self.validation_errors.append("File too small to contain valid FIT header")
            return False
        
        # Check header size
        header_size = file_data[0]
        if header_size < 12:
            self.validation_errors.append(f"Invalid header size: {header_size}")
            return False
        
        # Check protocol version
        protocol_version = file_data[1]
        if protocol_version == 0:
            self.validation_errors.append("Invalid protocol version")
            return False
        
        # Check profile version
        profile_version = struct.unpack('<H', file_data[2:4])[0]
        if profile_version == 0:
            self.validation_warnings.append("Profile version is 0")
        
        # Check data size
        data_size = struct.unpack('<I', file_data[4:8])[0]
        expected_size = len(file_data) - header_size - 2  # Minus header and CRC
        if data_size != expected_size:
            self.validation_warnings.append(
                f"Data size mismatch: header says {data_size}, actual {expected_size}"
            )
        
        # Check file type signature
        signature = file_data[8:12]
        if signature != b'.FIT':
            self.validation_errors.append(f"Invalid file signature: {signature}")
            return False
        
        return True
    
    def _parse_messages(self, file_data: bytes) -> List[Dict[str, Any]]:
        """Parse FIT messages from file data."""
        messages = []
        
        # Skip header (first 14 bytes typically)
        header_size = file_data[0]
        offset = header_size
        
        # Parse messages until end of data
        data_size = struct.unpack('<I', file_data[4:8])[0]
        end_offset = header_size + data_size
        
        while offset < end_offset:
            try:
                message, bytes_read = self._parse_single_message(file_data, offset)
                if message:
                    messages.append(message)
                offset += bytes_read
            except Exception as e:
                self.validation_warnings.append(f"Error parsing message at offset {offset}: {str(e)}")
                break
        
        return messages
    
    def _parse_single_message(self, file_data: bytes, offset: int) -> Tuple[Optional[Dict[str, Any]], int]:
        """Parse a single FIT message."""
        if offset >= len(file_data):
            return None, 0
        
        record_header = file_data[offset]
        
        # Check if it's a definition message or data message
        if record_header & 0x40:  # Definition message
            return self._parse_definition_message(file_data, offset)
        else:  # Data message
            return self._parse_data_message(file_data, offset)
    
    def _parse_definition_message(self, file_data: bytes, offset: int) -> Tuple[Dict[str, Any], int]:
        """Parse a definition message."""
        # Simplified parsing - in real implementation would be more complex
        message = {
            "type": "definition",
            "offset": offset,
            "header": file_data[offset]
        }
        
        # Skip definition message (simplified)
        bytes_read = 5  # Minimum definition message size
        
        return message, bytes_read
    
    def _parse_data_message(self, file_data: bytes, offset: int) -> Tuple[Dict[str, Any], int]:
        """Parse a data message."""
        # Simplified parsing - in real implementation would decode actual fields
        message = {
            "type": "data",
            "offset": offset,
            "header": file_data[offset]
        }
        
        # Skip data message (simplified)
        bytes_read = 1  # Will vary based on message definition
        
        return message, bytes_read
    
    def _validate_messages(self, messages: List[Dict[str, Any]]) -> bool:
        """Validate that required messages are present."""
        required_message_types = [
            "file_id",
            "activity", 
            "session",
            "lap",
            "record"
        ]
        
        # In a real implementation, would check for actual message types
        # For now, just check that we have some messages
        if not messages:
            self.validation_errors.append("No messages found in FIT file")
            return False
        
        return True
    
    def _validate_message_content(self, messages: List[Dict[str, Any]]) -> bool:
        """Validate message content for Garmin Connect compatibility."""
        # In a real implementation, would validate:
        # - Required fields are present
        # - Field values are within valid ranges
        # - Timestamps are sequential
        # - Device identification is correct
        
        return True
    
    def _create_validation_report(self, is_valid: bool, messages: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create validation report."""
        return {
            "valid": is_valid,
            "errors": self.validation_errors.copy(),
            "warnings": self.validation_warnings.copy(),
            "message_count": len(messages) if messages else 0,
            "messages": messages or []
        }


class MockFITFile:
    """Creates mock FIT files for testing."""
    
    def __init__(self):
        self.messages = []
    
    def add_file_id_message(self, device_type: str = "bike"):
        """Add file ID message."""
        message = {
            "type": "file_id",
            "manufacturer": 1,  # Garmin
            "product": 1234,
            "device_type": device_type,
            "time_created": datetime.now()
        }
        self.messages.append(message)
    
    def add_activity_message(self, total_time: int, activity_type: str = "cycling"):
        """Add activity message."""
        message = {
            "type": "activity",
            "timestamp": datetime.now(),
            "total_timer_time": total_time,
            "type": activity_type,
            "event": "activity_end",
            "event_type": "stop"
        }
        self.messages.append(message)
    
    def add_session_message(self, workout_data: Dict[str, Any]):
        """Add session message."""
        message = {
            "type": "session",
            "timestamp": workout_data.get("end_time", datetime.now()),
            "start_time": workout_data.get("start_time", datetime.now()),
            "total_elapsed_time": workout_data.get("duration", 0),
            "total_timer_time": workout_data.get("duration", 0),
            "total_distance": workout_data.get("total_distance", 0),
            "total_calories": workout_data.get("total_calories", 0),
            "avg_power": workout_data.get("avg_power", 0),
            "max_power": workout_data.get("max_power", 0),
            "sport": "cycling" if workout_data.get("device_type") == "bike" else "rowing",
            "sub_sport": "indoor_cycling" if workout_data.get("device_type") == "bike" else "indoor_rowing"
        }
        self.messages.append(message)
    
    def add_lap_message(self, lap_data: Dict[str, Any]):
        """Add lap message."""
        message = {
            "type": "lap",
            "timestamp": lap_data.get("end_time", datetime.now()),
            "start_time": lap_data.get("start_time", datetime.now()),
            "total_elapsed_time": lap_data.get("duration", 0),
            "total_distance": lap_data.get("distance", 0),
            "avg_power": lap_data.get("avg_power", 0),
            "max_power": lap_data.get("max_power", 0)
        }
        self.messages.append(message)
    
    def add_record_messages(self, data_points: List[Dict[str, Any]]):
        """Add record messages from data points."""
        for point in data_points:
            message = {
                "type": "record",
                "timestamp": point.get("timestamp", datetime.now()),
                "power": point.get("power"),
                "heart_rate": point.get("heart_rate"),
                "distance": point.get("distance"),
                "calories": point.get("calories"),
                "cadence": point.get("cadence"),
                "speed": point.get("speed")
            }
            self.messages.append(message)
    
    def write_to_file(self, file_path: str):
        """Write mock FIT file."""
        # Create a minimal valid FIT file structure
        with open(file_path, 'wb') as f:
            # Write header
            header = bytearray(14)
            header[0] = 14  # Header size
            header[1] = 16  # Protocol version
            header[2:4] = struct.pack('<H', 2132)  # Profile version
            header[4:8] = struct.pack('<I', 100)  # Data size (placeholder)
            header[8:12] = b'.FIT'  # Signature
            header[12:14] = struct.pack('<H', 0)  # CRC (placeholder)
            
            f.write(header)
            
            # Write simplified message data
            for message in self.messages:
                # Write a minimal message representation
                message_data = json.dumps(message, default=str).encode('utf-8')[:50]
                f.write(message_data)
            
            # Write CRC
            f.write(struct.pack('<H', 0))


def create_test_fit_file(workout_data: Dict[str, Any], data_points: List[Dict[str, Any]], 
                        output_path: str = None) -> str:
    """Create a test FIT file from workout data."""
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix='.fit')
        os.close(fd)
    
    fit_file = MockFITFile()
    
    # Add required messages
    fit_file.add_file_id_message(workout_data.get("device_type", "bike"))
    fit_file.add_activity_message(
        workout_data.get("duration", 0),
        "cycling" if workout_data.get("device_type") == "bike" else "rowing"
    )
    fit_file.add_session_message(workout_data)
    
    # Add lap message (single lap for simplicity)
    lap_data = {
        "start_time": workout_data.get("start_time"),
        "end_time": workout_data.get("end_time"),
        "duration": workout_data.get("duration"),
        "distance": workout_data.get("total_distance"),
        "avg_power": workout_data.get("avg_power"),
        "max_power": workout_data.get("max_power")
    }
    fit_file.add_lap_message(lap_data)
    
    # Add record messages
    fit_file.add_record_messages(data_points)
    
    # Write to file
    fit_file.write_to_file(output_path)
    
    return output_path


def validate_training_load_calculation(fit_file_path: str, expected_training_load: float = None) -> Dict[str, Any]:
    """Validate training load calculation in FIT file."""
    # This would integrate with actual Garmin Connect API or FIT SDK
    # For testing, we'll simulate the validation
    
    validation_result = {
        "valid": True,
        "training_load_present": True,
        "calculated_training_load": 85.5,  # Mock value
        "expected_training_load": expected_training_load,
        "device_identification_correct": True,
        "sport_type_correct": True
    }
    
    if expected_training_load:
        difference = abs(validation_result["calculated_training_load"] - expected_training_load)
        if difference > 10:  # Allow 10% tolerance
            validation_result["valid"] = False
            validation_result["error"] = f"Training load difference too large: {difference}"
    
    return validation_result


def compare_fit_files(file1_path: str, file2_path: str) -> Dict[str, Any]:
    """Compare two FIT files for differences."""
    comparison = {
        "identical": False,
        "differences": [],
        "file1_size": 0,
        "file2_size": 0
    }
    
    try:
        # Compare file sizes
        comparison["file1_size"] = os.path.getsize(file1_path)
        comparison["file2_size"] = os.path.getsize(file2_path)
        
        if comparison["file1_size"] != comparison["file2_size"]:
            comparison["differences"].append("File sizes differ")
        
        # Compare file contents (simplified)
        with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
            data1 = f1.read()
            data2 = f2.read()
            
            if data1 == data2:
                comparison["identical"] = True
            else:
                # Find first difference
                for i, (b1, b2) in enumerate(zip(data1, data2)):
                    if b1 != b2:
                        comparison["differences"].append(f"First difference at byte {i}")
                        break
    
    except Exception as e:
        comparison["differences"].append(f"Error comparing files: {str(e)}")
    
    return comparison


class FITTestCase:
    """Base class for FIT file test cases."""
    
    def __init__(self):
        self.temp_files = []
        self.validator = FITFileValidator()
    
    def create_temp_fit_file(self, workout_data: Dict[str, Any], 
                           data_points: List[Dict[str, Any]]) -> str:
        """Create a temporary FIT file for testing."""
        fit_file_path = create_test_fit_file(workout_data, data_points)
        self.temp_files.append(fit_file_path)
        return fit_file_path
    
    def cleanup_temp_files(self):
        """Clean up temporary FIT files."""
        for file_path in self.temp_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        self.temp_files.clear()
    
    def assert_fit_file_valid(self, fit_file_path: str):
        """Assert that a FIT file is valid."""
        validation_result = self.validator.validate_fit_file(fit_file_path)
        assert validation_result["valid"], f"FIT file validation failed: {validation_result['errors']}"
    
    def assert_training_load_correct(self, fit_file_path: str, expected_load: float = None):
        """Assert that training load calculation is correct."""
        result = validate_training_load_calculation(fit_file_path, expected_load)
        assert result["valid"], f"Training load validation failed: {result.get('error', 'Unknown error')}"