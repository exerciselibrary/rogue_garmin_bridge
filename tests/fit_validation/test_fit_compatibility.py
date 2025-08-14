"""
Test Suite for FIT File Compatibility Verification

This module provides automated tests to verify FIT file compatibility
with Garmin Connect and other fitness platforms.
"""

import pytest
import os
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any

from src.fit.fit_converter import FITConverter
from src.fit.fit_analyzer import FITAnalyzer
from src.fit.fit_validator import validate_fit_file, ValidationSeverity

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestFITCompatibility:
    """Test FIT file compatibility with various scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.converter = FITConverter(output_dir=self.temp_dir)
        self.analyzer = FITAnalyzer(debug_mode=True)
    
    def teardown_method(self):
        """Clean up test fixtures"""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_sample_workout_data(self, workout_type: str = "bike", duration_minutes: int = 20) -> Dict[str, Any]:
        """Create sample workout data for testing"""
        from datetime import datetime, timedelta, timezone
        
        start_time = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)
        num_points = duration_minutes * 60  # 1 point per second
        
        # Generate realistic data patterns
        data_points = []
        for i in range(num_points):
            timestamp = start_time + timedelta(seconds=i)
            
            # Simulate workout progression
            progress = i / num_points
            intensity = 0.3 + 0.4 * (1 - abs(progress - 0.5) * 2)  # Bell curve intensity
            
            if workout_type == "bike":
                power = int(100 + intensity * 200)  # 100-300W
                cadence = int(60 + intensity * 40)   # 60-100 RPM
                speed = 15 + intensity * 15          # 15-30 km/h
            else:  # rower
                power = int(80 + intensity * 150)    # 80-230W
                cadence = int(20 + intensity * 15)   # 20-35 SPM (stroke rate)
                speed = 3 + intensity * 3            # 3-6 m/s
            
            heart_rate = int(120 + intensity * 60)   # 120-180 BPM
            distance = i * (speed / 3.6)             # Cumulative distance in meters
            
            data_points.append({
                'timestamp': timestamp.isoformat(),
                'power': power,
                'cadence': cadence,
                'speed': speed,
                'heart_rate': heart_rate,
                'distance': distance
            })
        
        return {
            'workout_type': workout_type,
            'start_time': start_time.isoformat(),
            'total_duration': duration_minutes * 60,
            'total_distance': data_points[-1]['distance'] if data_points else 0,
            'total_calories': int(duration_minutes * 10),  # Rough estimate
            'avg_power': sum(p['power'] for p in data_points) // len(data_points),
            'max_power': max(p['power'] for p in data_points),
            'avg_heart_rate': sum(p['heart_rate'] for p in data_points) // len(data_points),
            'max_heart_rate': max(p['heart_rate'] for p in data_points),
            'avg_cadence': sum(p['cadence'] for p in data_points) // len(data_points),
            'max_cadence': max(p['cadence'] for p in data_points),
            'avg_speed': sum(p['speed'] for p in data_points) / len(data_points),
            'max_speed': max(p['speed'] for p in data_points),
            'data_series': {
                'absolute_timestamps': [p['timestamp'] for p in data_points],
                'powers': [p['power'] for p in data_points],
                'cadences': [p['cadence'] for p in data_points],
                'speeds': [p['speed'] for p in data_points],
                'heart_rates': [p['heart_rate'] for p in data_points],
                'distances': [p['distance'] for p in data_points]
            }
        }
    
    def test_bike_workout_compatibility(self):
        """Test bike workout FIT file compatibility"""
        workout_data = self.create_sample_workout_data("bike", 30)
        
        # Generate FIT file
        fit_file_path = self.converter.convert_workout(workout_data)
        assert fit_file_path is not None
        assert os.path.exists(fit_file_path)
        
        # Validate the file
        validation_result = validate_fit_file(fit_file_path)
        
        # Should be valid or have only warnings
        errors = [issue for issue in validation_result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"FIT file has validation errors: {[e.message for e in errors]}"
        
        # Analyze the file
        analysis = self.analyzer.analyze_fit_file(fit_file_path)
        
        # Check basic properties
        assert analysis.has_power_data
        assert analysis.has_heart_rate_data
        assert analysis.has_cadence_data
        assert analysis.has_speed_data
        assert analysis.duration_seconds > 1500  # At least 25 minutes
        
        # Check Garmin Connect compatibility
        compatibility = self.analyzer.validate_garmin_connect_compatibility(fit_file_path)
        assert compatibility['is_compatible'], f"Not Garmin Connect compatible: {compatibility['issues']}"
        assert compatibility['score'] >= 80, f"Low compatibility score: {compatibility['score']}"
    
    def test_rower_workout_compatibility(self):
        """Test rower workout FIT file compatibility"""
        workout_data = self.create_sample_workout_data("rower", 25)
        
        # Generate FIT file
        fit_file_path = self.converter.convert_workout(workout_data)
        assert fit_file_path is not None
        assert os.path.exists(fit_file_path)
        
        # Validate the file
        validation_result = validate_fit_file(fit_file_path)
        
        # Should be valid or have only warnings
        errors = [issue for issue in validation_result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"FIT file has validation errors: {[e.message for e in errors]}"
        
        # Analyze the file
        analysis = self.analyzer.analyze_fit_file(fit_file_path)
        
        # Check basic properties
        assert analysis.has_power_data
        assert analysis.has_heart_rate_data
        assert analysis.has_cadence_data  # Stroke rate
        assert analysis.duration_seconds > 1200  # At least 20 minutes
        
        # Check Garmin Connect compatibility
        compatibility = self.analyzer.validate_garmin_connect_compatibility(fit_file_path)
        assert compatibility['is_compatible'], f"Not Garmin Connect compatible: {compatibility['issues']}"
        assert compatibility['score'] >= 80, f"Low compatibility score: {compatibility['score']}"
    
    def test_short_workout_compatibility(self):
        """Test short workout FIT file compatibility"""
        workout_data = self.create_sample_workout_data("bike", 5)  # 5 minute workout
        
        # Generate FIT file
        fit_file_path = self.converter.convert_workout(workout_data)
        assert fit_file_path is not None
        assert os.path.exists(fit_file_path)
        
        # Validate the file
        validation_result = validate_fit_file(fit_file_path)
        
        # Should be valid (short workouts are still valid)
        errors = [issue for issue in validation_result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"FIT file has validation errors: {[e.message for e in errors]}"
        
        # Check Garmin Connect compatibility (may have warnings for short duration)
        compatibility = self.analyzer.validate_garmin_connect_compatibility(fit_file_path)
        # Short workouts may have lower compatibility scores but should still be processable
        assert compatibility['score'] >= 50, f"Very low compatibility score: {compatibility['score']}"
    
    def test_minimal_data_compatibility(self):
        """Test FIT file with minimal data compatibility"""
        # Create workout with minimal data (no heart rate, limited power)
        workout_data = self.create_sample_workout_data("bike", 15)
        
        # Remove some data to test minimal scenario
        data_series = workout_data['data_series']
        data_series['heart_rates'] = [None] * len(data_series['powers'])  # No HR data
        workout_data['avg_heart_rate'] = None
        workout_data['max_heart_rate'] = None
        
        # Generate FIT file
        fit_file_path = self.converter.convert_workout(workout_data)
        assert fit_file_path is not None
        assert os.path.exists(fit_file_path)
        
        # Validate the file
        validation_result = validate_fit_file(fit_file_path)
        
        # Should still be valid
        errors = [issue for issue in validation_result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"FIT file has validation errors: {[e.message for e in errors]}"
        
        # Analyze the file
        analysis = self.analyzer.analyze_fit_file(fit_file_path)
        assert analysis.has_power_data
        assert not analysis.has_heart_rate_data  # Should reflect missing HR data
    
    def test_file_size_and_structure(self):
        """Test FIT file size and structure requirements"""
        workout_data = self.create_sample_workout_data("bike", 20)
        
        # Generate FIT file
        fit_file_path = self.converter.convert_workout(workout_data)
        assert fit_file_path is not None
        
        # Check file size (should be reasonable)
        file_size = os.path.getsize(fit_file_path)
        assert file_size > 1000, "FIT file too small"
        assert file_size < 1000000, "FIT file too large"  # Less than 1MB for 20min workout
        
        # Analyze structure
        analysis = self.analyzer.analyze_fit_file(fit_file_path)
        
        # Should have reasonable message counts
        assert analysis.total_messages > 100, "Too few messages"
        assert 'file_id_message' in analysis.message_counts
        assert 'activity_message' in analysis.message_counts
        assert 'record_message' in analysis.message_counts
        assert analysis.message_counts['record_message'] > 1000  # ~1 per second for 20min
    
    def test_data_consistency(self):
        """Test data consistency within FIT file"""
        workout_data = self.create_sample_workout_data("bike", 15)
        
        # Generate FIT file
        fit_file_path = self.converter.convert_workout(workout_data)
        assert fit_file_path is not None
        
        # Analyze the file
        analysis = self.analyzer.analyze_fit_file(fit_file_path)
        
        # Check data ranges are reasonable
        if analysis.power_range:
            assert analysis.power_range[0] >= 0, "Negative power values"
            assert analysis.power_range[1] <= 2000, "Unrealistic high power"
        
        if analysis.heart_rate_range:
            assert analysis.heart_rate_range[0] >= 30, "Unrealistic low heart rate"
            assert analysis.heart_rate_range[1] <= 250, "Unrealistic high heart rate"
        
        if analysis.cadence_range:
            assert analysis.cadence_range[0] >= 0, "Negative cadence"
            assert analysis.cadence_range[1] <= 300, "Unrealistic high cadence"
        
        if analysis.speed_range:
            assert analysis.speed_range[0] >= 0, "Negative speed"
            assert analysis.speed_range[1] <= 100, "Unrealistic high speed (m/s)"
    
    def test_timestamp_consistency(self):
        """Test timestamp consistency in FIT file"""
        workout_data = self.create_sample_workout_data("bike", 10)
        
        # Generate FIT file
        fit_file_path = self.converter.convert_workout(workout_data)
        assert fit_file_path is not None
        
        # Validate timestamps
        validation_result = validate_fit_file(fit_file_path)
        
        # Check for timestamp-related errors
        timestamp_errors = [issue for issue in validation_result.issues 
                          if 'timestamp' in issue.message.lower() and 
                          issue.severity == ValidationSeverity.ERROR]
        assert len(timestamp_errors) == 0, f"Timestamp errors: {[e.message for e in timestamp_errors]}"
        
        # Analyze timing
        analysis = self.analyzer.analyze_fit_file(fit_file_path)
        assert analysis.start_time is not None, "Missing start time"
        assert analysis.end_time is not None, "Missing end time"
        assert analysis.duration_seconds is not None, "Missing duration"
        assert analysis.duration_seconds > 500, "Duration too short"  # At least 8+ minutes
    
    def test_device_identification(self):
        """Test proper device identification in FIT file"""
        workout_data = self.create_sample_workout_data("bike", 15)
        
        # Add device information
        workout_data['device_name'] = 'Rogue Echo Bike'
        
        # Generate FIT file
        fit_file_path = self.converter.convert_workout(workout_data)
        assert fit_file_path is not None
        
        # Analyze device info
        analysis = self.analyzer.analyze_fit_file(fit_file_path)
        
        # Should have device identification
        assert analysis.device_manufacturer is not None, "Missing device manufacturer"
        assert analysis.device_product is not None, "Missing device product"
        
        # Check Garmin Connect compatibility with device info
        compatibility = self.analyzer.validate_garmin_connect_compatibility(fit_file_path)
        
        # Should not have device-related issues
        device_issues = [issue for issue in compatibility['issues'] 
                        if 'device' in issue.lower()]
        assert len(device_issues) == 0, f"Device identification issues: {device_issues}"
    
    def test_multiple_workout_types(self):
        """Test compatibility across different workout types"""
        workout_types = ["bike", "rower"]
        
        for workout_type in workout_types:
            workout_data = self.create_sample_workout_data(workout_type, 12)
            
            # Generate FIT file
            fit_file_path = self.converter.convert_workout(workout_data)
            assert fit_file_path is not None, f"Failed to generate FIT file for {workout_type}"
            
            # Validate compatibility
            compatibility = self.analyzer.validate_garmin_connect_compatibility(fit_file_path)
            assert compatibility['is_compatible'], f"{workout_type} workout not compatible: {compatibility['issues']}"
            
            # Check sport type is set appropriately
            analysis = self.analyzer.analyze_fit_file(fit_file_path)
            assert analysis.sport_type is not None, f"Missing sport type for {workout_type}"

class TestFITFileComparison:
    """Test FIT file comparison functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.converter = FITConverter(output_dir=self.temp_dir)
        self.analyzer = FITAnalyzer()
    
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_identical_files_comparison(self):
        """Test comparison of identical FIT files"""
        # Create workout data
        workout_data = {
            'workout_type': 'bike',
            'start_time': '2024-01-01T10:00:00Z',
            'total_duration': 600,
            'avg_power': 150,
            'data_series': {
                'absolute_timestamps': ['2024-01-01T10:00:00Z', '2024-01-01T10:01:00Z'],
                'powers': [150, 160],
                'heart_rates': [140, 145]
            }
        }
        
        # Generate two identical files
        fit_file1 = self.converter.convert_workout(workout_data)
        fit_file2 = self.converter.convert_workout(workout_data)
        
        assert fit_file1 is not None
        assert fit_file2 is not None
        
        # Compare files
        comparison = self.analyzer.compare_fit_files(fit_file1, fit_file2)
        
        # Should be highly compatible
        assert comparison.compatibility_score > 0.9, f"Low compatibility score: {comparison.compatibility_score}"
        assert len(comparison.issues) == 0, f"Unexpected issues: {comparison.issues}"
    
    def test_different_workout_types_comparison(self):
        """Test comparison of different workout types"""
        # Create bike workout
        bike_data = {
            'workout_type': 'bike',
            'start_time': '2024-01-01T10:00:00Z',
            'total_duration': 600,
            'avg_power': 150,
            'data_series': {
                'absolute_timestamps': ['2024-01-01T10:00:00Z', '2024-01-01T10:01:00Z'],
                'powers': [150, 160],
                'cadences': [80, 85]
            }
        }
        
        # Create rower workout
        rower_data = {
            'workout_type': 'rower',
            'start_time': '2024-01-01T10:00:00Z',
            'total_duration': 600,
            'avg_power': 120,
            'data_series': {
                'absolute_timestamps': ['2024-01-01T10:00:00Z', '2024-01-01T10:01:00Z'],
                'powers': [120, 130],
                'cadences': [25, 28]  # Stroke rate
            }
        }
        
        # Generate FIT files
        bike_fit = self.converter.convert_workout(bike_data)
        rower_fit = self.converter.convert_workout(rower_data)
        
        assert bike_fit is not None
        assert rower_fit is not None
        
        # Compare files
        comparison = self.analyzer.compare_fit_files(bike_fit, rower_fit)
        
        # Should have differences but still be somewhat compatible
        assert comparison.compatibility_score < 1.0, "Should have differences"
        assert len(comparison.field_differences) > 0, "Should have field differences"
        assert any('sport' in str(diff) for diff in comparison.field_differences), "Should have sport type difference"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])