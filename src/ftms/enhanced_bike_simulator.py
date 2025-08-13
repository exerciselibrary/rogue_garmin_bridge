#!/usr/bin/env python3
"""
Enhanced FTMS Bike Simulator with Realistic Data Generation

This module provides an enhanced bike simulator that uses statistical models
derived from real workout data to generate realistic workout patterns.
"""

import json
import random
import time
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

# Set up basic logging for testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('enhanced_bike_simulator')


@dataclass
class WorkoutPhaseConfig:
    """Configuration for a workout phase"""
    name: str
    duration_range: Tuple[float, float]
    power_mean: float
    power_std: float
    power_range: Tuple[float, float]
    cadence_mean: float
    cadence_std: float
    cadence_range: Tuple[float, float]
    speed_mean: float
    speed_std: float
    speed_range: Tuple[float, float]
    heart_rate_mean: float
    heart_rate_std: float
    heart_rate_range: Tuple[float, float]


class EnhancedBikeSimulator:
    """
    Enhanced bike simulator that generates realistic workout data based on
    statistical analysis of real workout sessions.
    """
    
    def __init__(self, workout_profile: str = "standard", patterns_file: str = "src/utils/workout_patterns.json"):
        """
        Initialize the enhanced bike simulator.
        
        Args:
            workout_profile: Type of workout ("standard", "intervals", "endurance")
            patterns_file: Path to the statistical patterns file
        """
        self.workout_profile = workout_profile
        self.patterns_file = patterns_file
        self.workout_phases: List[WorkoutPhaseConfig] = []
        self.correlations: Dict[str, float] = {}
        self.overall_stats: Dict[str, Any] = {}
        self.data_quality: Dict[str, Any] = {}
        
        # Current workout state
        self.workout_duration = 0
        self.current_phase_index = 0
        self.phase_start_time = 0
        self.total_distance = 0.0
        self.total_calories = 0
        self.previous_values = {
            'power': 0,
            'cadence': 0,
            'speed': 0,
            'heart_rate': 90
        }
        
        # Load statistical patterns
        self._load_patterns()
        
        # Configure workout phases based on profile
        self._configure_workout_phases()
        
        logger.info(f"Enhanced bike simulator initialized with {workout_profile} profile")
    
    def _load_patterns(self) -> None:
        """Load statistical patterns from the analysis file"""
        try:
            with open(self.patterns_file, 'r') as f:
                patterns = json.load(f)
            
            self.correlations = patterns.get('correlations', {})
            self.overall_stats = patterns.get('overall_stats', {})
            self.data_quality = patterns.get('data_quality', {})
            
            # Load phase configurations
            phases_data = patterns.get('phases', {})
            for phase_name, phase_data in phases_data.items():
                phase_config = WorkoutPhaseConfig(
                    name=phase_name,
                    duration_range=tuple(phase_data['duration_range']),
                    power_mean=phase_data['power']['mean'],
                    power_std=phase_data['power']['std'],
                    power_range=tuple(phase_data['power']['range']),
                    cadence_mean=phase_data['cadence']['mean'],
                    cadence_std=phase_data['cadence']['std'],
                    cadence_range=tuple(phase_data['cadence']['range']),
                    speed_mean=phase_data['speed']['mean'],
                    speed_std=phase_data['speed']['std'],
                    speed_range=tuple(phase_data['speed']['range']),
                    heart_rate_mean=phase_data['heart_rate']['mean'],
                    heart_rate_std=phase_data['heart_rate']['std'],
                    heart_rate_range=tuple(phase_data['heart_rate']['range'])
                )
                self.workout_phases.append(phase_config)
            
            logger.info(f"Loaded {len(self.workout_phases)} workout phases from patterns file")
            
        except FileNotFoundError:
            logger.error(f"Patterns file not found: {self.patterns_file}")
            self._create_default_phases()
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
            self._create_default_phases()
    
    def _create_default_phases(self) -> None:
        """Create default workout phases if patterns file is not available"""
        logger.info("Creating default workout phases")
        
        # Default phases based on typical workout structure
        self.workout_phases = [
            WorkoutPhaseConfig(
                name="warmup",
                duration_range=(60, 120),
                power_mean=80, power_std=20, power_range=(0, 150),
                cadence_mean=60, cadence_std=10, cadence_range=(0, 80),
                speed_mean=15, speed_std=5, speed_range=(0, 25),
                heart_rate_mean=100, heart_rate_std=10, heart_rate_range=(80, 120)
            ),
            WorkoutPhaseConfig(
                name="main_workout",
                duration_range=(300, 900),
                power_mean=200, power_std=40, power_range=(50, 300),
                cadence_mean=80, cadence_std=15, cadence_range=(40, 100),
                speed_mean=25, speed_std=8, speed_range=(10, 40),
                heart_rate_mean=150, heart_rate_std=15, heart_rate_range=(120, 180)
            ),
            WorkoutPhaseConfig(
                name="cooldown",
                duration_range=(60, 180),
                power_mean=60, power_std=15, power_range=(0, 100),
                cadence_mean=50, cadence_std=10, cadence_range=(20, 70),
                speed_mean=12, speed_std=4, speed_range=(5, 20),
                heart_rate_mean=110, heart_rate_std=10, heart_rate_range=(90, 130)
            )
        ]
        
        # Default correlations
        self.correlations = {
            'power_cadence': 0.8,
            'power_speed': 0.9,
            'cadence_speed': 0.85,
            'heart_rate_power': 0.7
        }
    
    def _configure_workout_phases(self) -> None:
        """Configure workout phases based on the selected profile"""
        if self.workout_profile == "intervals":
            self._configure_interval_workout()
        elif self.workout_profile == "endurance":
            self._configure_endurance_workout()
        # "standard" uses the phases as loaded from patterns
        
        logger.info(f"Configured {len(self.workout_phases)} phases for {self.workout_profile} workout")
    
    def _configure_interval_workout(self) -> None:
        """Configure phases for interval workout"""
        # Modify main workout phase to have higher intensity variations
        for phase in self.workout_phases:
            if phase.name == "main_workout":
                # Increase power range and variability for intervals
                phase.power_mean *= 1.2
                phase.power_std *= 1.5
                phase.power_range = (phase.power_range[0], phase.power_range[1] * 1.3)
                
                # Increase cadence variability
                phase.cadence_std *= 1.3
                
                # Increase heart rate for intervals
                phase.heart_rate_mean *= 1.1
                phase.heart_rate_std *= 1.2
    
    def _configure_endurance_workout(self) -> None:
        """Configure phases for endurance workout"""
        # Extend main workout duration and reduce intensity variations
        for phase in self.workout_phases:
            if phase.name == "main_workout":
                # Extend duration for endurance
                phase.duration_range = (phase.duration_range[0] * 2, phase.duration_range[1] * 3)
                
                # Reduce power variability for steady endurance
                phase.power_std *= 0.7
                phase.cadence_std *= 0.8
                phase.speed_std *= 0.8
                phase.heart_rate_std *= 0.9
    
    def start_workout(self) -> None:
        """Start a new workout session"""
        self.workout_duration = 0
        self.current_phase_index = 0
        self.phase_start_time = 0
        self.total_distance = 0.0
        self.total_calories = 0
        
        # Reset previous values to realistic starting points
        self.previous_values = {
            'power': 0,
            'cadence': 0,
            'speed': 0,
            'heart_rate': 90
        }
        
        logger.info(f"Started {self.workout_profile} workout with {len(self.workout_phases)} phases")
    
    def generate_data_point(self, elapsed_time: int) -> Dict[str, Any]:
        """
        Generate a realistic data point for the current workout time.
        
        Args:
            elapsed_time: Elapsed time in seconds since workout start
            
        Returns:
            Dictionary containing realistic bike workout data
        """
        self.workout_duration = elapsed_time
        
        # Determine current phase
        current_phase = self._get_current_phase()
        if current_phase is None:
            # Workout is complete, return minimal data
            return self._generate_end_workout_data()
        
        # Generate base values for current phase
        base_power = self._generate_phase_value(
            current_phase.power_mean,
            current_phase.power_std,
            current_phase.power_range
        )
        
        base_cadence = self._generate_phase_value(
            current_phase.cadence_mean,
            current_phase.cadence_std,
            current_phase.cadence_range
        )
        
        base_speed = self._generate_phase_value(
            current_phase.speed_mean,
            current_phase.speed_std,
            current_phase.speed_range
        )
        
        base_heart_rate = self._generate_phase_value(
            current_phase.heart_rate_mean,
            current_phase.heart_rate_std,
            current_phase.heart_rate_range
        )
        
        # Apply correlations to make values more realistic
        power, cadence, speed, heart_rate = self._apply_correlations(
            base_power, base_cadence, base_speed, base_heart_rate
        )
        
        # Add workout profile-specific variations
        power, cadence, speed, heart_rate = self._apply_profile_variations(
            power, cadence, speed, heart_rate, current_phase
        )
        
        # Apply smoothing to prevent unrealistic jumps
        power, cadence, speed, heart_rate = self._apply_smoothing(
            power, cadence, speed, heart_rate
        )
        
        # Add realistic data quality issues
        power, cadence, speed, heart_rate = self._apply_data_quality_effects(
            power, cadence, speed, heart_rate
        )
        
        # Update accumulated metrics
        self._update_accumulated_metrics(speed, power)
        
        # Store current values for next iteration
        self.previous_values = {
            'power': power,
            'cadence': cadence,
            'speed': speed,
            'heart_rate': heart_rate
        }
        
        # Create data packet
        data = {
            "type": "bike",
            "instantaneous_power": int(power),
            "instantaneous_cadence": int(cadence),
            "instantaneous_speed": round(speed, 2),
            "heart_rate": int(heart_rate),
            "total_distance": round(self.total_distance, 1),
            "total_calories": self.total_calories,
            "timestamp": elapsed_time,
            "elapsed_time": elapsed_time,
            "workout_phase": current_phase.name,
            "data_id": f"{elapsed_time}_{int(time.time() * 1000) % 1000}"
        }
        
        return data
    
    def _get_current_phase(self) -> Optional[WorkoutPhaseConfig]:
        """Get the current workout phase based on elapsed time"""
        if self.current_phase_index >= len(self.workout_phases):
            return None
        
        current_phase = self.workout_phases[self.current_phase_index]
        phase_elapsed = self.workout_duration - self.phase_start_time
        
        # Determine phase duration (random within range)
        if not hasattr(current_phase, '_actual_duration'):
            current_phase._actual_duration = random.uniform(
                current_phase.duration_range[0],
                current_phase.duration_range[1]
            )
        
        # Check if we should move to next phase
        if phase_elapsed >= current_phase._actual_duration:
            self.current_phase_index += 1
            self.phase_start_time = self.workout_duration
            
            if self.current_phase_index < len(self.workout_phases):
                next_phase = self.workout_phases[self.current_phase_index]
                logger.info(f"Transitioning to phase: {next_phase.name}")
                return next_phase
            else:
                return None
        
        return current_phase
    
    def _generate_phase_value(self, mean: float, std: float, value_range: Tuple[float, float]) -> float:
        """Generate a value within phase parameters"""
        # Generate value using normal distribution
        value = random.gauss(mean, std)
        
        # Clamp to range
        value = max(value_range[0], min(value_range[1], value))
        
        return value
    
    def _apply_correlations(self, power: float, cadence: float, speed: float, heart_rate: float) -> Tuple[float, float, float, float]:
        """Apply correlations between metrics to make them more realistic"""
        # Get correlation coefficients
        power_cadence_corr = self.correlations.get('power_cadence', 0.8)
        power_speed_corr = self.correlations.get('power_speed', 0.9)
        cadence_speed_corr = self.correlations.get('cadence_speed', 0.85)
        heart_rate_power_corr = self.correlations.get('heart_rate_power', 0.7)
        
        # Apply power-cadence correlation
        if power > 0:
            cadence_adjustment = (power - 100) * 0.2 * power_cadence_corr
            cadence = max(0, cadence + cadence_adjustment)
        
        # Apply power-speed correlation
        if power > 0:
            speed_adjustment = (power - 100) * 0.1 * power_speed_corr
            speed = max(0, speed + speed_adjustment)
        
        # Apply cadence-speed correlation (fine-tuning)
        if cadence > 0:
            speed_fine_adjustment = (cadence - 60) * 0.15 * cadence_speed_corr
            speed = max(0, speed + speed_fine_adjustment)
        
        # Apply heart rate-power correlation
        if power > 0:
            hr_adjustment = (power - 150) * 0.3 * heart_rate_power_corr
            heart_rate = max(60, min(220, heart_rate + hr_adjustment))
        
        return power, cadence, speed, heart_rate
    
    def _apply_profile_variations(self, power: float, cadence: float, speed: float, heart_rate: float, phase: WorkoutPhaseConfig) -> Tuple[float, float, float, float]:
        """Apply workout profile-specific variations"""
        if self.workout_profile == "intervals" and phase.name == "main_workout":
            # Create interval pattern
            interval_period = 30  # 30-second intervals
            phase_time = self.workout_duration - self.phase_start_time
            cycle_time = phase_time % (interval_period * 2)
            
            if cycle_time < interval_period:
                # High intensity interval
                power *= 1.4
                cadence *= 1.2
                speed *= 1.3
                heart_rate *= 1.1
            else:
                # Recovery interval
                power *= 0.6
                cadence *= 0.8
                speed *= 0.7
                heart_rate *= 0.95
        
        elif self.workout_profile == "endurance":
            # Add slight variations to prevent monotony
            variation_factor = 0.05 * random.uniform(-1, 1)
            power *= (1 + variation_factor)
            cadence *= (1 + variation_factor * 0.5)
            speed *= (1 + variation_factor * 0.7)
            heart_rate *= (1 + variation_factor * 0.3)
        
        return power, cadence, speed, heart_rate
    
    def _apply_smoothing(self, power: float, cadence: float, speed: float, heart_rate: float) -> Tuple[float, float, float, float]:
        """Apply smoothing to prevent unrealistic jumps between data points"""
        smoothing_factor = 0.7  # How much to blend with previous values
        
        # Smooth each metric
        power = power * (1 - smoothing_factor) + self.previous_values['power'] * smoothing_factor
        cadence = cadence * (1 - smoothing_factor) + self.previous_values['cadence'] * smoothing_factor
        speed = speed * (1 - smoothing_factor) + self.previous_values['speed'] * smoothing_factor
        heart_rate = heart_rate * (1 - smoothing_factor) + self.previous_values['heart_rate'] * smoothing_factor
        
        return power, cadence, speed, heart_rate
    
    def _apply_data_quality_effects(self, power: float, cadence: float, speed: float, heart_rate: float) -> Tuple[float, float, float, float]:
        """Apply realistic data quality effects based on analysis"""
        # Get data quality percentages
        zero_power_pct = self.data_quality.get('zero_power_percentage', 4.3)
        zero_cadence_pct = self.data_quality.get('zero_cadence_percentage', 4.3)
        zero_speed_pct = self.data_quality.get('zero_speed_percentage', 4.3)
        
        # Occasionally set values to zero based on real data patterns
        if random.random() * 100 < zero_power_pct:
            power = 0
        
        if random.random() * 100 < zero_cadence_pct:
            cadence = 0
        
        if random.random() * 100 < zero_speed_pct:
            speed = 0
        
        # Add small random noise to simulate sensor variations
        power += random.gauss(0, 2)
        cadence += random.gauss(0, 1)
        speed += random.gauss(0, 0.5)
        heart_rate += random.gauss(0, 2)
        
        # Ensure non-negative values
        power = max(0, power)
        cadence = max(0, cadence)
        speed = max(0, speed)
        heart_rate = max(60, min(220, heart_rate))
        
        return power, cadence, speed, heart_rate
    
    def _update_accumulated_metrics(self, speed: float, power: float) -> None:
        """Update accumulated distance and calories"""
        # Update distance (speed in km/h -> m/s -> m per second)
        if speed > 0:
            speed_ms = speed * 0.277778  # km/h to m/s
            distance_increment = speed_ms * 1.0  # 1 second
            self.total_distance += distance_increment
        
        # Update calories (simplified model: ~4 calories per minute per 100W)
        if power > 0:
            calories_per_second = (power * 0.04 * 60) / 3600
            self.total_calories += int(calories_per_second)
    
    def _generate_end_workout_data(self) -> Dict[str, Any]:
        """Generate final data point when workout is complete"""
        return {
            "type": "bike",
            "instantaneous_power": 0,
            "instantaneous_cadence": 0,
            "instantaneous_speed": 0.0,
            "heart_rate": max(90, self.previous_values['heart_rate'] - 10),
            "total_distance": round(self.total_distance, 1),
            "total_calories": self.total_calories,
            "timestamp": self.workout_duration,
            "elapsed_time": self.workout_duration,
            "workout_phase": "complete",
            "is_final_point": True,
            "data_id": f"final_{int(time.time())}"
        }
    
    def get_workout_summary(self) -> Dict[str, Any]:
        """Get summary of the current workout configuration"""
        return {
            "profile": self.workout_profile,
            "phases": [
                {
                    "name": phase.name,
                    "duration_range": phase.duration_range,
                    "power_range": phase.power_range,
                    "cadence_range": phase.cadence_range,
                    "speed_range": phase.speed_range,
                    "heart_rate_range": phase.heart_rate_range
                }
                for phase in self.workout_phases
            ],
            "correlations": self.correlations,
            "data_quality": self.data_quality
        }


def main():
    """Test the enhanced bike simulator"""
    print("Testing Enhanced Bike Simulator")
    print("=" * 50)
    
    # Test different workout profiles
    profiles = ["standard", "intervals", "endurance"]
    
    for profile in profiles:
        print(f"\nTesting {profile} profile:")
        simulator = EnhancedBikeSimulator(workout_profile=profile)
        simulator.start_workout()
        
        # Generate some sample data points
        for elapsed_time in [0, 30, 60, 120, 300, 600]:
            data = simulator.generate_data_point(elapsed_time)
            print(f"  {elapsed_time:3d}s: Power={data['instantaneous_power']:3d}W, "
                  f"Cadence={data['instantaneous_cadence']:2d}RPM, "
                  f"Speed={data['instantaneous_speed']:5.1f}km/h, "
                  f"HR={data['heart_rate']:3d}BPM, "
                  f"Phase={data['workout_phase']}")


if __name__ == "__main__":
    main()