"""
Device Identification Module for FIT File Generation

This module provides proper device identification for Garmin Connect recognition
and accurate training load calculations.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    """Supported device types"""
    BIKE = "bike"
    ROWER = "rower"
    UNKNOWN = "unknown"

class SportType(Enum):
    """Sport types for FIT files"""
    CYCLING = 2
    ROWING = 15
    GENERIC = 0

class SubSportType(Enum):
    """Sub-sport types for FIT files"""
    INDOOR_CYCLING = 6
    ROAD_CYCLING = 7
    INDOOR_ROWING = 14
    GENERIC = 0

class ActivityType(Enum):
    """Activity types for FIT files"""
    INDOOR_CYCLING = 6
    CYCLING = 2
    ROWING = 15
    GENERIC = 0

@dataclass
class DeviceInfo:
    """Device information for FIT file generation"""
    manufacturer_id: int
    product_id: int
    device_type: DeviceType
    sport_type: SportType
    sub_sport_type: SubSportType
    activity_type: ActivityType
    device_name: str
    supports_power: bool = True
    supports_heart_rate: bool = True
    supports_cadence: bool = True

class DeviceIdentifier:
    """
    Identifies devices and provides proper FIT file metadata
    """
    
    # Garmin manufacturer ID
    GARMIN_MANUFACTURER_ID = 1
    
    # Custom manufacturer ID for Rogue equipment (using development range)
    ROGUE_MANUFACTURER_ID = 65534  # Development manufacturer ID
    
    # Product IDs for different devices
    ROGUE_ECHO_BIKE_PRODUCT_ID = 1001
    ROGUE_ECHO_ROWER_PRODUCT_ID = 1002
    GENERIC_BIKE_PRODUCT_ID = 1003
    GENERIC_ROWER_PRODUCT_ID = 1004
    
    def __init__(self):
        """Initialize device identifier"""
        self._device_registry = self._build_device_registry()
    
    def _build_device_registry(self) -> Dict[str, DeviceInfo]:
        """Build registry of supported devices"""
        return {
            "rogue_echo_bike": DeviceInfo(
                manufacturer_id=self.ROGUE_MANUFACTURER_ID,
                product_id=self.ROGUE_ECHO_BIKE_PRODUCT_ID,
                device_type=DeviceType.BIKE,
                sport_type=SportType.CYCLING,
                sub_sport_type=SubSportType.INDOOR_CYCLING,
                activity_type=ActivityType.INDOOR_CYCLING,
                device_name="Rogue Echo Bike",
                supports_power=True,
                supports_heart_rate=True,
                supports_cadence=True
            ),
            "rogue_echo_rower": DeviceInfo(
                manufacturer_id=self.ROGUE_MANUFACTURER_ID,
                product_id=self.ROGUE_ECHO_ROWER_PRODUCT_ID,
                device_type=DeviceType.ROWER,
                sport_type=SportType.ROWING,
                sub_sport_type=SubSportType.INDOOR_ROWING,
                activity_type=ActivityType.ROWING,
                device_name="Rogue Echo Rower",
                supports_power=True,
                supports_heart_rate=True,
                supports_cadence=True  # Stroke rate for rowers
            ),
            "generic_bike": DeviceInfo(
                manufacturer_id=self.ROGUE_MANUFACTURER_ID,
                product_id=self.GENERIC_BIKE_PRODUCT_ID,
                device_type=DeviceType.BIKE,
                sport_type=SportType.CYCLING,
                sub_sport_type=SubSportType.INDOOR_CYCLING,
                activity_type=ActivityType.INDOOR_CYCLING,
                device_name="Indoor Bike",
                supports_power=True,
                supports_heart_rate=True,
                supports_cadence=True
            ),
            "generic_rower": DeviceInfo(
                manufacturer_id=self.ROGUE_MANUFACTURER_ID,
                product_id=self.GENERIC_ROWER_PRODUCT_ID,
                device_type=DeviceType.ROWER,
                sport_type=SportType.ROWING,
                sub_sport_type=SubSportType.INDOOR_ROWING,
                activity_type=ActivityType.ROWING,
                device_name="Indoor Rower",
                supports_power=True,
                supports_heart_rate=True,
                supports_cadence=True
            )
        }
    
    def identify_device(self, 
                       workout_type: str, 
                       device_name: Optional[str] = None,
                       device_address: Optional[str] = None) -> DeviceInfo:
        """
        Identify device based on workout type and optional device information
        
        Args:
            workout_type: Type of workout ('bike' or 'rower')
            device_name: Optional device name from Bluetooth
            device_address: Optional device Bluetooth address
            
        Returns:
            DeviceInfo object with proper identification
        """
        # Normalize workout type
        workout_type = workout_type.lower().strip()
        
        # Try to identify specific device first
        if device_name:
            device_key = self._match_device_name(device_name, workout_type)
            if device_key and device_key in self._device_registry:
                logger.info(f"Identified device: {device_key} from name '{device_name}'")
                return self._device_registry[device_key]
        
        # Fallback to generic device based on workout type
        if workout_type in ['bike', 'cycling']:
            device_key = "generic_bike"
        elif workout_type in ['rower', 'rowing']:
            device_key = "generic_rower"
        else:
            logger.warning(f"Unknown workout type '{workout_type}', using generic bike")
            device_key = "generic_bike"
        
        logger.info(f"Using generic device identification: {device_key}")
        return self._device_registry[device_key]
    
    def _match_device_name(self, device_name: str, workout_type: str) -> Optional[str]:
        """
        Match device name to registry key
        
        Args:
            device_name: Device name from Bluetooth
            workout_type: Workout type for context
            
        Returns:
            Registry key or None if no match
        """
        device_name_lower = device_name.lower()
        
        # Check for Rogue Echo Bike
        if any(keyword in device_name_lower for keyword in ['rogue', 'echo']) and \
           any(keyword in device_name_lower for keyword in ['bike', 'cycle']):
            return "rogue_echo_bike"
        
        # Check for Rogue Echo Rower
        if any(keyword in device_name_lower for keyword in ['rogue', 'echo']) and \
           any(keyword in device_name_lower for keyword in ['rower', 'row']):
            return "rogue_echo_rower"
        
        # Generic matching based on workout type
        if workout_type in ['bike', 'cycling'] and \
           any(keyword in device_name_lower for keyword in ['bike', 'cycle']):
            return "generic_bike"
        
        if workout_type in ['rower', 'rowing'] and \
           any(keyword in device_name_lower for keyword in ['rower', 'row']):
            return "generic_rower"
        
        return None
    
    def get_training_load_multiplier(self, device_info: DeviceInfo, workout_intensity: float) -> float:
        """
        Get training load multiplier based on device type and workout intensity
        
        Args:
            device_info: Device information
            workout_intensity: Workout intensity (0.0 to 1.0)
            
        Returns:
            Training load multiplier
        """
        # Base multipliers by device type
        base_multipliers = {
            DeviceType.BIKE: 1.0,
            DeviceType.ROWER: 1.2,  # Rowing typically engages more muscle groups
            DeviceType.UNKNOWN: 0.8
        }
        
        base_multiplier = base_multipliers.get(device_info.device_type, 1.0)
        
        # Adjust based on workout intensity
        intensity_multiplier = 0.5 + (workout_intensity * 1.5)  # Range: 0.5 to 2.0
        
        final_multiplier = base_multiplier * intensity_multiplier
        
        logger.debug(f"Training load multiplier: {final_multiplier:.2f} "
                    f"(base: {base_multiplier}, intensity: {intensity_multiplier:.2f})")
        
        return final_multiplier
    
    def calculate_workout_intensity(self, 
                                  avg_power: Optional[float] = None,
                                  max_power: Optional[float] = None,
                                  avg_heart_rate: Optional[float] = None,
                                  max_heart_rate: Optional[float] = None,
                                  user_ftp: Optional[float] = None,
                                  user_max_hr: Optional[float] = None) -> float:
        """
        Calculate workout intensity based on available metrics
        
        Args:
            avg_power: Average power (watts)
            max_power: Maximum power (watts)
            avg_heart_rate: Average heart rate (bpm)
            max_heart_rate: Maximum heart rate (bpm)
            user_ftp: User's Functional Threshold Power
            user_max_hr: User's maximum heart rate
            
        Returns:
            Workout intensity (0.0 to 1.0)
        """
        intensities = []
        
        # Power-based intensity
        if avg_power and user_ftp and avg_power > 0 and user_ftp > 0:
            power_intensity = min(avg_power / user_ftp, 1.5) / 1.5  # Cap at 150% FTP
            intensities.append(power_intensity)
            logger.debug(f"Power intensity: {power_intensity:.2f} (avg: {avg_power}W, FTP: {user_ftp}W)")
        
        # Heart rate-based intensity
        if avg_heart_rate and user_max_hr and avg_heart_rate > 0 and user_max_hr > 0:
            # Assume resting HR of 60 for intensity calculation
            resting_hr = 60
            hr_reserve = user_max_hr - resting_hr
            if hr_reserve > 0:
                hr_intensity = (avg_heart_rate - resting_hr) / hr_reserve
                hr_intensity = max(0.0, min(hr_intensity, 1.0))  # Clamp to 0-1
                intensities.append(hr_intensity)
                logger.debug(f"HR intensity: {hr_intensity:.2f} (avg: {avg_heart_rate}bpm, max: {user_max_hr}bpm)")
        
        # Fallback: use power distribution if no user thresholds
        if not intensities and avg_power and max_power and max_power > 0:
            # Simple intensity based on power distribution
            power_ratio = avg_power / max_power if max_power > 0 else 0.5
            fallback_intensity = min(power_ratio * 1.2, 1.0)  # Scale up slightly
            intensities.append(fallback_intensity)
            logger.debug(f"Fallback power intensity: {fallback_intensity:.2f}")
        
        # Default to moderate intensity if no data available
        if not intensities:
            default_intensity = 0.6
            logger.debug(f"Using default intensity: {default_intensity}")
            return default_intensity
        
        # Return average of calculated intensities
        final_intensity = sum(intensities) / len(intensities)
        logger.info(f"Calculated workout intensity: {final_intensity:.2f}")
        return final_intensity

def enhance_device_identification(workout_data: Dict[str, Any], 
                                user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Enhance workout data with proper device identification
    
    Args:
        workout_data: Workout data dictionary
        user_profile: Optional user profile with FTP, max HR, etc.
        
    Returns:
        Enhanced workout data with device identification
    """
    identifier = DeviceIdentifier()
    
    # Extract device information
    workout_type = workout_data.get('workout_type', 'bike')
    device_name = workout_data.get('device_name')
    device_address = workout_data.get('device_address')
    
    # Identify device
    device_info = identifier.identify_device(workout_type, device_name, device_address)
    
    # Calculate workout intensity
    user_ftp = user_profile.get('ftp') if user_profile else None
    user_max_hr = user_profile.get('max_heart_rate') if user_profile else None
    
    workout_intensity = identifier.calculate_workout_intensity(
        avg_power=workout_data.get('avg_power'),
        max_power=workout_data.get('max_power'),
        avg_heart_rate=workout_data.get('avg_heart_rate'),
        max_heart_rate=workout_data.get('max_heart_rate'),
        user_ftp=user_ftp,
        user_max_hr=user_max_hr
    )
    
    # Get training load multiplier
    training_load_multiplier = identifier.get_training_load_multiplier(device_info, workout_intensity)
    
    # Enhance workout data
    workout_data.update({
        'device_manufacturer_id': device_info.manufacturer_id,
        'device_product_id': device_info.product_id,
        'device_name_identified': device_info.device_name,
        'sport_type': device_info.sport_type.value,
        'sub_sport_type': device_info.sub_sport_type.value,
        'activity_type': device_info.activity_type.value,
        'workout_intensity': workout_intensity,
        'training_load_multiplier': training_load_multiplier,
        'device_supports_power': device_info.supports_power,
        'device_supports_heart_rate': device_info.supports_heart_rate,
        'device_supports_cadence': device_info.supports_cadence
    })
    
    logger.info(f"Enhanced device identification: {device_info.device_name} "
               f"(manufacturer: {device_info.manufacturer_id}, product: {device_info.product_id})")
    
    return workout_data

# Example usage and testing
if __name__ == "__main__":
    # Test device identification
    identifier = DeviceIdentifier()
    
    # Test bike identification
    bike_info = identifier.identify_device("bike", "Rogue Echo Bike")
    print(f"Bike Device: {bike_info.device_name}")
    print(f"  Manufacturer: {bike_info.manufacturer_id}")
    print(f"  Product: {bike_info.product_id}")
    print(f"  Sport: {bike_info.sport_type.value}")
    print(f"  Sub-sport: {bike_info.sub_sport_type.value}")
    
    # Test rower identification
    rower_info = identifier.identify_device("rower", "Rogue Echo Rower")
    print(f"\nRower Device: {rower_info.device_name}")
    print(f"  Manufacturer: {rower_info.manufacturer_id}")
    print(f"  Product: {rower_info.product_id}")
    print(f"  Sport: {rower_info.sport_type.value}")
    print(f"  Sub-sport: {rower_info.sub_sport_type.value}")
    
    # Test workout intensity calculation
    intensity = identifier.calculate_workout_intensity(
        avg_power=200, user_ftp=250, avg_heart_rate=150, user_max_hr=190
    )
    print(f"\nWorkout Intensity: {intensity:.2f}")
    
    # Test training load multiplier
    multiplier = identifier.get_training_load_multiplier(bike_info, intensity)
    print(f"Training Load Multiplier: {multiplier:.2f}")