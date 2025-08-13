#!/usr/bin/env python3
"""
Enhanced FTMS Rower Simulator with Realistic Data Generation

This module provides an enhanced rower simulator that generates realistic
rowing workout patterns based on physiological and biomechanical principles.
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
logger = logging.getLogger('enhanced_rower_simulator')


@dataclass
class RowerPhaseConfig:
    """Configuration for a rower workout phase"""
    name: str
    duration_range: Tuple[float, float]
    power_mean: float
    power_std: float
    power_range: Tuple[float, float]
    stroke_rate_mean: float
    stroke_rate_std: float
    stroke_rate_range: Tuple[float, float]
    speed_mean: float  # m/s for rowing
    speed_std: float
    speed_range: Tuple[float, float]
    heart_rate_mean: float
    heart_rate_std: float
    heart_rate_range: Tuple[float, float]


class EnhancedRowerSimulator:
    """
    Enhanced rower simulator that generates realistic rowing workout data
    based on rowing-specific biomechanics and training patterns.
    """
    
    def __init__(self, workout_profile: str = "standard"):
        """
        Initialize the enhanced rower simulator.
        
        Args:
            workout_profile: Type of workout ("standard", "intervals", "endurance")
        """
        self.workout_profile = workout_profile
        self.workout_phases: List[RowerPhaseConfig] = []
        
        # Rowing-specific correlations (different from cycling)
        self.correlations = {
            'power_stroke_rate': 0.65,  # Lower correlation than bike power-cadence
            'power_speed': 0.95,        # Very high correlation for rowing
            'stroke_rate_speed': 0.70,  # Moderate correlation
            'heart_rate_power': 0.80    # Higher than cycling due to full-body nature
        }
        
        # Current workout state
        self.workout_duration = 0
        self.current_phase_index = 0
        self.phase_start_time = 0
        self.total_distance = 0.0
        self.total_calories = 0
        self.total_strokes = 0
        self.previous_values = {
            'power': 0,
            'stroke_rate': 0,
            'speed': 0,
            'heart_rate': 90
        }
        
        # Configure workout phases
        self._configure_workout_phases()
        
        logger.info(f"Enhanced rower simulator initialized with {workout_profile} profile")
    
    def _configure_workout_phases(self) -> None:
        """Configure rower-specific workout phases"""
        # Base phases for rowing (different characteristics than cycling)
        base_phases = [
            RowerPhaseConfig(
                name="warmup",
                duration_range=(180, 300),  # Longer warmup for rowing
                power_mean=120, power_std=25, power_range=(50, 180),
                stroke_rate_mean=20, stroke_rate_std=3, stroke_rate_range=(16, 26),
                speed_mean=2.2, speed_std=0.3, speed_range=(1.5, 2.8),  # m/s
                heart_rate_mean=110, heart_rate_std=12, heart_rate_range=(90, 130)
            ),
            RowerPhaseConfig(
                name="main_workout",
                duration_range=(600, 1800),  # 10-30 minutes
                power_mean=220, power_std=35, power_range=(120, 350),
                stroke_rate_mean=26, stroke_rate_std=4, stroke_rate_range=(20, 34),
                speed_mean=3.0, speed_std=0.4, speed_range=(2.2, 4.0),  # m/s
                heart_rate_mean=160, heart_rate_std=18, heart_rate_range=(130, 190)
            ),
            RowerPhaseConfig(
                name="cooldown",
                duration_range=(180, 360),  # 3-6 minutes
                power_mean=100, power_std=20, power_range=(40, 150),
                stroke_rate_mean=18, stroke_rate_std=2, stroke_rate_range=(14, 22),
                speed_mean=2.0, speed_std=0.2, speed_range=(1.4, 2.4),  # m/s
                heart_rate_mean=120, heart_rate_std=10, heart_rate_range=(100, 140)
            )
        ]
        
        self.workout_phases = base_phases.copy()
        
        # Apply profile-specific modifications
        if self.workout_profile == "intervals":
            self._configure_interval_workout()
        elif self.workout_profile == "endurance":
            self._configure_endurance_workout()
        
        logger.info(f"Configured {len(self.workout_phases)} phases for {self.workout_profile} rowing workout")
    
    def _configure_interval_workout(self) -> None:
        """Configure phases for interval rowing workout"""
        for phase in self.workout_phases:
            if phase.name == "main_workout":
                # Higher intensity and variability for intervals
                phase.power_mean *= 1.3
                phase.power_std *= 1.8
                phase.power_range = (phase.power_range[0], phase.power_range[1] * 1.4)
                
                # Higher stroke rate variability for intervals
                phase.stroke_rate_mean *= 1.1
                phase.stroke_rate_std *= 1.5
                phase.stroke_rate_range = (phase.stroke_rate_range[0], phase.stroke_rate_range[1] * 1.2)
                
                # Increased heart rate for intervals
                phase.heart_rate_mean *= 1.15
                phase.heart_rate_std *= 1.3
    
    def _configure_endurance_workout(self) -> None:
        """Configure phases for endurance rowing workout"""
        for phase in self.workout_phases:
            if phase.name == "main_workout":
                # Much longer duration for endurance
                phase.duration_range = (phase.duration_range[0] * 2.5, phase.duration_range[1] * 4)
                
                # Lower intensity but more consistent
                phase.power_mean *= 0.85
                phase.power_std *= 0.6
                phase.stroke_rate_std *= 0.7
                phase.speed_std *= 0.6
                phase.heart_rate_std *= 0.8
    
    def start_workout(self) -> None:
        """Start a new rowing workout session"""
        self.workout_duration = 0
        self.current_phase_index = 0
        self.phase_start_time = 0
        self.total_distance = 0.0
        self.total_calories = 0
        self.total_strokes = 0
        
        # Reset previous values to realistic starting points
        self.previous_values = {
            'power': 0,
            'stroke_rate': 0,
            'speed': 0,
            'heart_rate': 90
        }
        
        logger.info(f"Started {self.workout_profile} rowing workout with {len(self.workout_phases)} phases")
    
    def generate_data_point(self, elapsed_time: int) -> Dict[str, Any]:
        """
        Generate a realistic rowing data point for the current workout time.
        
        Args:
            elapsed_time: Elapsed time in seconds since workout start
            
        Returns:
            Dictionary containing realistic rowing workout data
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
        
        base_stroke_rate = self._generate_phase_value(
            current_phase.stroke_rate_mean,
            current_phase.stroke_rate_std,
            current_phase.stroke_rate_range
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
        
        # Apply rowing-specific correlations
        power, stroke_rate, speed, heart_rate = self._apply_rowing_correlations(
            base_power, base_stroke_rate, base_speed, base_heart_rate
        )
        
        # Add workout profile-specific variations
        power, stroke_rate, speed, heart_rate = self._apply_profile_variations(
            power, stroke_rate, speed, heart_rate, current_phase
        )
        
        # Apply smoothing to prevent unrealistic jumps
        power, stroke_rate, speed, heart_rate = self._apply_smoothing(
            power, stroke_rate, speed, heart_rate
        )
        
        # Add realistic rowing-specific effects
        power, stroke_rate, speed, heart_rate = self._apply_rowing_effects(
            power, stroke_rate, speed, heart_rate
        )
        
        # Update accumulated metrics
        self._update_accumulated_metrics(speed, power, stroke_rate)
        
        # Store current values for next iteration
        self.previous_values = {
            'power': power,
            'stroke_rate': stroke_rate,
            'speed': speed,
            'heart_rate': heart_rate
        }
        
        # Create data packet
        data = {
            "type": "rower",
            "instantaneous_power": int(power),
            "stroke_rate": int(stroke_rate),
            "heart_rate": int(heart_rate),
            "total_distance": round(self.total_distance, 1),
            "total_calories": self.total_calories,
            "total_strokes": self.total_strokes,
            "timestamp": elapsed_time,
            "elapsed_time": elapsed_time,
            "workout_phase": current_phase.name,
            "speed_ms": round(speed, 2),  # Speed in m/s for rowing
            "data_id": f"{elapsed_time}_{int(time.time() * 1000) % 1000}"
        }
        
        return data
    
    def _get_current_phase(self) -> Optional[RowerPhaseConfig]:
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
                logger.info(f"Transitioning to rowing phase: {next_phase.name}")
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
    
    def _apply_rowing_correlations(self, power: float, stroke_rate: float, speed: float, heart_rate: float) -> Tuple[float, float, float, float]:
        """Apply rowing-specific correlations between metrics"""
        # Get correlation coefficients
        power_stroke_rate_corr = self.correlations['power_stroke_rate']
        power_speed_corr = self.correlations['power_speed']
        stroke_rate_speed_corr = self.correlations['stroke_rate_speed']
        heart_rate_power_corr = self.correlations['heart_rate_power']
        
        # Apply power-stroke rate correlation (weaker than cycling)
        if power > 0:
            stroke_rate_adjustment = (power - 200) * 0.05 * power_stroke_rate_corr
            stroke_rate = max(0, stroke_rate + stroke_rate_adjustment)
        
        # Apply power-speed correlation (very strong for rowing)
        if power > 0:
            # Rowing speed is highly correlated with power (cube root relationship)
            speed_from_power = (power / 2.8) ** (1/3)  # Simplified rowing power curve
            speed = speed * (1 - power_speed_corr) + speed_from_power * power_speed_corr
        
        # Apply stroke rate-speed correlation
        if stroke_rate > 0:
            speed_adjustment = (stroke_rate - 24) * 0.08 * stroke_rate_speed_corr
            speed = max(0, speed + speed_adjustment)
        
        # Apply heart rate-power correlation (stronger for rowing due to full-body)
        if power > 0:
            hr_adjustment = (power - 200) * 0.25 * heart_rate_power_corr
            heart_rate = max(60, min(220, heart_rate + hr_adjustment))
        
        return power, stroke_rate, speed, heart_rate
    
    def _apply_profile_variations(self, power: float, stroke_rate: float, speed: float, heart_rate: float, phase: RowerPhaseConfig) -> Tuple[float, float, float, float]:
        """Apply workout profile-specific variations"""
        if self.workout_profile == "intervals" and phase.name == "main_workout":
            # Create interval pattern for rowing
            interval_period = 120  # 2-minute intervals (longer than cycling)
            phase_time = self.workout_duration - self.phase_start_time
            cycle_time = phase_time % (interval_period * 2)
            
            if cycle_time < interval_period:
                # High intensity interval
                power *= 1.5
                stroke_rate *= 1.3
                speed *= 1.2
                heart_rate *= 1.12
            else:
                # Recovery interval
                power *= 0.65
                stroke_rate *= 0.75
                speed *= 0.8
                heart_rate *= 0.92
        
        elif self.workout_profile == "endurance":
            # Add slight variations for endurance rowing
            variation_factor = 0.03 * random.uniform(-1, 1)  # Smaller variations
            power *= (1 + variation_factor)
            stroke_rate *= (1 + variation_factor * 0.3)
            speed *= (1 + variation_factor * 0.5)
            heart_rate *= (1 + variation_factor * 0.2)
        
        return power, stroke_rate, speed, heart_rate
    
    def _apply_smoothing(self, power: float, stroke_rate: float, speed: float, heart_rate: float) -> Tuple[float, float, float, float]:
        """Apply smoothing to prevent unrealistic jumps between data points"""
        smoothing_factor = 0.8  # Slightly more smoothing for rowing
        
        # Smooth each metric
        power = power * (1 - smoothing_factor) + self.previous_values['power'] * smoothing_factor
        stroke_rate = stroke_rate * (1 - smoothing_factor) + self.previous_values['stroke_rate'] * smoothing_factor
        speed = speed * (1 - smoothing_factor) + self.previous_values['speed'] * smoothing_factor
        heart_rate = heart_rate * (1 - smoothing_factor) + self.previous_values['heart_rate'] * smoothing_factor
        
        return power, stroke_rate, speed, heart_rate
    
    def _apply_rowing_effects(self, power: float, stroke_rate: float, speed: float, heart_rate: float) -> Tuple[float, float, float, float]:
        """Apply rowing-specific effects and data quality patterns"""
        # Rowing has more consistent data than cycling (less zero values)
        zero_power_chance = 1.0  # Lower than cycling
        zero_stroke_rate_chance = 1.0
        
        # Occasionally set values to zero
        if random.random() * 100 < zero_power_chance:
            power = 0
            stroke_rate = 0  # If no power, no stroke rate
        
        if random.random() * 100 < zero_stroke_rate_chance:
            stroke_rate = 0
        
        # Add rowing-specific noise patterns
        power += random.gauss(0, 3)  # Slightly more power variation
        stroke_rate += random.gauss(0, 0.5)  # Less stroke rate variation
        speed += random.gauss(0, 0.1)  # Small speed variation
        heart_rate += random.gauss(0, 2)
        
        # Ensure non-negative values and realistic ranges
        power = max(0, power)
        stroke_rate = max(0, min(50, stroke_rate))  # Max ~50 SPM
        speed = max(0, min(6.0, speed))  # Max ~6 m/s for rowing
        heart_rate = max(60, min(220, heart_rate))
        
        return power, stroke_rate, speed, heart_rate
    
    def _update_accumulated_metrics(self, speed: float, power: float, stroke_rate: float) -> None:
        """Update accumulated distance, calories, and strokes"""
        # Update distance (speed in m/s -> m per second)
        if speed > 0:
            distance_increment = speed * 1.0  # 1 second
            self.total_distance += distance_increment
        
        # Update calories (rowing burns more calories: ~6 calories per minute per 100W)
        if power > 0:
            calories_per_second = (power * 0.06 * 60) / 3600
            self.total_calories += int(calories_per_second)
        
        # Update total strokes
        if stroke_rate > 0:
            strokes_per_second = stroke_rate / 60.0
            self.total_strokes += int(strokes_per_second)
    
    def _generate_end_workout_data(self) -> Dict[str, Any]:
        """Generate final data point when workout is complete"""
        return {
            "type": "rower",
            "instantaneous_power": 0,
            "stroke_rate": 0,
            "heart_rate": max(90, self.previous_values['heart_rate'] - 15),
            "total_distance": round(self.total_distance, 1),
            "total_calories": self.total_calories,
            "total_strokes": self.total_strokes,
            "timestamp": self.workout_duration,
            "elapsed_time": self.workout_duration,
            "workout_phase": "complete",
            "speed_ms": 0.0,
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
                    "stroke_rate_range": phase.stroke_rate_range,
                    "speed_range": phase.speed_range,
                    "heart_rate_range": phase.heart_rate_range
                }
                for phase in self.workout_phases
            ],
            "correlations": self.correlations
        }


def main():
    """Test the enhanced rower simulator"""
    print("Testing Enhanced Rower Simulator")
    print("=" * 50)
    
    # Test different workout profiles
    profiles = ["standard", "intervals", "endurance"]
    
    for profile in profiles:
        print(f"\nTesting {profile} profile:")
        simulator = EnhancedRowerSimulator(workout_profile=profile)
        simulator.start_workout()
        
        # Generate some sample data points
        for elapsed_time in [0, 60, 180, 300, 600, 900]:
            data = simulator.generate_data_point(elapsed_time)
            print(f"  {elapsed_time:3d}s: Power={data['instantaneous_power']:3d}W, "
                  f"StrokeRate={data['stroke_rate']:2d}SPM, "
                  f"Speed={data['speed_ms']:4.1f}m/s, "
                  f"HR={data['heart_rate']:3d}BPM, "
                  f"Distance={data['total_distance']:6.1f}m, "
                  f"Phase={data['workout_phase']}")


if __name__ == "__main__":
    main()