"""
Database testing utilities and helpers.
"""

import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json


class TestDatabaseManager:
    """Manages test databases with cleanup and isolation."""
    
    def __init__(self):
        self.temp_dir = None
        self.db_path = None
        self.connection = None
    
    def setup_test_database(self) -> str:
        """Create a temporary test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rogue_garmin.db")
        
        # Create database with schema
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()
        
        return self.db_path
    
    def teardown_test_database(self):
        """Clean up test database."""
        if self.connection:
            self.connection.close()
            self.connection = None
        
        if self.db_path and os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        if self.temp_dir and os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def _create_schema(self):
        """Create database schema for testing."""
        cursor = self.connection.cursor()
        
        # Workouts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_type TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration INTEGER DEFAULT 0,
                total_distance REAL DEFAULT 0.0,
                total_calories INTEGER DEFAULT 0,
                avg_power INTEGER DEFAULT 0,
                max_power INTEGER DEFAULT 0,
                avg_heart_rate INTEGER DEFAULT 0,
                max_heart_rate INTEGER DEFAULT 0,
                avg_cadence INTEGER DEFAULT 0,
                max_cadence INTEGER DEFAULT 0,
                avg_speed REAL DEFAULT 0.0,
                max_speed REAL DEFAULT 0.0,
                avg_stroke_rate INTEGER DEFAULT 0,
                max_stroke_rate INTEGER DEFAULT 0,
                total_strokes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Data points table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                power INTEGER,
                heart_rate INTEGER,
                calories INTEGER,
                distance REAL,
                cadence INTEGER,
                speed REAL,
                stroke_rate INTEGER,
                stroke_count INTEGER,
                FOREIGN KEY (workout_id) REFERENCES workouts (id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_start_time ON workouts(start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_device_type ON workouts(device_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_points_workout_id ON data_points(workout_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_points_timestamp ON data_points(timestamp)")
        
        self.connection.commit()
    
    def insert_test_workout(self, workout_data: Dict[str, Any]) -> int:
        """Insert a test workout and return its ID."""
        cursor = self.connection.cursor()
        
        columns = []
        values = []
        placeholders = []
        
        for key, value in workout_data.items():
            columns.append(key)
            values.append(value)
            placeholders.append("?")
        
        query = f"""
            INSERT INTO workouts ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """
        
        cursor.execute(query, values)
        self.connection.commit()
        
        return cursor.lastrowid
    
    def insert_test_data_points(self, workout_id: int, data_points: List[Dict[str, Any]]):
        """Insert test data points for a workout."""
        cursor = self.connection.cursor()
        
        for point in data_points:
            point_data = {"workout_id": workout_id, **point}
            
            columns = []
            values = []
            placeholders = []
            
            for key, value in point_data.items():
                columns.append(key)
                values.append(value)
                placeholders.append("?")
            
            query = f"""
                INSERT INTO data_points ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """
            
            cursor.execute(query, values)
        
        self.connection.commit()
    
    def get_workout_count(self) -> int:
        """Get total number of workouts."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM workouts")
        return cursor.fetchone()[0]
    
    def get_data_point_count(self, workout_id: Optional[int] = None) -> int:
        """Get total number of data points, optionally for a specific workout."""
        cursor = self.connection.cursor()
        if workout_id:
            cursor.execute("SELECT COUNT(*) FROM data_points WHERE workout_id = ?", (workout_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM data_points")
        return cursor.fetchone()[0]
    
    def clear_all_data(self):
        """Clear all data from test database."""
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM data_points")
        cursor.execute("DELETE FROM workouts")
        self.connection.commit()


def create_sample_workout_data(device_type: str = "bike", duration: int = 600) -> Dict[str, Any]:
    """Create sample workout data for testing."""
    start_time = datetime.now() - timedelta(seconds=duration)
    end_time = start_time + timedelta(seconds=duration)
    
    workout_data = {
        "device_type": device_type,
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "total_distance": duration * 0.1,  # 0.1 km per second
        "total_calories": duration * 0.5,  # 0.5 calories per second
        "avg_power": 150,
        "max_power": 200,
        "avg_heart_rate": 140,
        "max_heart_rate": 170
    }
    
    if device_type == "bike":
        workout_data.update({
            "avg_cadence": 80,
            "max_cadence": 95,
            "avg_speed": 25.0,
            "max_speed": 30.0
        })
    elif device_type == "rower":
        workout_data.update({
            "avg_stroke_rate": 24,
            "max_stroke_rate": 28,
            "total_strokes": duration // 2
        })
    
    return workout_data


def create_sample_data_points(device_type: str = "bike", count: int = 600) -> List[Dict[str, Any]]:
    """Create sample data points for testing."""
    data_points = []
    start_time = datetime.now() - timedelta(seconds=count)
    
    for i in range(count):
        timestamp = start_time + timedelta(seconds=i)
        
        # Create realistic progression
        progress = i / count
        intensity = 0.5 + 0.3 * (1 - abs(progress - 0.5) * 2)
        
        base_point = {
            "timestamp": timestamp,
            "power": int(150 + intensity * 50),
            "heart_rate": int(140 + intensity * 30),
            "calories": i * 0.5,
            "distance": i * 0.1
        }
        
        if device_type == "bike":
            base_point.update({
                "cadence": int(80 + intensity * 15),
                "speed": 25.0 + intensity * 5
            })
        elif device_type == "rower":
            base_point.update({
                "stroke_rate": int(24 + intensity * 4),
                "stroke_count": i // 2
            })
        
        data_points.append(base_point)
    
    return data_points


def validate_database_integrity(db_path: str) -> Dict[str, Any]:
    """Validate database integrity and return report."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    
    report = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "statistics": {}
    }
    
    try:
        # Check table existence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ["workouts", "data_points"]
        for table in required_tables:
            if table not in tables:
                report["valid"] = False
                report["errors"].append(f"Missing required table: {table}")
        
        if not report["valid"]:
            return report
        
        # Check data consistency
        cursor.execute("SELECT COUNT(*) FROM workouts")
        workout_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM data_points")
        data_point_count = cursor.fetchone()[0]
        
        report["statistics"]["workout_count"] = workout_count
        report["statistics"]["data_point_count"] = data_point_count
        
        # Check for orphaned data points
        cursor.execute("""
            SELECT COUNT(*) FROM data_points dp
            LEFT JOIN workouts w ON dp.workout_id = w.id
            WHERE w.id IS NULL
        """)
        orphaned_points = cursor.fetchone()[0]
        
        if orphaned_points > 0:
            report["warnings"].append(f"Found {orphaned_points} orphaned data points")
        
        # Check for workouts without data points
        cursor.execute("""
            SELECT COUNT(*) FROM workouts w
            LEFT JOIN data_points dp ON w.id = dp.workout_id
            WHERE dp.workout_id IS NULL
        """)
        empty_workouts = cursor.fetchone()[0]
        
        if empty_workouts > 0:
            report["warnings"].append(f"Found {empty_workouts} workouts without data points")
        
        # Check timestamp consistency
        cursor.execute("""
            SELECT w.id, w.start_time, w.end_time, 
                   MIN(dp.timestamp) as first_point,
                   MAX(dp.timestamp) as last_point
            FROM workouts w
            JOIN data_points dp ON w.id = dp.workout_id
            GROUP BY w.id, w.start_time, w.end_time
        """)
        
        for row in cursor.fetchall():
            workout_id = row[0]
            start_time = datetime.fromisoformat(row[1]) if row[1] else None
            end_time = datetime.fromisoformat(row[2]) if row[2] else None
            first_point = datetime.fromisoformat(row[3]) if row[3] else None
            last_point = datetime.fromisoformat(row[4]) if row[4] else None
            
            if start_time and first_point and start_time > first_point:
                report["warnings"].append(
                    f"Workout {workout_id}: start_time after first data point"
                )
            
            if end_time and last_point and end_time < last_point:
                report["warnings"].append(
                    f"Workout {workout_id}: end_time before last data point"
                )
    
    except Exception as e:
        report["valid"] = False
        report["errors"].append(f"Database validation error: {str(e)}")
    
    finally:
        connection.close()
    
    return report


class DatabaseTestCase:
    """Base class for database test cases."""
    
    def __init__(self):
        self.db_manager = TestDatabaseManager()
        self.db_path = None
    
    def setup(self):
        """Set up test database."""
        self.db_path = self.db_manager.setup_test_database()
    
    def teardown(self):
        """Clean up test database."""
        self.db_manager.teardown_test_database()
    
    def create_test_workout(self, device_type: str = "bike", duration: int = 600) -> int:
        """Create a complete test workout with data points."""
        workout_data = create_sample_workout_data(device_type, duration)
        workout_id = self.db_manager.insert_test_workout(workout_data)
        
        data_points = create_sample_data_points(device_type, duration)
        self.db_manager.insert_test_data_points(workout_id, data_points)
        
        return workout_id
    
    def assert_workout_exists(self, workout_id: int):
        """Assert that a workout exists in the database."""
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id FROM workouts WHERE id = ?", (workout_id,))
        result = cursor.fetchone()
        assert result is not None, f"Workout {workout_id} does not exist"
    
    def assert_data_points_exist(self, workout_id: int, expected_count: int = None):
        """Assert that data points exist for a workout."""
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM data_points WHERE workout_id = ?", (workout_id,))
        count = cursor.fetchone()[0]
        
        assert count > 0, f"No data points found for workout {workout_id}"
        
        if expected_count is not None:
            assert count == expected_count, f"Expected {expected_count} data points, found {count}"
    
    def get_workout_summary(self, workout_id: int) -> Dict[str, Any]:
        """Get workout summary for validation."""
        cursor = self.db_manager.connection.cursor()
        
        # Get workout data
        cursor.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))
        workout_row = cursor.fetchone()
        
        if not workout_row:
            return None
        
        workout = dict(workout_row)
        
        # Get data point statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as point_count,
                AVG(power) as avg_power_calculated,
                MAX(power) as max_power_calculated,
                AVG(heart_rate) as avg_hr_calculated,
                MAX(heart_rate) as max_hr_calculated,
                MAX(distance) as final_distance,
                MAX(calories) as final_calories
            FROM data_points 
            WHERE workout_id = ?
        """, (workout_id,))
        
        stats_row = cursor.fetchone()
        if stats_row:
            workout.update(dict(stats_row))
        
        return workout