#!/usr/bin/env python3
"""
Configurable Workout Scenarios and Error Injection System

This module provides configurable workout scenarios and error injection
capabilities for comprehensive testing of the FTMS bridge system.
"""

import json
import random
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('workout_scenarios')


class ErrorType(Enum):
    """Types of errors that can be injected"""
    CONNECTION_DROP = "connection_drop"
    INVALID_DATA = "invalid_data"
    DATA_GAPS = "data_gaps"
    SENSOR_MALFUNCTION = "sensor_malfunction"
    BLUETOOTH_INTERFERENCE = "bluetooth_interference"
    POWER_SPIKE = "power_spike"
    HEART_RATE_DROPOUT = "heart_rate_dropout"


class DataQuality(Enum):
    """Data quality indicators"""
    GOOD = "good"
    ESTIMATED = "estimated"
    INTERPOLATED = "interpolated"
    CORRUPTED = "corrupted"
    MISSING = "missing"


@dataclass
class ErrorInjectionConfig:
    """Configuration for error injection"""
    error_type: ErrorType
    probability: float  # 0.0 to 1.0
    duration_range: tuple  # (min_seconds, max_seconds)
    severity: float  # 0.0 to 1.0
    recovery_time: float  # seconds
    description: str


@dataclass
class WorkoutScenarioConfig:
    """Configuration for a complete workout scenario"""
    name: str
    description: str
    device_type: str  # "bike" or "rower"
    duration_minutes: int
    difficulty_level: str  # "easy", "moderate", "hard", "extreme"
    workout_type: str  # "standard", "intervals", "endurance", "recovery"
    error_injection: List[ErrorInjectionConfig]
    custom_phases: Optional[List[Dict[str, Any]]] = None
    data_quality_target: float = 0.95  # Target percentage of good data


class WorkoutScenarioManager:
    """
    Manages configurable workout scenarios with error injection capabilities.
    """
    
    def __init__(self, scenarios_file: str = "src/ftms/workout_scenarios.json"):
        """
        Initialize the workout scenario manager.
        
        Args:
            scenarios_file: Path to the scenarios configuration file
        """
        self.scenarios_file = scenarios_file
        self.scenarios: Dict[str, WorkoutScenarioConfig] = {}
        self.current_scenario: Optional[WorkoutScenarioConfig] = None
        self.active_errors: List[Dict[str, Any]] = []
        self.error_history: List[Dict[str, Any]] = []
        
        # Load or create default scenarios
        self._load_scenarios()
        
        logger.info(f"Workout scenario manager initialized with {len(self.scenarios)} scenarios")
    
    def _load_scenarios(self) -> None:
        """Load scenarios from file or create defaults"""
        try:
            with open(self.scenarios_file, 'r') as f:
                scenarios_data = json.load(f)
            
            for name, data in scenarios_data.items():
                # Convert error injection configs
                error_configs = []
                for error_data in data.get('error_injection', []):
                    error_config = ErrorInjectionConfig(
                        error_type=ErrorType(error_data['error_type']),
                        probability=error_data['probability'],
                        duration_range=tuple(error_data['duration_range']),
                        severity=error_data['severity'],
                        recovery_time=error_data['recovery_time'],
                        description=error_data['description']
                    )
                    error_configs.append(error_config)
                
                scenario = WorkoutScenarioConfig(
                    name=data['name'],
                    description=data['description'],
                    device_type=data['device_type'],
                    duration_minutes=data['duration_minutes'],
                    difficulty_level=data['difficulty_level'],
                    workout_type=data['workout_type'],
                    error_injection=error_configs,
                    custom_phases=data.get('custom_phases'),
                    data_quality_target=data.get('data_quality_target', 0.95)
                )
                
                self.scenarios[name] = scenario
            
            logger.info(f"Loaded {len(self.scenarios)} scenarios from {self.scenarios_file}")
            
        except FileNotFoundError:
            logger.info("Scenarios file not found, creating default scenarios")
            self._create_default_scenarios()
            self._save_scenarios()
        except Exception as e:
            logger.error(f"Error loading scenarios: {e}")
            self._create_default_scenarios()
    
    def _create_default_scenarios(self) -> None:
        """Create default workout scenarios"""
        
        # Basic bike workout - no errors
        self.scenarios["bike_basic"] = WorkoutScenarioConfig(
            name="bike_basic",
            description="Basic bike workout with no error injection",
            device_type="bike",
            duration_minutes=20,
            difficulty_level="easy",
            workout_type="standard",
            error_injection=[],
            data_quality_target=1.0
        )
        
        # Bike workout with connection issues
        self.scenarios["bike_connection_issues"] = WorkoutScenarioConfig(
            name="bike_connection_issues",
            description="Bike workout with intermittent connection drops",
            device_type="bike",
            duration_minutes=30,
            difficulty_level="moderate",
            workout_type="standard",
            error_injection=[
                ErrorInjectionConfig(
                    error_type=ErrorType.CONNECTION_DROP,
                    probability=0.1,
                    duration_range=(2, 8),
                    severity=1.0,
                    recovery_time=3.0,
                    description="Bluetooth connection drops"
                ),
                ErrorInjectionConfig(
                    error_type=ErrorType.DATA_GAPS,
                    probability=0.05,
                    duration_range=(1, 3),
                    severity=0.7,
                    recovery_time=1.0,
                    description="Missing data points"
                )
            ],
            data_quality_target=0.85
        )
        
        # Bike intervals with sensor issues
        self.scenarios["bike_intervals_sensor_issues"] = WorkoutScenarioConfig(
            name="bike_intervals_sensor_issues",
            description="High-intensity bike intervals with sensor malfunctions",
            device_type="bike",
            duration_minutes=25,
            difficulty_level="hard",
            workout_type="intervals",
            error_injection=[
                ErrorInjectionConfig(
                    error_type=ErrorType.SENSOR_MALFUNCTION,
                    probability=0.08,
                    duration_range=(5, 15),
                    severity=0.6,
                    recovery_time=2.0,
                    description="Power sensor gives erratic readings"
                ),
                ErrorInjectionConfig(
                    error_type=ErrorType.HEART_RATE_DROPOUT,
                    probability=0.12,
                    duration_range=(3, 10),
                    severity=0.8,
                    recovery_time=1.5,
                    description="Heart rate monitor disconnects"
                ),
                ErrorInjectionConfig(
                    error_type=ErrorType.POWER_SPIKE,
                    probability=0.03,
                    duration_range=(1, 2),
                    severity=0.9,
                    recovery_time=0.5,
                    description="Sudden power spikes"
                )
            ],
            data_quality_target=0.80
        )
        
        # Rower basic workout
        self.scenarios["rower_basic"] = WorkoutScenarioConfig(
            name="rower_basic",
            description="Basic rower workout with minimal errors",
            device_type="rower",
            duration_minutes=25,
            difficulty_level="moderate",
            workout_type="standard",
            error_injection=[
                ErrorInjectionConfig(
                    error_type=ErrorType.DATA_GAPS,
                    probability=0.02,
                    duration_range=(1, 2),
                    severity=0.3,
                    recovery_time=0.5,
                    description="Occasional missing data points"
                )
            ],
            data_quality_target=0.95
        )
        
        # Rower endurance with interference
        self.scenarios["rower_endurance_interference"] = WorkoutScenarioConfig(
            name="rower_endurance_interference",
            description="Long rower workout with Bluetooth interference",
            device_type="rower",
            duration_minutes=45,
            difficulty_level="moderate",
            workout_type="endurance",
            error_injection=[
                ErrorInjectionConfig(
                    error_type=ErrorType.BLUETOOTH_INTERFERENCE,
                    probability=0.06,
                    duration_range=(2, 6),
                    severity=0.5,
                    recovery_time=2.0,
                    description="Bluetooth interference causes data corruption"
                ),
                ErrorInjectionConfig(
                    error_type=ErrorType.INVALID_DATA,
                    probability=0.04,
                    duration_range=(1, 3),
                    severity=0.4,
                    recovery_time=1.0,
                    description="Invalid sensor readings"
                )
            ],
            data_quality_target=0.88
        )
        
        # Extreme stress test scenario
        self.scenarios["stress_test_extreme"] = WorkoutScenarioConfig(
            name="stress_test_extreme",
            description="Extreme stress test with multiple error types",
            device_type="bike",
            duration_minutes=15,
            difficulty_level="extreme",
            workout_type="intervals",
            error_injection=[
                ErrorInjectionConfig(
                    error_type=ErrorType.CONNECTION_DROP,
                    probability=0.15,
                    duration_range=(1, 5),
                    severity=1.0,
                    recovery_time=2.0,
                    description="Frequent connection drops"
                ),
                ErrorInjectionConfig(
                    error_type=ErrorType.SENSOR_MALFUNCTION,
                    probability=0.12,
                    duration_range=(3, 8),
                    severity=0.8,
                    recovery_time=1.5,
                    description="Multiple sensor malfunctions"
                ),
                ErrorInjectionConfig(
                    error_type=ErrorType.INVALID_DATA,
                    probability=0.10,
                    duration_range=(1, 4),
                    severity=0.7,
                    recovery_time=1.0,
                    description="Corrupted data packets"
                ),
                ErrorInjectionConfig(
                    error_type=ErrorType.POWER_SPIKE,
                    probability=0.08,
                    duration_range=(1, 2),
                    severity=1.0,
                    recovery_time=0.5,
                    description="Extreme power spikes"
                )
            ],
            data_quality_target=0.60
        )
        
        logger.info(f"Created {len(self.scenarios)} default scenarios")
    
    def _save_scenarios(self) -> None:
        """Save scenarios to file"""
        try:
            scenarios_data = {}
            for name, scenario in self.scenarios.items():
                # Convert to serializable format
                scenario_dict = asdict(scenario)
                # Convert enums to strings
                for error_config in scenario_dict['error_injection']:
                    error_config['error_type'] = error_config['error_type'].value
                
                scenarios_data[name] = scenario_dict
            
            with open(self.scenarios_file, 'w') as f:
                json.dump(scenarios_data, f, indent=2)
            
            logger.info(f"Saved scenarios to {self.scenarios_file}")
            
        except Exception as e:
            logger.error(f"Error saving scenarios: {e}")
    
    def get_available_scenarios(self) -> List[str]:
        """Get list of available scenario names"""
        return list(self.scenarios.keys())
    
    def get_scenario_info(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific scenario"""
        if scenario_name not in self.scenarios:
            return None
        
        scenario = self.scenarios[scenario_name]
        return {
            "name": scenario.name,
            "description": scenario.description,
            "device_type": scenario.device_type,
            "duration_minutes": scenario.duration_minutes,
            "difficulty_level": scenario.difficulty_level,
            "workout_type": scenario.workout_type,
            "error_types": [error.error_type.value for error in scenario.error_injection],
            "data_quality_target": scenario.data_quality_target
        }
    
    def load_scenario(self, scenario_name: str) -> bool:
        """Load a specific scenario for execution"""
        if scenario_name not in self.scenarios:
            logger.error(f"Scenario '{scenario_name}' not found")
            return False
        
        self.current_scenario = self.scenarios[scenario_name]
        self.active_errors = []
        self.error_history = []
        
        logger.info(f"Loaded scenario: {scenario_name}")
        return True
    
    def should_inject_error(self, elapsed_time: int) -> Optional[ErrorInjectionConfig]:
        """
        Determine if an error should be injected at the current time.
        
        Args:
            elapsed_time: Current elapsed time in seconds
            
        Returns:
            ErrorInjectionConfig if an error should be injected, None otherwise
        """
        if not self.current_scenario:
            return None
        
        # Check if any errors are currently active
        current_time = time.time()
        self.active_errors = [
            error for error in self.active_errors 
            if current_time < error['end_time']
        ]
        
        # Don't inject new errors if we already have active ones
        if self.active_errors:
            return None
        
        # Check each error type for injection
        for error_config in self.current_scenario.error_injection:
            if random.random() < error_config.probability / 60:  # Per-second probability
                # Inject this error
                duration = random.uniform(
                    error_config.duration_range[0],
                    error_config.duration_range[1]
                )
                
                error_instance = {
                    'config': error_config,
                    'start_time': current_time,
                    'end_time': current_time + duration,
                    'elapsed_time': elapsed_time,
                    'duration': duration
                }
                
                self.active_errors.append(error_instance)
                self.error_history.append(error_instance.copy())
                
                logger.warning(f"Injecting error: {error_config.error_type.value} "
                             f"for {duration:.1f}s at {elapsed_time}s")
                
                return error_config
        
        return None
    
    def apply_error_to_data(self, data: Dict[str, Any], error_config: ErrorInjectionConfig) -> Dict[str, Any]:
        """
        Apply error effects to workout data.
        
        Args:
            data: Original workout data
            error_config: Error configuration to apply
            
        Returns:
            Modified workout data with error effects
        """
        modified_data = data.copy()
        error_type = error_config.error_type
        severity = error_config.severity
        
        if error_type == ErrorType.CONNECTION_DROP:
            # Simulate connection drop - return None or empty data
            return None
        
        elif error_type == ErrorType.INVALID_DATA:
            # Corrupt some data values
            if 'instantaneous_power' in modified_data and random.random() < severity:
                modified_data['instantaneous_power'] = -1  # Invalid power
            
            if 'heart_rate' in modified_data and random.random() < severity:
                modified_data['heart_rate'] = 0  # Invalid heart rate
            
            if 'instantaneous_cadence' in modified_data and random.random() < severity:
                modified_data['instantaneous_cadence'] = 999  # Invalid cadence
            
            modified_data['data_quality'] = DataQuality.CORRUPTED.value
        
        elif error_type == ErrorType.DATA_GAPS:
            # Randomly zero out some values
            if random.random() < severity:
                if 'instantaneous_power' in modified_data:
                    modified_data['instantaneous_power'] = 0
                if 'instantaneous_cadence' in modified_data:
                    modified_data['instantaneous_cadence'] = 0
                if 'stroke_rate' in modified_data:
                    modified_data['stroke_rate'] = 0
            
            modified_data['data_quality'] = DataQuality.MISSING.value
        
        elif error_type == ErrorType.SENSOR_MALFUNCTION:
            # Add noise and drift to sensor readings
            noise_factor = severity * 0.3
            
            if 'instantaneous_power' in modified_data:
                noise = random.gauss(0, modified_data['instantaneous_power'] * noise_factor)
                modified_data['instantaneous_power'] = max(0, int(modified_data['instantaneous_power'] + noise))
            
            if 'instantaneous_cadence' in modified_data:
                noise = random.gauss(0, modified_data['instantaneous_cadence'] * noise_factor)
                modified_data['instantaneous_cadence'] = max(0, int(modified_data['instantaneous_cadence'] + noise))
            
            if 'stroke_rate' in modified_data:
                noise = random.gauss(0, modified_data['stroke_rate'] * noise_factor)
                modified_data['stroke_rate'] = max(0, int(modified_data['stroke_rate'] + noise))
            
            modified_data['data_quality'] = DataQuality.ESTIMATED.value
        
        elif error_type == ErrorType.BLUETOOTH_INTERFERENCE:
            # Simulate interference - corrupt random fields
            fields_to_corrupt = ['instantaneous_power', 'instantaneous_cadence', 'stroke_rate', 'heart_rate']
            for field in fields_to_corrupt:
                if field in modified_data and random.random() < severity * 0.5:
                    # Add random interference
                    if isinstance(modified_data[field], (int, float)):
                        interference = random.randint(-50, 50)
                        modified_data[field] = max(0, modified_data[field] + interference)
            
            modified_data['data_quality'] = DataQuality.CORRUPTED.value
        
        elif error_type == ErrorType.POWER_SPIKE:
            # Sudden power spike
            if 'instantaneous_power' in modified_data:
                spike_multiplier = 1 + (severity * random.uniform(2, 5))
                modified_data['instantaneous_power'] = int(modified_data['instantaneous_power'] * spike_multiplier)
            
            modified_data['data_quality'] = DataQuality.ESTIMATED.value
        
        elif error_type == ErrorType.HEART_RATE_DROPOUT:
            # Heart rate monitor disconnects
            if 'heart_rate' in modified_data:
                modified_data['heart_rate'] = 0
            
            modified_data['data_quality'] = DataQuality.MISSING.value
        
        # Add error metadata
        modified_data['error_injected'] = error_type.value
        modified_data['error_severity'] = severity
        
        return modified_data
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about injected errors"""
        if not self.error_history:
            return {"total_errors": 0}
        
        error_counts = {}
        total_error_time = 0
        
        for error in self.error_history:
            error_type = error['config'].error_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            total_error_time += error['duration']
        
        return {
            "total_errors": len(self.error_history),
            "error_counts": error_counts,
            "total_error_time": total_error_time,
            "active_errors": len(self.active_errors)
        }
    
    def create_custom_scenario(self, name: str, config: Dict[str, Any]) -> bool:
        """
        Create a custom workout scenario.
        
        Args:
            name: Name for the new scenario
            config: Scenario configuration dictionary
            
        Returns:
            True if scenario was created successfully
        """
        try:
            # Convert error injection configs
            error_configs = []
            for error_data in config.get('error_injection', []):
                error_config = ErrorInjectionConfig(
                    error_type=ErrorType(error_data['error_type']),
                    probability=error_data['probability'],
                    duration_range=tuple(error_data['duration_range']),
                    severity=error_data['severity'],
                    recovery_time=error_data['recovery_time'],
                    description=error_data['description']
                )
                error_configs.append(error_config)
            
            scenario = WorkoutScenarioConfig(
                name=name,
                description=config['description'],
                device_type=config['device_type'],
                duration_minutes=config['duration_minutes'],
                difficulty_level=config['difficulty_level'],
                workout_type=config['workout_type'],
                error_injection=error_configs,
                custom_phases=config.get('custom_phases'),
                data_quality_target=config.get('data_quality_target', 0.95)
            )
            
            self.scenarios[name] = scenario
            self._save_scenarios()
            
            logger.info(f"Created custom scenario: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating custom scenario: {e}")
            return False


def main():
    """Test the workout scenarios system"""
    print("Testing Workout Scenarios System")
    print("=" * 50)
    
    manager = WorkoutScenarioManager()
    
    # List available scenarios
    scenarios = manager.get_available_scenarios()
    print(f"\nAvailable scenarios: {scenarios}")
    
    # Test each scenario
    for scenario_name in scenarios[:3]:  # Test first 3 scenarios
        print(f"\nTesting scenario: {scenario_name}")
        info = manager.get_scenario_info(scenario_name)
        print(f"  Description: {info['description']}")
        print(f"  Device: {info['device_type']}")
        print(f"  Duration: {info['duration_minutes']} minutes")
        print(f"  Difficulty: {info['difficulty_level']}")
        print(f"  Error types: {info['error_types']}")
        
        # Load scenario and simulate some error injection
        manager.load_scenario(scenario_name)
        
        # Simulate 60 seconds of workout
        error_count = 0
        for elapsed_time in range(0, 60, 5):
            error_config = manager.should_inject_error(elapsed_time)
            if error_config:
                error_count += 1
                print(f"    {elapsed_time}s: Error injected - {error_config.error_type.value}")
        
        stats = manager.get_error_statistics()
        print(f"  Total errors in simulation: {stats['total_errors']}")


if __name__ == "__main__":
    main()