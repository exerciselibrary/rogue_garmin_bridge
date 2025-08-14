"""
Enhanced Speed Calculation Module for FIT File Generation

This module provides improved speed calculation algorithms based on workout.log analysis,
including outlier filtering, running averages, and validation against distance accumulation.
"""

import logging
import statistics
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SpeedMetrics:
    """Container for calculated speed metrics"""
    avg_speed: float
    max_speed: float
    filtered_speeds: List[float]
    outliers_removed: int
    distance_validated: bool
    validation_error: Optional[str] = None

class EnhancedSpeedCalculator:
    """
    Enhanced speed calculator with outlier filtering and validation
    """
    
    def __init__(self, outlier_threshold_std: float = 2.0, min_valid_speed: float = 0.1):
        """
        Initialize the speed calculator
        
        Args:
            outlier_threshold_std: Number of standard deviations for outlier detection
            min_valid_speed: Minimum speed (km/h) to consider valid
        """
        self.outlier_threshold_std = outlier_threshold_std
        self.min_valid_speed = min_valid_speed
    
    def calculate_speed_metrics(self, 
                              instantaneous_speeds: List[float],
                              distances: List[float] = None,
                              timestamps: List[float] = None,
                              device_avg_speed: float = None) -> SpeedMetrics:
        """
        Calculate enhanced speed metrics with outlier filtering and validation
        
        Args:
            instantaneous_speeds: List of instantaneous speed values (km/h)
            distances: Optional list of cumulative distances (meters)
            timestamps: Optional list of timestamps (seconds from start)
            device_avg_speed: Device-reported average speed for comparison
            
        Returns:
            SpeedMetrics object with calculated values
        """
        if not instantaneous_speeds:
            logger.warning("No speed data provided")
            return SpeedMetrics(0.0, 0.0, [], 0, False, "No speed data")
        
        # Filter out invalid speeds
        valid_speeds = [s for s in instantaneous_speeds if s >= self.min_valid_speed]
        
        if not valid_speeds:
            logger.warning("No valid speed values found")
            return SpeedMetrics(0.0, 0.0, [], len(instantaneous_speeds), False, "No valid speeds")
        
        # Apply outlier filtering
        filtered_speeds, outliers_removed = self._filter_outliers(valid_speeds)
        
        if not filtered_speeds:
            logger.warning("All speeds filtered as outliers, using original valid speeds")
            filtered_speeds = valid_speeds
            outliers_removed = 0
        
        # Calculate basic metrics
        avg_speed = statistics.mean(filtered_speeds)
        max_speed = max(filtered_speeds)
        
        # Validate against distance if available
        distance_validated = True
        validation_error = None
        
        if distances and timestamps and len(distances) == len(timestamps) == len(instantaneous_speeds):
            distance_validated, validation_error = self._validate_against_distance(
                filtered_speeds, distances, timestamps
            )
        
        # Log comparison with device-reported speed if available
        if device_avg_speed is not None:
            speed_ratio = avg_speed / device_avg_speed if device_avg_speed > 0 else float('inf')
            logger.info(f"Calculated avg speed: {avg_speed:.2f} km/h, "
                       f"Device-reported: {device_avg_speed:.2f} km/h, "
                       f"Ratio: {speed_ratio:.1f}x")
        
        logger.info(f"Speed calculation: avg={avg_speed:.2f} km/h, max={max_speed:.2f} km/h, "
                   f"filtered {len(filtered_speeds)}/{len(instantaneous_speeds)} points, "
                   f"removed {outliers_removed} outliers")
        
        return SpeedMetrics(
            avg_speed=avg_speed,
            max_speed=max_speed,
            filtered_speeds=filtered_speeds,
            outliers_removed=outliers_removed,
            distance_validated=distance_validated,
            validation_error=validation_error
        )
    
    def _filter_outliers(self, speeds: List[float]) -> Tuple[List[float], int]:
        """
        Filter outliers using standard deviation method
        
        Args:
            speeds: List of speed values
            
        Returns:
            Tuple of (filtered_speeds, outliers_removed_count)
        """
        if len(speeds) < 3:
            return speeds, 0
        
        try:
            mean_speed = statistics.mean(speeds)
            std_speed = statistics.stdev(speeds)
            
            if std_speed == 0:
                return speeds, 0
            
            # Filter speeds within threshold standard deviations
            threshold = self.outlier_threshold_std * std_speed
            filtered_speeds = [
                s for s in speeds 
                if abs(s - mean_speed) <= threshold
            ]
            
            outliers_removed = len(speeds) - len(filtered_speeds)
            
            if outliers_removed > 0:
                logger.debug(f"Removed {outliers_removed} outliers from {len(speeds)} speeds "
                           f"(mean={mean_speed:.2f}, std={std_speed:.2f}, threshold={threshold:.2f})")
            
            return filtered_speeds, outliers_removed
            
        except statistics.StatisticsError as e:
            logger.warning(f"Error in outlier filtering: {e}")
            return speeds, 0
    
    def _validate_against_distance(self, 
                                 speeds: List[float], 
                                 distances: List[float], 
                                 timestamps: List[float]) -> Tuple[bool, Optional[str]]:
        """
        Validate calculated speeds against distance accumulation
        
        Args:
            speeds: Filtered speed values (km/h)
            distances: Cumulative distances (meters)
            timestamps: Timestamps (seconds from start)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Calculate expected distance from speed integration
            expected_distance = 0.0
            
            for i in range(1, len(speeds)):
                if i < len(timestamps):
                    time_delta = timestamps[i] - timestamps[i-1]
                    # Convert speed from km/h to m/s and multiply by time
                    speed_ms = speeds[i] / 3.6
                    expected_distance += speed_ms * time_delta
            
            # Get actual final distance
            actual_distance = distances[-1] if distances else 0
            
            # Allow for some tolerance (20%) due to measurement errors
            tolerance = 0.20
            distance_error = abs(expected_distance - actual_distance) / max(actual_distance, 1)
            
            is_valid = distance_error <= tolerance
            
            if not is_valid:
                error_msg = (f"Distance validation failed: expected {expected_distance:.1f}m, "
                           f"actual {actual_distance:.1f}m, error {distance_error:.1%}")
                logger.warning(error_msg)
                return False, error_msg
            else:
                logger.debug(f"Distance validation passed: expected {expected_distance:.1f}m, "
                           f"actual {actual_distance:.1f}m, error {distance_error:.1%}")
                return True, None
                
        except Exception as e:
            error_msg = f"Distance validation error: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def calculate_running_average(self, 
                                speeds: List[float], 
                                window_size: int = 5,
                                weight_recent: float = 0.7) -> List[float]:
        """
        Calculate running average with proper weighting
        
        Args:
            speeds: List of speed values
            window_size: Size of the moving window
            weight_recent: Weight for more recent values (0.5 = equal, 1.0 = only recent)
            
        Returns:
            List of running averages
        """
        if not speeds:
            return []
        
        running_averages = []
        
        for i in range(len(speeds)):
            # Determine window bounds
            start_idx = max(0, i - window_size + 1)
            window_speeds = speeds[start_idx:i+1]
            
            if len(window_speeds) == 1:
                running_averages.append(window_speeds[0])
                continue
            
            # Apply weighting - more recent values get higher weight
            weights = []
            for j in range(len(window_speeds)):
                # Linear weighting from (1-weight_recent) to weight_recent
                weight = (1 - weight_recent) + (weight_recent * j / (len(window_speeds) - 1))
                weights.append(weight)
            
            # Calculate weighted average
            weighted_sum = sum(speed * weight for speed, weight in zip(window_speeds, weights))
            weight_sum = sum(weights)
            
            running_avg = weighted_sum / weight_sum
            running_averages.append(running_avg)
        
        return running_averages

def fix_device_reported_speeds(workout_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix device-reported average speed issues identified in logs
    
    Args:
        workout_data: Workout data dictionary
        
    Returns:
        Updated workout data with corrected speeds
    """
    calculator = EnhancedSpeedCalculator()
    
    # Extract speed data
    data_series = workout_data.get('data_series', {})
    instantaneous_speeds = data_series.get('speeds', [])
    distances = data_series.get('distances', [])
    timestamps = data_series.get('timestamps', [])
    
    if not instantaneous_speeds:
        logger.warning("No instantaneous speed data found")
        return workout_data
    
    # Get device-reported average for comparison
    device_avg_speed = workout_data.get('avg_speed', 0)
    
    # Calculate enhanced metrics
    speed_metrics = calculator.calculate_speed_metrics(
        instantaneous_speeds=instantaneous_speeds,
        distances=distances,
        timestamps=timestamps,
        device_avg_speed=device_avg_speed
    )
    
    # Update workout data with corrected values
    workout_data['avg_speed'] = speed_metrics.avg_speed
    workout_data['max_speed'] = speed_metrics.max_speed
    
    # Add metadata about the correction
    workout_data['speed_correction_applied'] = True
    workout_data['original_device_avg_speed'] = device_avg_speed
    workout_data['outliers_removed'] = speed_metrics.outliers_removed
    workout_data['distance_validated'] = speed_metrics.distance_validated
    
    if speed_metrics.validation_error:
        workout_data['speed_validation_error'] = speed_metrics.validation_error
    
    logger.info(f"Applied speed correction: {device_avg_speed:.2f} -> {speed_metrics.avg_speed:.2f} km/h")
    
    return workout_data

# Example usage and testing
if __name__ == "__main__":
    # Test with sample data from workout.log
    sample_speeds = [0.0, 0.0, 1.12, 5.3, 9.49, 12.55, 14.32, 14.32, 14.96, 14.96, 16.73]
    sample_distances = [0, 0, 0, 0, 0, 16, 16, 16, 32, 32, 32]
    sample_timestamps = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    
    calculator = EnhancedSpeedCalculator()
    metrics = calculator.calculate_speed_metrics(
        instantaneous_speeds=sample_speeds,
        distances=sample_distances,
        timestamps=sample_timestamps,
        device_avg_speed=0.75  # From log
    )
    
    print(f"Speed Metrics:")
    print(f"  Average Speed: {metrics.avg_speed:.2f} km/h")
    print(f"  Max Speed: {metrics.max_speed:.2f} km/h")
    print(f"  Outliers Removed: {metrics.outliers_removed}")
    print(f"  Distance Validated: {metrics.distance_validated}")
    if metrics.validation_error:
        print(f"  Validation Error: {metrics.validation_error}")