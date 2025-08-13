#!/usr/bin/env python3
"""
Workout Data Analyzer - Extract patterns from workout.log for realistic simulation
"""

import re
import json
import statistics
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class WorkoutDataPoint:
    """Represents a single workout data point"""
    timestamp: datetime
    elapsed_time: int
    device_type: str
    speed: float
    cadence: float
    power: int
    heart_rate: int
    distance: int
    
    
@dataclass
class WorkoutPhase:
    """Represents a workout phase with statistical characteristics"""
    name: str
    start_time: int
    end_time: int
    duration: int
    avg_power: float
    avg_cadence: float
    avg_speed: float
    avg_heart_rate: float
    power_range: Tuple[float, float]
    cadence_range: Tuple[float, float]
    speed_range: Tuple[float, float]
    heart_rate_range: Tuple[float, float]


class WorkoutDataAnalyzer:
    """Analyzes workout log data to extract realistic patterns"""
    
    def __init__(self, log_file_path: str = "logs/workout.log"):
        self.log_file_path = log_file_path
        self.data_points: List[WorkoutDataPoint] = []
        self.workout_phases: List[WorkoutPhase] = []
        
    def parse_workout_log(self) -> List[WorkoutDataPoint]:
        """Parse workout.log file and extract data points"""
        data_pattern = r"Data: (\{.*?\})"
        
        try:
            with open(self.log_file_path, 'r') as file:
                content = file.read()
                
            matches = re.findall(data_pattern, content)
            
            for match in matches:
                try:
                    # Clean up the data string and parse as JSON
                    data_str = match.replace("'", '"')
                    data = json.loads(data_str)
                    
                    # Only process bike data for now
                    if data.get('device_type') == 'bike':
                        timestamp = datetime.fromisoformat(data['timestamp'])
                        
                        data_point = WorkoutDataPoint(
                            timestamp=timestamp,
                            elapsed_time=data.get('elapsed_time', 0),
                            device_type=data['device_type'],
                            speed=float(data.get('speed', 0)),
                            cadence=float(data.get('cadence', 0)),
                            power=int(data.get('power', 0)),
                            heart_rate=int(data.get('heart_rate', 0)),
                            distance=int(data.get('distance', 0))
                        )
                        
                        self.data_points.append(data_point)
                        
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"Error parsing data point: {e}")
                    continue
                    
        except FileNotFoundError:
            print(f"Workout log file not found: {self.log_file_path}")
            return []
            
        print(f"Parsed {len(self.data_points)} data points from workout log")
        return self.data_points
    
    def identify_workout_phases(self) -> List[WorkoutPhase]:
        """Identify workout phases based on power and cadence patterns"""
        if not self.data_points:
            return []
            
        # Sort by elapsed time
        sorted_points = sorted(self.data_points, key=lambda x: x.elapsed_time)
        
        # Calculate moving averages for phase detection
        window_size = 10
        phases = []
        
        # Warm-up phase (first 5 minutes or until power > 20W consistently)
        warmup_end = 300  # 5 minutes default
        for i, point in enumerate(sorted_points):
            if point.elapsed_time > 60 and point.power > 20:  # After 1 minute, power > 20W
                # Look ahead to confirm sustained power
                sustained = True
                for j in range(i, min(i + 5, len(sorted_points))):
                    if sorted_points[j].power < 15:
                        sustained = False
                        break
                if sustained:
                    warmup_end = point.elapsed_time
                    break
        
        # Extract warmup data
        warmup_points = [p for p in sorted_points if p.elapsed_time <= warmup_end]
        if warmup_points:
            phases.append(self._create_phase("warmup", warmup_points))
        
        # Main workout phase (after warmup until power drops significantly)
        main_start = warmup_end
        main_end = sorted_points[-1].elapsed_time
        
        # Look for cooldown (sustained power drop)
        for i in range(len(sorted_points) - 10, 0, -1):
            point = sorted_points[i]
            if point.elapsed_time > main_start + 300:  # At least 5 minutes of main workout
                # Check if power dropped significantly
                recent_avg = statistics.mean([p.power for p in sorted_points[i:i+5]])
                earlier_avg = statistics.mean([p.power for p in sorted_points[max(0, i-20):i-10]])
                
                if recent_avg < earlier_avg * 0.6:  # 40% power drop
                    main_end = point.elapsed_time
                    break
        
        # Extract main workout data
        main_points = [p for p in sorted_points if main_start < p.elapsed_time <= main_end]
        if main_points:
            phases.append(self._create_phase("main_workout", main_points))
        
        # Cooldown phase (remaining data)
        cooldown_points = [p for p in sorted_points if p.elapsed_time > main_end]
        if cooldown_points:
            phases.append(self._create_phase("cooldown", cooldown_points))
        
        self.workout_phases = phases
        return phases
    
    def _create_phase(self, name: str, points: List[WorkoutDataPoint]) -> WorkoutPhase:
        """Create a workout phase from data points"""
        if not points:
            return None
            
        powers = [p.power for p in points]
        cadences = [p.cadence for p in points]
        speeds = [p.speed for p in points]
        heart_rates = [p.heart_rate for p in points if p.heart_rate > 0]
        
        return WorkoutPhase(
            name=name,
            start_time=min(p.elapsed_time for p in points),
            end_time=max(p.elapsed_time for p in points),
            duration=max(p.elapsed_time for p in points) - min(p.elapsed_time for p in points),
            avg_power=statistics.mean(powers) if powers else 0,
            avg_cadence=statistics.mean(cadences) if cadences else 0,
            avg_speed=statistics.mean(speeds) if speeds else 0,
            avg_heart_rate=statistics.mean(heart_rates) if heart_rates else 0,
            power_range=(min(powers) if powers else 0, max(powers) if powers else 0),
            cadence_range=(min(cadences) if cadences else 0, max(cadences) if cadences else 0),
            speed_range=(min(speeds) if speeds else 0, max(speeds) if speeds else 0),
            heart_rate_range=(min(heart_rates) if heart_rates else 0, max(heart_rates) if heart_rates else 0)
        )
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient between two variables"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
            
        n = len(x)
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(n))
        
        denominator = (sum_sq_x * sum_sq_y) ** 0.5
        
        if denominator == 0:
            return 0.0
            
        return numerator / denominator
    
    def calculate_correlations(self) -> Dict[str, float]:
        """Calculate correlations between different metrics"""
        if not self.data_points:
            return {}
            
        # Extract non-zero values for correlation analysis
        valid_points = [p for p in self.data_points if p.power > 0 and p.cadence > 0 and p.speed > 0]
        
        if len(valid_points) < 10:
            return {}
            
        powers = [p.power for p in valid_points]
        cadences = [p.cadence for p in valid_points]
        speeds = [p.speed for p in valid_points]
        heart_rates = [p.heart_rate for p in valid_points if p.heart_rate > 0]
        
        correlations = {}
        
        try:
            # Power-Cadence correlation
            if len(powers) == len(cadences):
                correlations['power_cadence'] = self._calculate_correlation(powers, cadences)
            
            # Power-Speed correlation
            if len(powers) == len(speeds):
                correlations['power_speed'] = self._calculate_correlation(powers, speeds)
            
            # Cadence-Speed correlation
            if len(cadences) == len(speeds):
                correlations['cadence_speed'] = self._calculate_correlation(cadences, speeds)
            
            # Heart rate correlations (if available)
            if heart_rates and len(heart_rates) > 10:
                hr_powers = [p.power for p in valid_points if p.heart_rate > 0]
                if len(hr_powers) == len(heart_rates):
                    correlations['heart_rate_power'] = self._calculate_correlation(heart_rates, hr_powers)
                    
        except Exception as e:
            print(f"Error calculating correlations: {e}")
            
        return correlations
    
    def generate_statistical_model(self) -> Dict:
        """Generate statistical model for realistic data generation"""
        if not self.data_points or not self.workout_phases:
            return {}
            
        model = {
            'phases': {},
            'correlations': self.calculate_correlations(),
            'overall_stats': self._calculate_overall_stats(),
            'data_quality': self._analyze_data_quality()
        }
        
        # Generate phase-specific models
        for phase in self.workout_phases:
            phase_points = [p for p in self.data_points 
                          if phase.start_time <= p.elapsed_time <= phase.end_time]
            
            if phase_points:
                model['phases'][phase.name] = {
                    'duration_range': (phase.duration * 0.8, phase.duration * 1.2),
                    'power': {
                        'mean': phase.avg_power,
                        'std': statistics.stdev([p.power for p in phase_points]) if len(phase_points) > 1 else 5,
                        'range': phase.power_range
                    },
                    'cadence': {
                        'mean': phase.avg_cadence,
                        'std': statistics.stdev([p.cadence for p in phase_points]) if len(phase_points) > 1 else 2,
                        'range': phase.cadence_range
                    },
                    'speed': {
                        'mean': phase.avg_speed,
                        'std': statistics.stdev([p.speed for p in phase_points]) if len(phase_points) > 1 else 1,
                        'range': phase.speed_range
                    },
                    'heart_rate': {
                        'mean': phase.avg_heart_rate,
                        'std': statistics.stdev([p.heart_rate for p in phase_points if p.heart_rate > 0]) if len([p for p in phase_points if p.heart_rate > 0]) > 1 else 3,
                        'range': phase.heart_rate_range
                    }
                }
        
        return model
    
    def _calculate_overall_stats(self) -> Dict:
        """Calculate overall workout statistics"""
        if not self.data_points:
            return {}
            
        valid_points = [p for p in self.data_points if p.power > 0]
        
        return {
            'total_duration': max(p.elapsed_time for p in self.data_points),
            'max_power': max(p.power for p in valid_points) if valid_points else 0,
            'avg_power': statistics.mean([p.power for p in valid_points]) if valid_points else 0,
            'max_cadence': max(p.cadence for p in self.data_points),
            'avg_cadence': statistics.mean([p.cadence for p in self.data_points if p.cadence > 0]),
            'max_speed': max(p.speed for p in self.data_points),
            'avg_speed': statistics.mean([p.speed for p in self.data_points if p.speed > 0]),
            'heart_rate_range': (
                min(p.heart_rate for p in self.data_points if p.heart_rate > 0),
                max(p.heart_rate for p in self.data_points if p.heart_rate > 0)
            ) if any(p.heart_rate > 0 for p in self.data_points) else (0, 0)
        }
    
    def _analyze_data_quality(self) -> Dict:
        """Analyze data quality patterns for realistic simulation"""
        if not self.data_points:
            return {}
            
        total_points = len(self.data_points)
        zero_power_points = len([p for p in self.data_points if p.power == 0])
        zero_cadence_points = len([p for p in self.data_points if p.cadence == 0])
        zero_speed_points = len([p for p in self.data_points if p.speed == 0])
        
        return {
            'zero_power_percentage': (zero_power_points / total_points) * 100,
            'zero_cadence_percentage': (zero_cadence_points / total_points) * 100,
            'zero_speed_percentage': (zero_speed_points / total_points) * 100,
            'data_consistency': self._check_data_consistency()
        }
    
    def _check_data_consistency(self) -> Dict:
        """Check for data consistency patterns"""
        if len(self.data_points) < 2:
            return {}
            
        # Check for timestamp consistency (should be ~1Hz)
        time_gaps = []
        for i in range(1, len(self.data_points)):
            gap = self.data_points[i].elapsed_time - self.data_points[i-1].elapsed_time
            time_gaps.append(gap)
        
        return {
            'avg_time_gap': statistics.mean(time_gaps) if time_gaps else 0,
            'time_gap_std': statistics.stdev(time_gaps) if len(time_gaps) > 1 else 0,
            'expected_frequency': 1.0  # 1Hz expected
        }
    
    def print_analysis_report(self):
        """Print a comprehensive analysis report"""
        print("\n" + "="*60)
        print("WORKOUT DATA ANALYSIS REPORT")
        print("="*60)
        
        if not self.data_points:
            print("No data points found!")
            return
            
        print(f"\nTotal data points analyzed: {len(self.data_points)}")
        print(f"Workout duration: {max(p.elapsed_time for p in self.data_points)} seconds")
        
        # Phase analysis
        print(f"\nWorkout Phases Identified: {len(self.workout_phases)}")
        for phase in self.workout_phases:
            print(f"\n{phase.name.upper()}:")
            print(f"  Duration: {phase.duration}s ({phase.duration/60:.1f} minutes)")
            print(f"  Power: {phase.avg_power:.1f}W (range: {phase.power_range[0]:.1f}-{phase.power_range[1]:.1f}W)")
            print(f"  Cadence: {phase.avg_cadence:.1f} RPM (range: {phase.cadence_range[0]:.1f}-{phase.cadence_range[1]:.1f} RPM)")
            print(f"  Speed: {phase.avg_speed:.1f} km/h (range: {phase.speed_range[0]:.1f}-{phase.speed_range[1]:.1f} km/h)")
            print(f"  Heart Rate: {phase.avg_heart_rate:.1f} BPM (range: {phase.heart_rate_range[0]:.1f}-{phase.heart_rate_range[1]:.1f} BPM)")
        
        # Correlations
        correlations = self.calculate_correlations()
        if correlations:
            print(f"\nMetric Correlations:")
            for key, value in correlations.items():
                print(f"  {key.replace('_', '-').title()}: {value:.3f}")
        
        # Overall stats
        stats = self._calculate_overall_stats()
        if stats:
            print(f"\nOverall Statistics:")
            print(f"  Max Power: {stats['max_power']}W")
            print(f"  Average Power: {stats['avg_power']:.1f}W")
            print(f"  Max Cadence: {stats['max_cadence']:.1f} RPM")
            print(f"  Average Cadence: {stats['avg_cadence']:.1f} RPM")
            print(f"  Max Speed: {stats['max_speed']:.1f} km/h")
            print(f"  Average Speed: {stats['avg_speed']:.1f} km/h")
            print(f"  Heart Rate Range: {stats['heart_rate_range'][0]:.0f}-{stats['heart_rate_range'][1]:.0f} BPM")
        
        # Data quality
        quality = self._analyze_data_quality()
        if quality:
            print(f"\nData Quality Analysis:")
            print(f"  Zero Power Points: {quality['zero_power_percentage']:.1f}%")
            print(f"  Zero Cadence Points: {quality['zero_cadence_percentage']:.1f}%")
            print(f"  Zero Speed Points: {quality['zero_speed_percentage']:.1f}%")
            
            consistency = quality.get('data_consistency', {})
            if consistency:
                print(f"  Average Time Gap: {consistency['avg_time_gap']:.1f}s")
                print(f"  Time Gap Std Dev: {consistency['time_gap_std']:.1f}s")


def main():
    """Main function to run the analysis"""
    analyzer = WorkoutDataAnalyzer()
    
    # Parse the workout log
    data_points = analyzer.parse_workout_log()
    
    if not data_points:
        print("No data points found in workout log!")
        return
    
    # Identify workout phases
    phases = analyzer.identify_workout_phases()
    
    # Generate statistical model
    model = analyzer.generate_statistical_model()
    
    # Print analysis report
    analyzer.print_analysis_report()
    
    # Save the statistical model for use in simulation
    try:
        with open('src/utils/workout_patterns.json', 'w') as f:
            json.dump(model, f, indent=2, default=str)
        print(f"\nStatistical model saved to: src/utils/workout_patterns.json")
    except Exception as e:
        print(f"Error saving model: {e}")


if __name__ == "__main__":
    main()