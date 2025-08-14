"""
FIT File Analysis and Debugging Tools

This module provides utilities for inspecting FIT files, comparing generated files,
detailed logging for FIT file generation, and compatibility verification.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from fit_tool.fit_file import FitFile
    from fit_tool.profile.messages.file_id_message import FileIdMessage
    from fit_tool.profile.messages.device_info_message import DeviceInfoMessage
    from fit_tool.profile.messages.event_message import EventMessage
    from fit_tool.profile.messages.record_message import RecordMessage
    from fit_tool.profile.messages.lap_message import LapMessage
    from fit_tool.profile.messages.session_message import SessionMessage
    from fit_tool.profile.messages.activity_message import ActivityMessage
except ImportError as e:
    logging.warning(f"FIT tool imports failed: {e}")

logger = logging.getLogger(__name__)

@dataclass
class FITFileInfo:
    """Information about a FIT file"""
    file_path: str
    file_size_bytes: int
    total_messages: int
    message_counts: Dict[str, int]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    sport_type: Optional[str]
    device_manufacturer: Optional[int]
    device_product: Optional[int]
    has_power_data: bool
    has_heart_rate_data: bool
    has_cadence_data: bool
    has_speed_data: bool
    power_range: Optional[Tuple[int, int]]
    heart_rate_range: Optional[Tuple[int, int]]
    cadence_range: Optional[Tuple[int, int]]
    speed_range: Optional[Tuple[float, float]]

@dataclass
class FITComparison:
    """Comparison between two FIT files"""
    file1_info: FITFileInfo
    file2_info: FITFileInfo
    message_count_differences: Dict[str, Tuple[int, int]]
    field_differences: List[Dict[str, Any]]
    compatibility_score: float
    issues: List[str]

class FITAnalyzer:
    """
    FIT file analysis and debugging tool
    """
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize the FIT analyzer
        
        Args:
            debug_mode: Enable detailed debug logging
        """
        self.debug_mode = debug_mode
        if debug_mode:
            logging.getLogger().setLevel(logging.DEBUG)
    
    def analyze_fit_file(self, file_path: str) -> FITFileInfo:
        """
        Analyze a FIT file and extract detailed information
        
        Args:
            file_path: Path to the FIT file
            
        Returns:
            FITFileInfo with detailed analysis
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"FIT file not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        
        try:
            fit_file = FitFile.from_file(file_path)
        except Exception as e:
            logger.error(f"Failed to parse FIT file {file_path}: {e}")
            raise
        
        # Initialize analysis data
        message_counts = {}
        start_time = None
        end_time = None
        sport_type = None
        device_manufacturer = None
        device_product = None
        
        # Data ranges
        power_values = []
        heart_rate_values = []
        cadence_values = []
        speed_values = []
        
        # Analyze messages
        for message in fit_file.messages:
            message_type = type(message).__name__.lower()
            message_counts[message_type] = message_counts.get(message_type, 0) + 1
            
            # Extract timestamps
            if hasattr(message, 'timestamp') and message.timestamp:
                timestamp = self._convert_timestamp(message.timestamp)
                if timestamp:
                    if start_time is None or timestamp < start_time:
                        start_time = timestamp
                    if end_time is None or timestamp > end_time:
                        end_time = timestamp
            
            # Extract device info
            if isinstance(message, FileIdMessage):
                device_manufacturer = getattr(message, 'manufacturer', None)
                device_product = getattr(message, 'product', None)
            
            # Extract sport type
            if hasattr(message, 'sport') and message.sport is not None:
                sport_type = str(message.sport)
            
            # Extract data values for ranges
            if hasattr(message, 'power') and message.power is not None:
                power_values.append(message.power)
            
            if hasattr(message, 'heart_rate') and message.heart_rate is not None:
                heart_rate_values.append(message.heart_rate)
            
            if hasattr(message, 'cadence') and message.cadence is not None:
                cadence_values.append(message.cadence)
            
            if hasattr(message, 'speed') and message.speed is not None:
                speed_values.append(message.speed)
        
        # Calculate duration
        duration_seconds = None
        if start_time and end_time:
            duration_seconds = (end_time - start_time).total_seconds()
        
        # Calculate data ranges
        power_range = (min(power_values), max(power_values)) if power_values else None
        heart_rate_range = (min(heart_rate_values), max(heart_rate_values)) if heart_rate_values else None
        cadence_range = (min(cadence_values), max(cadence_values)) if cadence_values else None
        speed_range = (min(speed_values), max(speed_values)) if speed_values else None
        
        return FITFileInfo(
            file_path=file_path,
            file_size_bytes=file_size,
            total_messages=sum(message_counts.values()),
            message_counts=message_counts,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            sport_type=sport_type,
            device_manufacturer=device_manufacturer,
            device_product=device_product,
            has_power_data=len(power_values) > 0,
            has_heart_rate_data=len(heart_rate_values) > 0,
            has_cadence_data=len(cadence_values) > 0,
            has_speed_data=len(speed_values) > 0,
            power_range=power_range,
            heart_rate_range=heart_rate_range,
            cadence_range=cadence_range,
            speed_range=speed_range
        )
    
    def compare_fit_files(self, file1_path: str, file2_path: str) -> FITComparison:
        """
        Compare two FIT files and identify differences
        
        Args:
            file1_path: Path to first FIT file
            file2_path: Path to second FIT file
            
        Returns:
            FITComparison with detailed comparison
        """
        info1 = self.analyze_fit_file(file1_path)
        info2 = self.analyze_fit_file(file2_path)
        
        # Compare message counts
        message_count_differences = {}
        all_message_types = set(info1.message_counts.keys()) | set(info2.message_counts.keys())
        
        for msg_type in all_message_types:
            count1 = info1.message_counts.get(msg_type, 0)
            count2 = info2.message_counts.get(msg_type, 0)
            if count1 != count2:
                message_count_differences[msg_type] = (count1, count2)
        
        # Compare field values
        field_differences = []
        
        # Compare basic properties
        if info1.sport_type != info2.sport_type:
            field_differences.append({
                'field': 'sport_type',
                'file1_value': info1.sport_type,
                'file2_value': info2.sport_type
            })
        
        if info1.device_manufacturer != info2.device_manufacturer:
            field_differences.append({
                'field': 'device_manufacturer',
                'file1_value': info1.device_manufacturer,
                'file2_value': info2.device_manufacturer
            })
        
        if info1.device_product != info2.device_product:
            field_differences.append({
                'field': 'device_product',
                'file1_value': info1.device_product,
                'file2_value': info2.device_product
            })
        
        # Compare data availability
        data_fields = ['has_power_data', 'has_heart_rate_data', 'has_cadence_data', 'has_speed_data']
        for field in data_fields:
            val1 = getattr(info1, field)
            val2 = getattr(info2, field)
            if val1 != val2:
                field_differences.append({
                    'field': field,
                    'file1_value': val1,
                    'file2_value': val2
                })
        
        # Calculate compatibility score (0-1, higher is more compatible)
        compatibility_score = self._calculate_compatibility_score(info1, info2, message_count_differences, field_differences)
        
        # Generate issues list
        issues = []
        if message_count_differences:
            issues.append(f"Message count differences in {len(message_count_differences)} message types")
        
        if field_differences:
            issues.append(f"Field differences in {len(field_differences)} fields")
        
        if abs(info1.total_messages - info2.total_messages) > 10:
            issues.append(f"Significant difference in total messages: {info1.total_messages} vs {info2.total_messages}")
        
        if info1.duration_seconds and info2.duration_seconds:
            duration_diff = abs(info1.duration_seconds - info2.duration_seconds)
            if duration_diff > 60:  # More than 1 minute difference
                issues.append(f"Significant duration difference: {duration_diff:.1f} seconds")
        
        return FITComparison(
            file1_info=info1,
            file2_info=info2,
            message_count_differences=message_count_differences,
            field_differences=field_differences,
            compatibility_score=compatibility_score,
            issues=issues
        )
    
    def inspect_fit_file(self, file_path: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Detailed inspection of FIT file with message-by-message analysis
        
        Args:
            file_path: Path to FIT file
            output_file: Optional path to save inspection report
            
        Returns:
            Detailed inspection data
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"FIT file not found: {file_path}")
        
        try:
            fit_file = FitFile.from_file(file_path)
        except Exception as e:
            logger.error(f"Failed to parse FIT file {file_path}: {e}")
            raise
        
        inspection_data = {
            'file_info': {
                'path': file_path,
                'size_bytes': os.path.getsize(file_path),
                'analysis_time': datetime.now().isoformat()
            },
            'messages': []
        }
        
        # Inspect each message
        for i, message in enumerate(fit_file.messages):
            message_data = {
                'index': i,
                'type': type(message).__name__,
                'fields': {}
            }
            
            # Extract all available fields
            for attr_name in dir(message):
                if not attr_name.startswith('_') and not callable(getattr(message, attr_name)):
                    try:
                        value = getattr(message, attr_name)
                        if value is not None:
                            # Convert datetime objects to ISO format
                            if isinstance(value, datetime):
                                value = value.isoformat()
                            message_data['fields'][attr_name] = value
                    except Exception as e:
                        logger.debug(f"Error extracting field {attr_name}: {e}")
            
            inspection_data['messages'].append(message_data)
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(inspection_data, f, indent=2, default=str)
            logger.info(f"Inspection report saved to {output_file}")
        
        return inspection_data
    
    def validate_garmin_connect_compatibility(self, file_path: str) -> Dict[str, Any]:
        """
        Validate FIT file for Garmin Connect compatibility
        
        Args:
            file_path: Path to FIT file
            
        Returns:
            Compatibility report
        """
        info = self.analyze_fit_file(file_path)
        
        compatibility_report = {
            'file_path': file_path,
            'is_compatible': True,
            'issues': [],
            'recommendations': [],
            'score': 100
        }
        
        # Check required message types
        required_messages = ['file_id_message', 'activity_message']
        for msg_type in required_messages:
            if msg_type not in info.message_counts:
                compatibility_report['issues'].append(f"Missing required message type: {msg_type}")
                compatibility_report['is_compatible'] = False
                compatibility_report['score'] -= 30
        
        # Check recommended message types
        recommended_messages = ['device_info_message', 'session_message', 'lap_message']
        for msg_type in recommended_messages:
            if msg_type not in info.message_counts:
                compatibility_report['issues'].append(f"Missing recommended message type: {msg_type}")
                compatibility_report['score'] -= 10
        
        # Check for data content
        if not info.has_power_data and not info.has_heart_rate_data:
            compatibility_report['issues'].append("No power or heart rate data - training load calculation may be inaccurate")
            compatibility_report['score'] -= 15
        
        # Check device identification
        if info.device_manufacturer is None:
            compatibility_report['issues'].append("Missing device manufacturer - may affect device recognition")
            compatibility_report['score'] -= 10
        
        if info.device_product is None:
            compatibility_report['issues'].append("Missing device product ID - may affect device recognition")
            compatibility_report['score'] -= 10
        
        # Check sport type
        if info.sport_type is None:
            compatibility_report['issues'].append("Missing sport type - may affect activity categorization")
            compatibility_report['score'] -= 15
        
        # Check duration
        if info.duration_seconds is None or info.duration_seconds < 60:
            compatibility_report['issues'].append("Very short or missing duration - may not be accepted")
            compatibility_report['score'] -= 20
        
        # Generate recommendations
        if compatibility_report['score'] < 100:
            if not info.has_power_data and not info.has_heart_rate_data:
                compatibility_report['recommendations'].append("Add power or heart rate data for better training metrics")
            
            if info.device_manufacturer is None or info.device_product is None:
                compatibility_report['recommendations'].append("Set proper device manufacturer and product IDs")
            
            if info.sport_type is None:
                compatibility_report['recommendations'].append("Set appropriate sport type for activity categorization")
            
            if 'record_message' not in info.message_counts or info.message_counts['record_message'] < 10:
                compatibility_report['recommendations'].append("Include more record messages for detailed activity data")
        
        # Final compatibility determination
        compatibility_report['is_compatible'] = compatibility_report['score'] >= 70
        
        return compatibility_report
    
    def _convert_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Convert FIT timestamp to datetime"""
        try:
            if isinstance(timestamp, (int, float)):
                # FIT timestamps are typically in milliseconds since Unix epoch
                if timestamp > 1e12:  # Milliseconds
                    return datetime.fromtimestamp(timestamp / 1000, timezone.utc)
                else:  # Seconds
                    return datetime.fromtimestamp(timestamp, timezone.utc)
            return None
        except Exception as e:
            logger.debug(f"Error converting timestamp {timestamp}: {e}")
            return None
    
    def _calculate_compatibility_score(self, info1: FITFileInfo, info2: FITFileInfo, 
                                     message_diffs: Dict[str, Tuple[int, int]], 
                                     field_diffs: List[Dict[str, Any]]) -> float:
        """Calculate compatibility score between two FIT files"""
        score = 1.0
        
        # Penalize message count differences
        if message_diffs:
            score -= len(message_diffs) * 0.1
        
        # Penalize field differences
        if field_diffs:
            score -= len(field_diffs) * 0.05
        
        # Penalize significant size differences
        if info1.file_size_bytes > 0 and info2.file_size_bytes > 0:
            size_ratio = min(info1.file_size_bytes, info2.file_size_bytes) / max(info1.file_size_bytes, info2.file_size_bytes)
            if size_ratio < 0.8:
                score -= 0.2
        
        # Penalize duration differences
        if info1.duration_seconds and info2.duration_seconds:
            duration_ratio = min(info1.duration_seconds, info2.duration_seconds) / max(info1.duration_seconds, info2.duration_seconds)
            if duration_ratio < 0.9:
                score -= 0.1
        
        return max(0.0, score)

def print_fit_analysis(info: FITFileInfo):
    """Print formatted FIT file analysis"""
    print("=" * 60)
    print("FIT FILE ANALYSIS")
    print("=" * 60)
    print(f"File: {info.file_path}")
    print(f"Size: {info.file_size_bytes:,} bytes")
    print(f"Total Messages: {info.total_messages}")
    print()
    
    if info.start_time:
        print(f"Start Time: {info.start_time}")
    if info.end_time:
        print(f"End Time: {info.end_time}")
    if info.duration_seconds:
        print(f"Duration: {info.duration_seconds:.1f} seconds ({info.duration_seconds/60:.1f} minutes)")
    print()
    
    if info.sport_type:
        print(f"Sport Type: {info.sport_type}")
    if info.device_manufacturer:
        print(f"Device Manufacturer: {info.device_manufacturer}")
    if info.device_product:
        print(f"Device Product: {info.device_product}")
    print()
    
    print("Data Availability:")
    print(f"  Power: {'✓' if info.has_power_data else '✗'}")
    print(f"  Heart Rate: {'✓' if info.has_heart_rate_data else '✗'}")
    print(f"  Cadence: {'✓' if info.has_cadence_data else '✗'}")
    print(f"  Speed: {'✓' if info.has_speed_data else '✗'}")
    print()
    
    if info.power_range:
        print(f"Power Range: {info.power_range[0]} - {info.power_range[1]} watts")
    if info.heart_rate_range:
        print(f"Heart Rate Range: {info.heart_rate_range[0]} - {info.heart_rate_range[1]} bpm")
    if info.cadence_range:
        print(f"Cadence Range: {info.cadence_range[0]} - {info.cadence_range[1]} rpm")
    if info.speed_range:
        print(f"Speed Range: {info.speed_range[0]:.1f} - {info.speed_range[1]:.1f} m/s")
    print()
    
    print("Message Counts:")
    for msg_type, count in sorted(info.message_counts.items()):
        print(f"  {msg_type}: {count}")
    print("=" * 60)

def print_fit_comparison(comparison: FITComparison):
    """Print formatted FIT file comparison"""
    print("=" * 60)
    print("FIT FILE COMPARISON")
    print("=" * 60)
    print(f"File 1: {comparison.file1_info.file_path}")
    print(f"File 2: {comparison.file2_info.file_path}")
    print(f"Compatibility Score: {comparison.compatibility_score:.2f}")
    print()
    
    if comparison.message_count_differences:
        print("Message Count Differences:")
        for msg_type, (count1, count2) in comparison.message_count_differences.items():
            print(f"  {msg_type}: {count1} vs {count2}")
        print()
    
    if comparison.field_differences:
        print("Field Differences:")
        for diff in comparison.field_differences:
            print(f"  {diff['field']}: {diff['file1_value']} vs {diff['file2_value']}")
        print()
    
    if comparison.issues:
        print("Issues:")
        for issue in comparison.issues:
            print(f"  • {issue}")
    else:
        print("No significant issues found!")
    
    print("=" * 60)

# Command-line interface
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="FIT File Analysis and Debugging Tool")
    parser.add_argument("command", choices=["analyze", "compare", "inspect", "validate"], 
                       help="Command to execute")
    parser.add_argument("file1", help="Path to FIT file")
    parser.add_argument("file2", nargs="?", help="Path to second FIT file (for compare)")
    parser.add_argument("--output", "-o", help="Output file for inspection report")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    analyzer = FITAnalyzer(debug_mode=args.debug)
    
    try:
        if args.command == "analyze":
            info = analyzer.analyze_fit_file(args.file1)
            print_fit_analysis(info)
        
        elif args.command == "compare":
            if not args.file2:
                print("Error: compare command requires two files")
                sys.exit(1)
            comparison = analyzer.compare_fit_files(args.file1, args.file2)
            print_fit_comparison(comparison)
        
        elif args.command == "inspect":
            inspection = analyzer.inspect_fit_file(args.file1, args.output)
            print(f"Inspected {len(inspection['messages'])} messages")
            if args.output:
                print(f"Report saved to {args.output}")
        
        elif args.command == "validate":
            report = analyzer.validate_garmin_connect_compatibility(args.file1)
            print("=" * 60)
            print("GARMIN CONNECT COMPATIBILITY REPORT")
            print("=" * 60)
            print(f"File: {report['file_path']}")
            print(f"Compatible: {'✓' if report['is_compatible'] else '✗'}")
            print(f"Score: {report['score']}/100")
            print()
            
            if report['issues']:
                print("Issues:")
                for issue in report['issues']:
                    print(f"  • {issue}")
                print()
            
            if report['recommendations']:
                print("Recommendations:")
                for rec in report['recommendations']:
                    print(f"  • {rec}")
            
            print("=" * 60)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)