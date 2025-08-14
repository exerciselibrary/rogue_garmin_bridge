"""
Comprehensive FIT File Validation Module

This module provides validation against Garmin FIT SDK specifications,
message type completeness checking, field value range validation,
and automated compatibility testing.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

try:
    from fit_tool.fit_file import FitFile
    from fit_tool.profile.messages.file_id_message import FileIdMessage
    from fit_tool.profile.messages.device_info_message import DeviceInfoMessage
    from fit_tool.profile.messages.event_message import EventMessage
    from fit_tool.profile.messages.record_message import RecordMessage
    from fit_tool.profile.messages.lap_message import LapMessage
    from fit_tool.profile.messages.session_message import SessionMessage
    from fit_tool.profile.messages.activity_message import ActivityMessage
    from fit_tool.profile.profile_type import FileType, Sport, Event, EventType
except ImportError as e:
    logging.warning(f"FIT tool imports failed: {e}")

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    severity: ValidationSeverity
    message: str
    field_name: Optional[str] = None
    message_type: Optional[str] = None
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None

@dataclass
class ValidationResult:
    """Results of FIT file validation"""
    is_valid: bool
    issues: List[ValidationIssue]
    message_counts: Dict[str, int]
    total_messages: int
    file_size_bytes: int
    validation_time_ms: float

class FITValidator:
    """
    Comprehensive FIT file validator
    """
    
    # Required message types for a valid activity FIT file
    REQUIRED_MESSAGE_TYPES = {
        'file_id_message',
        'activity_message'
    }
    
    # Recommended message types for complete activity files
    RECOMMENDED_MESSAGE_TYPES = {
        'device_info_message',
        'event_message',
        'record_message',
        'lap_message',
        'session_message'
    }
    
    # Field value ranges for validation
    FIELD_RANGES = {
        'power': (0, 2000),  # Watts
        'heart_rate': (30, 250),  # BPM
        'cadence': (0, 300),  # RPM
        'speed': (0, 100),  # m/s (360 km/h max)
        'distance': (0, 1000000),  # meters (1000 km max)
        'temperature': (-40, 60),  # Celsius
        'altitude': (-500, 9000),  # meters
        'calories': (0, 10000),  # kcal
        'total_elapsed_time': (0, 86400),  # seconds (24 hours max)
        'total_timer_time': (0, 86400),  # seconds
    }
    
    def __init__(self):
        """Initialize the FIT validator"""
        self.validation_start_time = None
    
    def validate_fit_file(self, file_path: str) -> ValidationResult:
        """
        Validate a FIT file comprehensively
        
        Args:
            file_path: Path to the FIT file to validate
            
        Returns:
            ValidationResult with validation details
        """
        self.validation_start_time = datetime.now()
        issues = []
        message_counts = {}
        total_messages = 0
        file_size = 0
        
        try:
            # Check file existence and size
            if not os.path.exists(file_path):
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    f"FIT file does not exist: {file_path}"
                ))
                return self._create_result(False, issues, message_counts, total_messages, file_size)
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    "FIT file is empty"
                ))
                return self._create_result(False, issues, message_counts, total_messages, file_size)
            
            # Load and parse FIT file
            try:
                fit_file = FitFile.from_file(file_path)
            except Exception as e:
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    f"Failed to parse FIT file: {str(e)}"
                ))
                return self._create_result(False, issues, message_counts, total_messages, file_size)
            
            # Count messages by type
            for message in fit_file.messages:
                message_type = type(message).__name__.lower()
                message_counts[message_type] = message_counts.get(message_type, 0) + 1
                total_messages += 1
            
            # Validate message type completeness
            issues.extend(self._validate_message_completeness(message_counts))
            
            # Validate individual messages
            issues.extend(self._validate_messages(fit_file.messages))
            
            # Validate message sequence and consistency
            issues.extend(self._validate_message_sequence(fit_file.messages))
            
            # Validate field value ranges
            issues.extend(self._validate_field_ranges(fit_file.messages))
            
            # Validate timestamps
            issues.extend(self._validate_timestamps(fit_file.messages))
            
            # Check for Garmin Connect compatibility
            issues.extend(self._validate_garmin_compatibility(fit_file.messages))
            
        except Exception as e:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                f"Unexpected validation error: {str(e)}"
            ))
        
        # Determine overall validity
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in issues)
        is_valid = not has_errors
        
        return self._create_result(is_valid, issues, message_counts, total_messages, file_size)
    
    def _create_result(self, is_valid: bool, issues: List[ValidationIssue], 
                      message_counts: Dict[str, int], total_messages: int, 
                      file_size: int) -> ValidationResult:
        """Create validation result with timing"""
        validation_time = (datetime.now() - self.validation_start_time).total_seconds() * 1000
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            message_counts=message_counts,
            total_messages=total_messages,
            file_size_bytes=file_size,
            validation_time_ms=validation_time
        )
    
    def _validate_message_completeness(self, message_counts: Dict[str, int]) -> List[ValidationIssue]:
        """Validate that required message types are present"""
        issues = []
        
        # Check required messages
        for required_type in self.REQUIRED_MESSAGE_TYPES:
            if required_type not in message_counts:
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    f"Missing required message type: {required_type}",
                    message_type=required_type
                ))
        
        # Check recommended messages
        for recommended_type in self.RECOMMENDED_MESSAGE_TYPES:
            if recommended_type not in message_counts:
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    f"Missing recommended message type: {recommended_type}",
                    message_type=recommended_type
                ))
        
        # Check for reasonable message counts
        if message_counts.get('record_message', 0) == 0:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "No record messages found - file may not contain workout data"
            ))
        elif message_counts.get('record_message', 0) < 10:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                f"Very few record messages ({message_counts['record_message']}) - workout may be too short"
            ))
        
        return issues
    
    def _validate_messages(self, messages: List[Any]) -> List[ValidationIssue]:
        """Validate individual message content"""
        issues = []
        
        for message in messages:
            message_type = type(message).__name__
            
            # Validate FileIdMessage
            if isinstance(message, FileIdMessage):
                issues.extend(self._validate_file_id_message(message))
            
            # Validate DeviceInfoMessage
            elif hasattr(message, '__class__') and 'DeviceInfoMessage' in message.__class__.__name__:
                issues.extend(self._validate_device_info_message(message))
            
            # Validate RecordMessage
            elif hasattr(message, '__class__') and 'RecordMessage' in message.__class__.__name__:
                issues.extend(self._validate_record_message(message))
            
            # Validate SessionMessage
            elif hasattr(message, '__class__') and 'SessionMessage' in message.__class__.__name__:
                issues.extend(self._validate_session_message(message))
            
            # Validate ActivityMessage
            elif hasattr(message, '__class__') and 'ActivityMessage' in message.__class__.__name__:
                issues.extend(self._validate_activity_message(message))
        
        return issues
    
    def _validate_file_id_message(self, message: FileIdMessage) -> List[ValidationIssue]:
        """Validate FileIdMessage content"""
        issues = []
        
        # Check file type
        if not hasattr(message, 'type') or message.type != FileType.ACTIVITY:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "FileIdMessage must have type ACTIVITY",
                field_name='type',
                message_type='FileIdMessage',
                expected_value=FileType.ACTIVITY,
                actual_value=getattr(message, 'type', None)
            ))
        
        # Check manufacturer
        if not hasattr(message, 'manufacturer') or message.manufacturer is None:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "FileIdMessage missing manufacturer",
                field_name='manufacturer',
                message_type='FileIdMessage'
            ))
        
        # Check product
        if not hasattr(message, 'product') or message.product is None:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "FileIdMessage missing product",
                field_name='product',
                message_type='FileIdMessage'
            ))
        
        # Check time_created
        if not hasattr(message, 'time_created') or message.time_created is None:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "FileIdMessage missing time_created",
                field_name='time_created',
                message_type='FileIdMessage'
            ))
        
        return issues
    
    def _validate_device_info_message(self, message: Any) -> List[ValidationIssue]:
        """Validate DeviceInfoMessage content"""
        issues = []
        
        # Check timestamp
        if not hasattr(message, 'timestamp') or message.timestamp is None:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "DeviceInfoMessage missing timestamp",
                field_name='timestamp',
                message_type='DeviceInfoMessage'
            ))
        
        # Check manufacturer consistency with FileId
        if hasattr(message, 'manufacturer') and message.manufacturer is None:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "DeviceInfoMessage missing manufacturer",
                field_name='manufacturer',
                message_type='DeviceInfoMessage'
            ))
        
        return issues
    
    def _validate_record_message(self, message: Any) -> List[ValidationIssue]:
        """Validate RecordMessage content"""
        issues = []
        
        # Check timestamp
        if not hasattr(message, 'timestamp') or message.timestamp is None:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "RecordMessage missing timestamp",
                field_name='timestamp',
                message_type='RecordMessage'
            ))
        
        # Check for at least one data field
        data_fields = ['power', 'heart_rate', 'cadence', 'speed', 'distance']
        has_data = any(hasattr(message, field) and getattr(message, field) is not None 
                      for field in data_fields)
        
        if not has_data:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "RecordMessage has no data fields",
                message_type='RecordMessage'
            ))
        
        return issues
    
    def _validate_session_message(self, message: Any) -> List[ValidationIssue]:
        """Validate SessionMessage content"""
        issues = []
        
        # Check required fields
        required_fields = ['timestamp', 'start_time', 'total_elapsed_time']
        for field in required_fields:
            if not hasattr(message, field) or getattr(message, field) is None:
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    f"SessionMessage missing required field: {field}",
                    field_name=field,
                    message_type='SessionMessage'
                ))
        
        # Check sport type
        if hasattr(message, 'sport') and message.sport is None:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "SessionMessage missing sport type",
                field_name='sport',
                message_type='SessionMessage'
            ))
        
        return issues
    
    def _validate_activity_message(self, message: Any) -> List[ValidationIssue]:
        """Validate ActivityMessage content"""
        issues = []
        
        # Check timestamp
        if not hasattr(message, 'timestamp') or message.timestamp is None:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "ActivityMessage missing timestamp",
                field_name='timestamp',
                message_type='ActivityMessage'
            ))
        
        # Check activity type
        if not hasattr(message, 'type') or message.type is None:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "ActivityMessage missing activity type",
                field_name='type',
                message_type='ActivityMessage'
            ))
        
        return issues
    
    def _validate_message_sequence(self, messages: List[Any]) -> List[ValidationIssue]:
        """Validate message sequence and consistency"""
        issues = []
        
        # Check that FileId comes first
        if messages and not isinstance(messages[0], FileIdMessage):
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "FileIdMessage must be the first message"
            ))
        
        # Check timestamp ordering in record messages
        record_timestamps = []
        for message in messages:
            if hasattr(message, '__class__') and 'RecordMessage' in message.__class__.__name__:
                if hasattr(message, 'timestamp') and message.timestamp is not None:
                    record_timestamps.append(message.timestamp)
        
        # Verify timestamps are in ascending order
        for i in range(1, len(record_timestamps)):
            if record_timestamps[i] < record_timestamps[i-1]:
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    f"Record timestamps not in ascending order at position {i}"
                ))
                break
        
        return issues
    
    def _validate_field_ranges(self, messages: List[Any]) -> List[ValidationIssue]:
        """Validate field value ranges"""
        issues = []
        
        for message in messages:
            message_type = type(message).__name__
            
            for field_name, (min_val, max_val) in self.FIELD_RANGES.items():
                if hasattr(message, field_name):
                    value = getattr(message, field_name)
                    if value is not None and (value < min_val or value > max_val):
                        issues.append(ValidationIssue(
                            ValidationSeverity.WARNING,
                            f"Field {field_name} value {value} outside expected range [{min_val}, {max_val}]",
                            field_name=field_name,
                            message_type=message_type,
                            expected_value=f"[{min_val}, {max_val}]",
                            actual_value=value
                        ))
        
        return issues
    
    def _validate_timestamps(self, messages: List[Any]) -> List[ValidationIssue]:
        """Validate timestamp consistency and reasonableness"""
        issues = []
        
        timestamps = []
        for message in messages:
            if hasattr(message, 'timestamp') and message.timestamp is not None:
                timestamps.append(message.timestamp)
        
        if not timestamps:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "No valid timestamps found in file"
            ))
            return issues
        
        # Check for reasonable timestamp values (not too far in past/future)
        current_time_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        one_year_ms = 365 * 24 * 60 * 60 * 1000
        
        for timestamp in timestamps:
            if timestamp < (current_time_ms - one_year_ms):
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    f"Timestamp {timestamp} is more than a year in the past"
                ))
                break
            elif timestamp > (current_time_ms + one_year_ms):
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    f"Timestamp {timestamp} is more than a year in the future"
                ))
                break
        
        return issues
    
    def _validate_garmin_compatibility(self, messages: List[Any]) -> List[ValidationIssue]:
        """Validate Garmin Connect compatibility requirements"""
        issues = []
        
        # Check for proper device identification
        has_device_info = any(hasattr(msg, '__class__') and 'DeviceInfoMessage' in msg.__class__.__name__ 
                             for msg in messages)
        
        if not has_device_info:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "Missing DeviceInfoMessage - may affect Garmin Connect compatibility"
            ))
        
        # Check for proper sport/activity type mapping
        session_messages = [msg for msg in messages 
                           if hasattr(msg, '__class__') and 'SessionMessage' in msg.__class__.__name__]
        
        for session_msg in session_messages:
            if hasattr(session_msg, 'sport') and session_msg.sport is None:
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "SessionMessage missing sport type - may affect activity categorization in Garmin Connect"
                ))
        
        # Check for training load calculation fields
        has_power_data = any(hasattr(msg, 'power') and getattr(msg, 'power') is not None 
                            for msg in messages)
        has_hr_data = any(hasattr(msg, 'heart_rate') and getattr(msg, 'heart_rate') is not None 
                         for msg in messages)
        
        if not has_power_data and not has_hr_data:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "No power or heart rate data found - training load calculation may be inaccurate"
            ))
        
        return issues
    
    def validate_against_reference(self, file_path: str, reference_file_path: str) -> ValidationResult:
        """
        Validate a FIT file against a reference file
        
        Args:
            file_path: Path to the FIT file to validate
            reference_file_path: Path to the reference FIT file
            
        Returns:
            ValidationResult with comparison details
        """
        self.validation_start_time = datetime.now()
        issues = []
        
        try:
            # Load both files
            fit_file = FitFile.from_file(file_path)
            ref_file = FitFile.from_file(reference_file_path)
            
            # Compare message counts
            file_counts = {}
            ref_counts = {}
            
            for message in fit_file.messages:
                msg_type = type(message).__name__
                file_counts[msg_type] = file_counts.get(msg_type, 0) + 1
            
            for message in ref_file.messages:
                msg_type = type(message).__name__
                ref_counts[msg_type] = ref_counts.get(msg_type, 0) + 1
            
            # Check for missing message types
            for msg_type in ref_counts:
                if msg_type not in file_counts:
                    issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        f"Message type {msg_type} present in reference but missing in file"
                    ))
                elif file_counts[msg_type] != ref_counts[msg_type]:
                    issues.append(ValidationIssue(
                        ValidationSeverity.INFO,
                        f"Message count difference for {msg_type}: file={file_counts[msg_type]}, reference={ref_counts[msg_type]}"
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                f"Error comparing with reference file: {str(e)}"
            ))
        
        return self._create_result(len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
                                 issues, file_counts, sum(file_counts.values()), 
                                 os.path.getsize(file_path))

def validate_fit_file(file_path: str) -> ValidationResult:
    """
    Convenience function to validate a FIT file
    
    Args:
        file_path: Path to the FIT file to validate
        
    Returns:
        ValidationResult with validation details
    """
    validator = FITValidator()
    return validator.validate_fit_file(file_path)

def print_validation_report(result: ValidationResult, file_path: str = None):
    """
    Print a formatted validation report
    
    Args:
        result: ValidationResult to report
        file_path: Optional file path for the report header
    """
    print("=" * 60)
    print("FIT FILE VALIDATION REPORT")
    print("=" * 60)
    
    if file_path:
        print(f"File: {file_path}")
    
    print(f"Valid: {'✓' if result.is_valid else '✗'}")
    print(f"File Size: {result.file_size_bytes:,} bytes")
    print(f"Total Messages: {result.total_messages}")
    print(f"Validation Time: {result.validation_time_ms:.1f} ms")
    print()
    
    if result.message_counts:
        print("Message Counts:")
        for msg_type, count in sorted(result.message_counts.items()):
            print(f"  {msg_type}: {count}")
        print()
    
    if result.issues:
        print("Issues Found:")
        errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in result.issues if i.severity == ValidationSeverity.WARNING]
        infos = [i for i in result.issues if i.severity == ValidationSeverity.INFO]
        
        if errors:
            print(f"  ERRORS ({len(errors)}):")
            for issue in errors:
                print(f"    ✗ {issue.message}")
        
        if warnings:
            print(f"  WARNINGS ({len(warnings)}):")
            for issue in warnings:
                print(f"    ⚠ {issue.message}")
        
        if infos:
            print(f"  INFO ({len(infos)}):")
            for issue in infos:
                print(f"    ℹ {issue.message}")
    else:
        print("No issues found!")
    
    print("=" * 60)

# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fit_validator.py <fit_file_path> [reference_file_path]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        # Compare with reference file
        reference_path = sys.argv[2]
        validator = FITValidator()
        result = validator.validate_against_reference(file_path, reference_path)
        print_validation_report(result, file_path)
    else:
        # Standard validation
        result = validate_fit_file(file_path)
        print_validation_report(result, file_path)