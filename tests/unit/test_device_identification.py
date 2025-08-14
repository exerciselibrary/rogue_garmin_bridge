"""
Unit tests for Device Identification Module
"""

import pytest
import logging
from src.fit.device_identification import (
    DeviceIdentifier, DeviceType, SportType, SubSportType, ActivityType,
    enhance_device_identification
)

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

class TestDeviceIdentifier:
    """Test cases for DeviceIdentifier"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.identifier = DeviceIdentifier()
    
    def test_identify_rogue_echo_bike(self):
        """Test identification of Rogue Echo Bike"""
        device_info = self.identifier.identify_device("bike", "Rogue Echo Bike")
        
        assert device_info.device_type == DeviceType.BIKE
        assert device_info.sport_type == SportType.CYCLING
        assert device_info.sub_sport_type == SubSportType.INDOOR_CYCLING
        assert device_info.activity_type == ActivityType.INDOOR_CYCLING
        assert device_info.device_name == "Rogue Echo Bike"
        assert device_info.supports_power is True
        assert device_info.supports_cadence is True
    
    def test_identify_rogue_echo_rower(self):
        """Test identification of Rogue Echo Rower"""
        device_info = self.identifier.identify_device("rower", "Rogue Echo Rower")
        
        assert device_info.device_type == DeviceType.ROWER
        assert device_info.sport_type == SportType.ROWING
        assert device_info.sub_sport_type == SubSportType.INDOOR_ROWING
        assert device_info.activity_type == ActivityType.ROWING
        assert device_info.device_name == "Rogue Echo Rower"
        assert device_info.supports_power is True
        assert device_info.supports_cadence is True  # Stroke rate
    
    def test_identify_generic_bike(self):
        """Test identification of generic bike"""
        device_info = self.identifier.identify_device("bike")
        
        assert device_info.device_type == DeviceType.BIKE
        assert device_info.sport_type == SportType.CYCLING
        assert device_info.device_name == "Indoor Bike"
        assert device_info.manufacturer_id == self.identifier.ROGUE_MANUFACTURER_ID
    
    def test_identify_generic_rower(self):
        """Test identification of generic rower"""
        device_info = self.identifier.identify_device("rower")
        
        assert device_info.device_type == DeviceType.ROWER
        assert device_info.sport_type == SportType.ROWING
        assert device_info.device_name == "Indoor Rower"
        assert device_info.manufacturer_id == self.identifier.ROGUE_MANUFACTURER_ID
    
    def test_identify_unknown_workout_type(self):
        """Test handling of unknown workout type"""
        device_info = self.identifier.identify_device("unknown")
        
        # Should default to bike
        assert device_info.device_type == DeviceType.BIKE
        assert device_info.sport_type == SportType.CYCLING
    
    def test_device_name_matching_case_insensitive(self):
        """Test case-insensitive device name matching"""
        device_info = self.identifier.identify_device("bike", "ROGUE ECHO BIKE")
        
        assert device_info.device_name == "Rogue Echo Bike"
        assert device_info.device_type == DeviceType.BIKE
    
    def test_device_name_partial_matching(self):
        """Test partial device name matching"""
        device_info = self.identifier.identify_device("bike", "Echo Bike Pro")
        
        assert device_info.device_name == "Rogue Echo Bike"
        assert device_info.device_type == DeviceType.BIKE
    
    def test_workout_intensity_calculation_power_based(self):
        """Test workout intensity calculation using power"""
        intensity = self.identifier.calculate_workout_intensity(
            avg_power=200, user_ftp=250
        )
        
        # 200W / 250W FTP = 0.8, scaled to 0.533
        assert 0.5 <= intensity <= 0.6
    
    def test_workout_intensity_calculation_hr_based(self):
        """Test workout intensity calculation using heart rate"""
        intensity = self.identifier.calculate_workout_intensity(
            avg_heart_rate=150, user_max_hr=190
        )
        
        # (150 - 60) / (190 - 60) = 90/130 = 0.69
        assert 0.6 <= intensity <= 0.8
    
    def test_workout_intensity_calculation_combined(self):
        """Test workout intensity calculation using both power and HR"""
        intensity = self.identifier.calculate_workout_intensity(
            avg_power=200, user_ftp=250,
            avg_heart_rate=150, user_max_hr=190
        )
        
        # Should average power and HR intensities
        assert 0.5 <= intensity <= 0.8
    
    def test_workout_intensity_fallback(self):
        """Test workout intensity fallback calculation"""
        intensity = self.identifier.calculate_workout_intensity(
            avg_power=150, max_power=200
        )
        
        # Should use power ratio fallback
        assert 0.5 <= intensity <= 1.0
    
    def test_workout_intensity_default(self):
        """Test default workout intensity when no data available"""
        intensity = self.identifier.calculate_workout_intensity()
        
        assert intensity == 0.6  # Default moderate intensity
    
    def test_training_load_multiplier_bike(self):
        """Test training load multiplier for bike"""
        device_info = self.identifier.identify_device("bike")
        multiplier = self.identifier.get_training_load_multiplier(device_info, 0.7)
        
        # Base 1.0 * (0.5 + 0.7 * 1.5) = 1.0 * 1.55 = 1.55
        assert 1.4 <= multiplier <= 1.6
    
    def test_training_load_multiplier_rower(self):
        """Test training load multiplier for rower"""
        device_info = self.identifier.identify_device("rower")
        multiplier = self.identifier.get_training_load_multiplier(device_info, 0.7)
        
        # Base 1.2 * (0.5 + 0.7 * 1.5) = 1.2 * 1.55 = 1.86
        assert 1.7 <= multiplier <= 1.9
    
    def test_training_load_multiplier_low_intensity(self):
        """Test training load multiplier with low intensity"""
        device_info = self.identifier.identify_device("bike")
        multiplier = self.identifier.get_training_load_multiplier(device_info, 0.2)
        
        # Base 1.0 * (0.5 + 0.2 * 1.5) = 1.0 * 0.8 = 0.8
        assert 0.7 <= multiplier <= 0.9
    
    def test_training_load_multiplier_high_intensity(self):
        """Test training load multiplier with high intensity"""
        device_info = self.identifier.identify_device("bike")
        multiplier = self.identifier.get_training_load_multiplier(device_info, 1.0)
        
        # Base 1.0 * (0.5 + 1.0 * 1.5) = 1.0 * 2.0 = 2.0
        assert 1.9 <= multiplier <= 2.1

class TestEnhanceDeviceIdentification:
    """Test cases for enhance_device_identification function"""
    
    def test_enhance_bike_workout_data(self):
        """Test enhancing bike workout data"""
        workout_data = {
            'workout_type': 'bike',
            'device_name': 'Rogue Echo Bike',
            'avg_power': 200,
            'max_power': 350,
            'avg_heart_rate': 150,
            'max_heart_rate': 175
        }
        
        user_profile = {
            'ftp': 250,
            'max_heart_rate': 190
        }
        
        enhanced_data = enhance_device_identification(workout_data, user_profile)
        
        assert enhanced_data['device_manufacturer_id'] == 65534  # Rogue manufacturer ID
        assert enhanced_data['device_product_id'] == 1001  # Rogue Echo Bike product ID
        assert enhanced_data['device_name_identified'] == "Rogue Echo Bike"
        assert enhanced_data['sport_type'] == SportType.CYCLING.value
        assert enhanced_data['sub_sport_type'] == SubSportType.INDOOR_CYCLING.value
        assert enhanced_data['activity_type'] == ActivityType.INDOOR_CYCLING.value
        assert 'workout_intensity' in enhanced_data
        assert 'training_load_multiplier' in enhanced_data
        assert enhanced_data['device_supports_power'] is True
    
    def test_enhance_rower_workout_data(self):
        """Test enhancing rower workout data"""
        workout_data = {
            'workout_type': 'rower',
            'avg_power': 180,
            'max_power': 300
        }
        
        enhanced_data = enhance_device_identification(workout_data)
        
        assert enhanced_data['device_manufacturer_id'] == 65534
        assert enhanced_data['device_product_id'] == 1004  # Generic rower product ID
        assert enhanced_data['device_name_identified'] == "Indoor Rower"
        assert enhanced_data['sport_type'] == SportType.ROWING.value
        assert enhanced_data['sub_sport_type'] == SubSportType.INDOOR_ROWING.value
        assert enhanced_data['activity_type'] == ActivityType.ROWING.value
    
    def test_enhance_without_user_profile(self):
        """Test enhancing workout data without user profile"""
        workout_data = {
            'workout_type': 'bike',
            'avg_power': 150,
            'max_power': 250
        }
        
        enhanced_data = enhance_device_identification(workout_data)
        
        # Should still work with fallback intensity calculation
        assert 'workout_intensity' in enhanced_data
        assert 'training_load_multiplier' in enhanced_data
        assert enhanced_data['workout_intensity'] > 0
    
    def test_enhance_minimal_data(self):
        """Test enhancing with minimal workout data"""
        workout_data = {
            'workout_type': 'bike'
        }
        
        enhanced_data = enhance_device_identification(workout_data)
        
        # Should use defaults
        assert enhanced_data['device_manufacturer_id'] == 65534
        assert enhanced_data['workout_intensity'] == 0.6  # Default intensity
        assert enhanced_data['training_load_multiplier'] > 0
    
    def test_preserve_original_data(self):
        """Test that original workout data is preserved"""
        workout_data = {
            'workout_type': 'bike',
            'total_duration': 1800,
            'total_distance': 5000,
            'custom_field': 'test_value'
        }
        
        enhanced_data = enhance_device_identification(workout_data)
        
        # Original data should be preserved
        assert enhanced_data['total_duration'] == 1800
        assert enhanced_data['total_distance'] == 5000
        assert enhanced_data['custom_field'] == 'test_value'
        
        # New fields should be added
        assert 'device_manufacturer_id' in enhanced_data
        assert 'workout_intensity' in enhanced_data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])