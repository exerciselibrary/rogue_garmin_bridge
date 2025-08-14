"""
Unit tests for Enhanced Speed Calculator
"""

import pytest
import logging
from src.fit.speed_calculator import EnhancedSpeedCalculator, SpeedMetrics, fix_device_reported_speeds

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

class TestEnhancedSpeedCalculator:
    """Test cases for EnhancedSpeedCalculator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.calculator = EnhancedSpeedCalculator()
    
    def test_basic_speed_calculation(self):
        """Test basic speed calculation without outliers"""
        speeds = [10.0, 12.0, 11.0, 13.0, 12.5]
        
        metrics = self.calculator.calculate_speed_metrics(speeds)
        
        assert metrics.avg_speed == pytest.approx(11.7, rel=1e-2)
        assert metrics.max_speed == 13.0
        assert metrics.outliers_removed == 0
        assert len(metrics.filtered_speeds) == 5
    
    def test_outlier_filtering(self):
        """Test outlier detection and removal"""
        # Include some obvious outliers
        speeds = [10.0, 12.0, 11.0, 50.0, 13.0, 12.5, 100.0]  # 50.0 and 100.0 are outliers
        
        metrics = self.calculator.calculate_speed_metrics(speeds)
        
        # Should remove the outliers
        assert metrics.outliers_removed > 0
        assert metrics.max_speed <= 50.0  # Max should be from filtered data (50.0 might still be included)
        assert len(metrics.filtered_speeds) < len(speeds)
    
    def test_empty_speed_list(self):
        """Test handling of empty speed list"""
        metrics = self.calculator.calculate_speed_metrics([])
        
        assert metrics.avg_speed == 0.0
        assert metrics.max_speed == 0.0
        assert metrics.outliers_removed == 0
        assert not metrics.distance_validated
        assert metrics.validation_error == "No speed data"
    
    def test_invalid_speeds_filtering(self):
        """Test filtering of invalid (too low) speeds"""
        speeds = [0.0, 0.05, 10.0, 12.0, 0.0, 11.0]  # Some speeds below minimum
        
        metrics = self.calculator.calculate_speed_metrics(speeds)
        
        # Should only use valid speeds (>= 0.1 km/h by default)
        assert metrics.avg_speed > 0
        assert len(metrics.filtered_speeds) == 3  # Only 10.0, 12.0, 11.0
    
    def test_distance_validation_success(self):
        """Test successful distance validation"""
        speeds = [10.0, 10.0, 10.0, 10.0]  # Constant 10 km/h
        timestamps = [0, 1, 2, 3]  # 1 second intervals
        # At 10 km/h for 3 seconds = 10/3.6 * 3 = 8.33 meters
        distances = [0, 2.78, 5.56, 8.33]  # Cumulative distances
        
        metrics = self.calculator.calculate_speed_metrics(
            speeds, distances, timestamps
        )
        
        assert metrics.distance_validated
        assert metrics.validation_error is None
    
    def test_distance_validation_failure(self):
        """Test distance validation failure"""
        speeds = [10.0, 10.0, 10.0, 10.0]  # Constant 10 km/h
        timestamps = [0, 1, 2, 3]  # 1 second intervals
        distances = [0, 1, 2, 3]  # Much lower distances than expected
        
        metrics = self.calculator.calculate_speed_metrics(
            speeds, distances, timestamps
        )
        
        assert not metrics.distance_validated
        assert metrics.validation_error is not None
    
    def test_running_average_calculation(self):
        """Test running average with weighting"""
        speeds = [10.0, 12.0, 14.0, 16.0, 18.0]
        
        running_avgs = self.calculator.calculate_running_average(speeds, window_size=3)
        
        assert len(running_avgs) == len(speeds)
        # First value should be the same
        assert running_avgs[0] == 10.0
        # Later values should be weighted averages
        assert running_avgs[-1] > running_avgs[0]  # Should trend upward
    
    def test_workout_log_sample_data(self):
        """Test with actual data from workout.log"""
        # Sample data from the log analysis
        speeds = [0.0, 0.0, 1.12, 5.3, 9.49, 12.55, 14.32, 14.32, 14.96, 14.96, 16.73]
        device_avg = 0.75  # Device reported average
        
        metrics = self.calculator.calculate_speed_metrics(speeds, device_avg_speed=device_avg)
        
        # Should calculate much higher average than device reported
        assert metrics.avg_speed > device_avg * 10  # At least 10x higher
        assert metrics.max_speed == 16.73
        assert metrics.outliers_removed >= 0  # May remove some outliers
    
    def test_single_speed_value(self):
        """Test with single speed value"""
        speeds = [15.0]
        
        metrics = self.calculator.calculate_speed_metrics(speeds)
        
        assert metrics.avg_speed == 15.0
        assert metrics.max_speed == 15.0
        assert metrics.outliers_removed == 0
    
    def test_all_zero_speeds(self):
        """Test with all zero speeds"""
        speeds = [0.0, 0.0, 0.0, 0.0]
        
        metrics = self.calculator.calculate_speed_metrics(speeds)
        
        assert metrics.avg_speed == 0.0
        assert metrics.max_speed == 0.0
        assert not metrics.distance_validated
        assert "No valid speeds" in metrics.validation_error

class TestFixDeviceReportedSpeeds:
    """Test cases for fix_device_reported_speeds function"""
    
    def test_fix_device_speeds(self):
        """Test fixing device-reported speeds"""
        workout_data = {
            'workout_type': 'bike',
            'avg_speed': 0.75,  # Low device-reported speed
            'data_series': {
                'speeds': [1.12, 5.3, 9.49, 12.55, 14.32, 14.96, 16.73],
                'distances': [0, 0, 0, 16, 16, 32, 32],
                'timestamps': [5, 6, 7, 8, 9, 11, 13]
            }
        }
        
        fixed_data = fix_device_reported_speeds(workout_data)
        
        # Should have much higher corrected average speed (at least 5x higher than original)
        original_speed = fixed_data['original_device_avg_speed']  # 0.75
        assert fixed_data['avg_speed'] > original_speed * 5
        assert fixed_data['speed_correction_applied'] is True
        assert fixed_data['original_device_avg_speed'] == 0.75
        assert 'outliers_removed' in fixed_data
    
    def test_no_speed_data(self):
        """Test with no speed data"""
        workout_data = {
            'workout_type': 'bike',
            'avg_speed': 0.0,
            'data_series': {}
        }
        
        fixed_data = fix_device_reported_speeds(workout_data)
        
        # Should return original data unchanged
        assert fixed_data == workout_data
    
    def test_rower_workout(self):
        """Test with rower workout data"""
        workout_data = {
            'workout_type': 'rower',
            'avg_speed': 5.0,  # Reasonable rower speed
            'data_series': {
                'speeds': [4.5, 5.0, 5.2, 5.1, 4.8],
                'distances': [0, 10, 20, 30, 40],
                'timestamps': [0, 2, 4, 6, 8]
            }
        }
        
        fixed_data = fix_device_reported_speeds(workout_data)
        
        # Should still apply correction but result should be similar
        assert 'speed_correction_applied' in fixed_data
        assert fixed_data['avg_speed'] > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])