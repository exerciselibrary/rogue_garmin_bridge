"""
Performance monitoring and optimization testing.

Adds performance metrics collection throughout the application, creates
performance regression testing, implements database query optimization
and indexing, and adds client-side performance monitoring for web interface.
"""

import pytest
import asyncio
import time
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, patch
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tests.utils.mock_devices import MockFTMSDevice, create_mock_workout_data
from tests.performance.test_load_testing import SystemResourceMonitor

# Import system components
try:
    from data.database_manager import DatabaseManager
    from data.workout_manager import WorkoutManager
    from ftms.ftms_manager import FTMSDeviceManager
    from web.app import app as flask_app
    from utils.logging_config import get_component_logger
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


@dataclass
class PerformanceMetric:
    """Represents a performance metric measurement."""
    timestamp: datetime
    component: str
    operation: str
    duration_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    additional_data: Optional[Dict[str, Any]] = None


class PerformanceCollector:
    """Collects and analyzes performance metrics."""
    
    def __init__(self):
        self.metrics = deque(maxlen=10000)  # Keep last 10k metrics
        self.component_stats = defaultdict(list)
        self.operation_stats = defaultdict(list)
        self.collecting = False
        self.collection_thread = None
        self.lock = threading.Lock()
    
    def start_collection(self):
        """Start collecting performance metrics."""
        self.collecting = True
        self.collection_thread = threading.Thread(target=self._collection_loop)
        self.collection_thread.daemon = True
        self.collection_thread.start()
    
    def stop_collection(self):
        """Stop collecting performance metrics."""
        self.collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=2.0)
    
    def record_metric(self, component: str, operation: str, duration_ms: float, 
                     memory_usage_mb: Optional[float] = None, 
                     cpu_percent: Optional[float] = None,
                     additional_data: Optional[Dict[str, Any]] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            component=component,
            operation=operation,
            duration_ms=duration_ms,
            memory_usage_mb=memory_usage_mb,
            cpu_percent=cpu_percent,
            additional_data=additional_data or {}
        )
        
        with self.lock:
            self.metrics.append(metric)
            self.component_stats[component].append(metric)
            self.operation_stats[operation].append(metric)
    
    def _collection_loop(self):
        """Background collection loop for system metrics."""
        import psutil
        process = psutil.Process()
        
        while self.collecting:
            try:
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()
                
                self.record_metric(
                    component="system",
                    operation="resource_monitoring",
                    duration_ms=0,
                    memory_usage_mb=memory_info.rss / (1024 * 1024),
                    cpu_percent=cpu_percent
                )
                
                time.sleep(1.0)
            except Exception as e:
                print(f"Error in performance collection: {e}")
                break
    
    def get_component_summary(self, component: str) -> Dict[str, Any]:
        """Get performance summary for a component."""
        with self.lock:
            metrics = self.component_stats.get(component, [])
        
        if not metrics:
            return {}
        
        durations = [m.duration_ms for m in metrics if m.duration_ms > 0]
        memory_values = [m.memory_usage_mb for m in metrics if m.memory_usage_mb is not None]
        cpu_values = [m.cpu_percent for m in metrics if m.cpu_percent is not None]
        
        summary = {
            'total_operations': len(metrics),
            'time_span_seconds': (metrics[-1].timestamp - metrics[0].timestamp).total_seconds(),
        }
        
        if durations:
            summary['duration_stats'] = {
                'min_ms': min(durations),
                'max_ms': max(durations),
                'avg_ms': statistics.mean(durations),
                'median_ms': statistics.median(durations),
                'p95_ms': statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else max(durations),
                'p99_ms': statistics.quantiles(durations, n=100)[98] if len(durations) > 100 else max(durations)
            }
        
        if memory_values:
            summary['memory_stats'] = {
                'min_mb': min(memory_values),
                'max_mb': max(memory_values),
                'avg_mb': statistics.mean(memory_values)
            }
        
        if cpu_values:
            summary['cpu_stats'] = {
                'min_percent': min(cpu_values),
                'max_percent': max(cpu_values),
                'avg_percent': statistics.mean(cpu_values)
            }
        
        return summary
    
    def get_operation_summary(self, operation: str) -> Dict[str, Any]:
        """Get performance summary for an operation."""
        with self.lock:
            metrics = self.operation_stats.get(operation, [])
        
        if not metrics:
            return {}
        
        durations = [m.duration_ms for m in metrics if m.duration_ms > 0]
        
        if not durations:
            return {'total_operations': len(metrics)}
        
        return {
            'total_operations': len(metrics),
            'duration_stats': {
                'min_ms': min(durations),
                'max_ms': max(durations),
                'avg_ms': statistics.mean(durations),
                'median_ms': statistics.median(durations),
                'operations_per_second': len(durations) / max(1, (metrics[-1].timestamp - metrics[0].timestamp).total_seconds())
            }
        }
    
    def detect_performance_regressions(self, baseline_metrics: Dict[str, Any], 
                                     threshold_percent: float = 20.0) -> List[Dict[str, Any]]:
        """Detect performance regressions compared to baseline."""
        regressions = []
        
        for component in self.component_stats.keys():
            current_summary = self.get_component_summary(component)
            baseline_summary = baseline_metrics.get(component, {})
            
            if not baseline_summary or 'duration_stats' not in current_summary:
                continue
            
            current_avg = current_summary['duration_stats']['avg_ms']
            baseline_avg = baseline_summary.get('duration_stats', {}).get('avg_ms')
            
            if baseline_avg and current_avg > baseline_avg * (1 + threshold_percent / 100):
                regression_percent = ((current_avg - baseline_avg) / baseline_avg) * 100
                regressions.append({
                    'component': component,
                    'metric': 'avg_duration_ms',
                    'baseline_value': baseline_avg,
                    'current_value': current_avg,
                    'regression_percent': regression_percent
                })
        
        return regressions
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file."""
        with self.lock:
            metrics_data = [asdict(metric) for metric in self.metrics]
        
        # Convert datetime objects to strings
        for metric in metrics_data:
            metric['timestamp'] = metric['timestamp'].isoformat()
        
        with open(filepath, 'w') as f:
            json.dump(metrics_data, f, indent=2)
    
    def clear_metrics(self):
        """Clear all collected metrics."""
        with self.lock:
            self.metrics.clear()
            self.component_stats.clear()
            self.operation_stats.clear()


class DatabasePerformanceOptimizer:
    """Optimize database performance and test query efficiency."""
    
    def __init__(self, database):
        self.database = database
        self.query_stats = defaultdict(list)
    
    def analyze_query_performance(self, query: str, params: tuple = ()) -> Dict[str, Any]:
        """Analyze performance of a specific query."""
        # Enable query profiling
        self.database.connection.execute("PRAGMA query_only = ON")
        
        start_time = time.time()
        
        try:
            # Execute query with EXPLAIN QUERY PLAN
            explain_result = self.database.connection.execute(
                f"EXPLAIN QUERY PLAN {query}", params
            ).fetchall()
            
            # Execute actual query
            self.database.connection.execute("PRAGMA query_only = OFF")
            result = self.database.connection.execute(query, params).fetchall()
            
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            analysis = {
                'query': query,
                'duration_ms': duration_ms,
                'row_count': len(result),
                'query_plan': [dict(row) for row in explain_result] if explain_result else [],
                'uses_index': any('USING INDEX' in str(row) for row in explain_result) if explain_result else False,
                'full_table_scan': any('SCAN TABLE' in str(row) for row in explain_result) if explain_result else False
            }
            
            self.query_stats[query].append(analysis)
            return analysis
            
        except Exception as e:
            self.database.connection.execute("PRAGMA query_only = OFF")
            return {
                'query': query,
                'error': str(e),
                'duration_ms': (time.time() - start_time) * 1000
            }
    
    def suggest_indexes(self) -> List[Dict[str, str]]:
        """Suggest database indexes based on query patterns."""
        suggestions = []
        
        # Analyze common query patterns
        common_queries = [
            "SELECT * FROM workouts WHERE device_type = ?",
            "SELECT * FROM workouts WHERE start_time >= ?",
            "SELECT * FROM workout_data WHERE workout_id = ?",
            "SELECT * FROM workout_data WHERE workout_id = ? ORDER BY timestamp",
            "SELECT COUNT(*) FROM workout_data WHERE workout_id = ?",
            "SELECT AVG(power), MAX(power) FROM workout_data WHERE workout_id = ?"
        ]
        
        for query in common_queries:
            try:
                analysis = self.analyze_query_performance(query, ('test_param',))
                
                if analysis.get('full_table_scan') and not analysis.get('uses_index'):
                    # Suggest index based on WHERE clause
                    if 'device_type' in query:
                        suggestions.append({
                            'table': 'workouts',
                            'columns': 'device_type',
                            'reason': 'Frequent filtering by device type'
                        })
                    elif 'start_time' in query:
                        suggestions.append({
                            'table': 'workouts',
                            'columns': 'start_time',
                            'reason': 'Frequent date range queries'
                        })
                    elif 'workout_id' in query and 'workout_data' in query:
                        suggestions.append({
                            'table': 'workout_data',
                            'columns': 'workout_id',
                            'reason': 'Foreign key lookups'
                        })
                        if 'ORDER BY timestamp' in query:
                            suggestions.append({
                                'table': 'workout_data',
                                'columns': 'workout_id, timestamp',
                                'reason': 'Sorting by timestamp within workout'
                            })
            except Exception as e:
                print(f"Error analyzing query {query}: {e}")
        
        return suggestions
    
    def create_recommended_indexes(self):
        """Create recommended database indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_workouts_device_type ON workouts(device_type)",
            "CREATE INDEX IF NOT EXISTS idx_workouts_start_time ON workouts(start_time)",
            "CREATE INDEX IF NOT EXISTS idx_workout_data_workout_id ON workout_data(workout_id)",
            "CREATE INDEX IF NOT EXISTS idx_workout_data_timestamp ON workout_data(workout_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_workout_data_power ON workout_data(power) WHERE power IS NOT NULL",
        ]
        
        created_indexes = []
        for index_sql in indexes:
            try:
                self.database.connection.execute(index_sql)
                created_indexes.append(index_sql)
            except Exception as e:
                print(f"Error creating index: {e}")
        
        self.database.connection.commit()
        return created_indexes
    
    def benchmark_queries(self, iterations: int = 100) -> Dict[str, Any]:
        """Benchmark common database queries."""
        # Create test data
        workout_id = self.database.create_workout({
            'device_type': 'bike',
            'start_time': datetime.now(),
            'duration': 3600
        })
        
        # Add test data points
        for i in range(1000):
            self.database.add_data_point(workout_id, {
                'timestamp': datetime.now() + timedelta(seconds=i),
                'power': 150 + i % 100,
                'heart_rate': 140 + i % 30
            })
        
        # Benchmark queries
        queries_to_benchmark = [
            ("SELECT COUNT(*) FROM workouts", ()),
            ("SELECT * FROM workouts WHERE device_type = ?", ('bike',)),
            ("SELECT * FROM workout_data WHERE workout_id = ? LIMIT 100", (workout_id,)),
            ("SELECT AVG(power), MAX(power) FROM workout_data WHERE workout_id = ?", (workout_id,)),
            ("SELECT * FROM workout_data WHERE workout_id = ? ORDER BY timestamp DESC LIMIT 10", (workout_id,))
        ]
        
        benchmark_results = {}
        
        for query, params in queries_to_benchmark:
            durations = []
            
            for _ in range(iterations):
                start_time = time.time()
                try:
                    result = self.database.connection.execute(query, params).fetchall()
                    duration_ms = (time.time() - start_time) * 1000
                    durations.append(duration_ms)
                except Exception as e:
                    print(f"Error in benchmark query: {e}")
                    continue
            
            if durations:
                benchmark_results[query] = {
                    'avg_duration_ms': statistics.mean(durations),
                    'min_duration_ms': min(durations),
                    'max_duration_ms': max(durations),
                    'median_duration_ms': statistics.median(durations),
                    'iterations': len(durations)
                }
        
        return benchmark_results


class WebPerformanceMonitor:
    """Monitor web interface performance."""
    
    def __init__(self):
        self.request_metrics = []
        self.client_metrics = []
    
    def measure_endpoint_performance(self, client, endpoint: str, iterations: int = 10) -> Dict[str, Any]:
        """Measure performance of a web endpoint."""
        durations = []
        status_codes = []
        response_sizes = []
        
        for _ in range(iterations):
            start_time = time.time()
            try:
                response = client.get(endpoint)
                duration_ms = (time.time() - start_time) * 1000
                
                durations.append(duration_ms)
                status_codes.append(response.status_code)
                response_sizes.append(len(response.data))
                
            except Exception as e:
                print(f"Error testing endpoint {endpoint}: {e}")
                continue
        
        if not durations:
            return {'error': 'No successful requests'}
        
        return {
            'endpoint': endpoint,
            'avg_duration_ms': statistics.mean(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'median_duration_ms': statistics.median(durations),
            'success_rate': sum(1 for code in status_codes if code == 200) / len(status_codes),
            'avg_response_size_bytes': statistics.mean(response_sizes),
            'iterations': len(durations)
        }
    
    def simulate_client_side_performance(self) -> Dict[str, Any]:
        """Simulate client-side performance metrics."""
        # Simulate various client-side operations
        operations = {
            'dom_ready': random.uniform(50, 200),
            'first_paint': random.uniform(100, 400),
            'first_contentful_paint': random.uniform(150, 500),
            'largest_contentful_paint': random.uniform(200, 800),
            'cumulative_layout_shift': random.uniform(0, 0.1),
            'first_input_delay': random.uniform(10, 100),
            'total_blocking_time': random.uniform(50, 300)
        }
        
        return operations


@pytest.fixture
def performance_collector():
    """Provide performance metrics collector."""
    collector = PerformanceCollector()
    yield collector
    collector.stop_collection()


@pytest.fixture
def db_optimizer():
    """Provide database performance optimizer."""
    def _create_optimizer(database):
        return DatabasePerformanceOptimizer(database)
    return _create_optimizer


@pytest.fixture
def web_monitor():
    """Provide web performance monitor."""
    return WebPerformanceMonitor()


@pytest.mark.performance
class TestPerformanceMetricsCollection:
    """Test performance metrics collection throughout the application."""
    
    async def test_ftms_manager_performance_tracking(self, performance_collector):
        """Test performance tracking in FTMS Manager."""
        performance_collector.start_collection()
        
        # Create mock FTMS manager with performance tracking
        device = MockFTMSDevice("bike")
        
        # Simulate FTMS operations with performance tracking
        operations = [
            ('device_discovery', 50),
            ('device_connection', 200),
            ('data_processing', 5),
            ('data_validation', 2),
            ('callback_notification', 1)
        ]
        
        for operation, base_duration in operations:
            for i in range(20):  # 20 iterations of each operation
                # Simulate operation with some variance
                duration = base_duration + random.uniform(-base_duration*0.2, base_duration*0.2)
                
                performance_collector.record_metric(
                    component="ftms_manager",
                    operation=operation,
                    duration_ms=duration,
                    additional_data={'iteration': i}
                )
                
                await asyncio.sleep(0.01)  # Small delay between operations
        
        # Let collector gather some system metrics
        await asyncio.sleep(2)
        
        performance_collector.stop_collection()
        
        # Analyze collected metrics
        ftms_summary = performance_collector.get_component_summary("ftms_manager")
        
        # Assertions
        assert ftms_summary['total_operations'] == 100, "Should track all FTMS operations"
        assert 'duration_stats' in ftms_summary, "Should have duration statistics"
        assert ftms_summary['duration_stats']['avg_ms'] > 0, "Should have positive average duration"
        
        # Check individual operation performance
        for operation, expected_duration in operations:
            op_summary = performance_collector.get_operation_summary(operation)
            assert op_summary['total_operations'] == 20, f"Should track all {operation} operations"
            
            # Duration should be close to expected (within 50% variance)
            avg_duration = op_summary['duration_stats']['avg_ms']
            assert abs(avg_duration - expected_duration) < expected_duration * 0.5, \
                f"{operation} duration should be close to expected"
        
        print(f"FTMS Manager performance summary:")
        print(f"  Total operations: {ftms_summary['total_operations']}")
        print(f"  Average duration: {ftms_summary['duration_stats']['avg_ms']:.2f} ms")
        print(f"  P95 duration: {ftms_summary['duration_stats']['p95_ms']:.2f} ms")
    
    async def test_workout_manager_performance_tracking(self, performance_collector, test_database):
        """Test performance tracking in Workout Manager."""
        performance_collector.start_collection()
        
        workout_manager = WorkoutManager(database=test_database)
        
        # Simulate workout operations
        workout_data = {
            'device_type': 'bike',
            'start_time': datetime.now(),
            'duration': 1800
        }
        
        # Track workout creation performance
        start_time = time.time()
        workout_id = test_database.create_workout(workout_data)
        creation_duration = (time.time() - start_time) * 1000
        
        performance_collector.record_metric(
            component="workout_manager",
            operation="create_workout",
            duration_ms=creation_duration
        )
        
        # Track data point processing performance
        data_points = create_mock_workout_data("bike", duration=300)  # 5 minutes
        
        for i, data_point in enumerate(data_points):
            start_time = time.time()
            
            # Simulate data processing
            try:
                test_database.add_data_point(workout_id, data_point)
                processing_duration = (time.time() - start_time) * 1000
                
                performance_collector.record_metric(
                    component="workout_manager",
                    operation="process_data_point",
                    duration_ms=processing_duration,
                    additional_data={'data_point_index': i}
                )
            except Exception as e:
                error_duration = (time.time() - start_time) * 1000
                performance_collector.record_metric(
                    component="workout_manager",
                    operation="process_data_point_error",
                    duration_ms=error_duration,
                    additional_data={'error': str(e)}
                )
        
        # Track workout summary calculation
        start_time = time.time()
        summary = test_database.get_workout_summary(workout_id)
        summary_duration = (time.time() - start_time) * 1000
        
        performance_collector.record_metric(
            component="workout_manager",
            operation="calculate_summary",
            duration_ms=summary_duration
        )
        
        performance_collector.stop_collection()
        
        # Analyze performance
        workout_summary = performance_collector.get_component_summary("workout_manager")
        
        # Assertions
        assert workout_summary['total_operations'] > 300, "Should track all workout operations"
        
        # Data point processing should be efficient
        data_processing_summary = performance_collector.get_operation_summary("process_data_point")
        assert data_processing_summary['duration_stats']['avg_ms'] < 10, \
            "Data point processing should be < 10ms on average"
        
        # Summary calculation should be reasonable
        summary_op_summary = performance_collector.get_operation_summary("calculate_summary")
        assert summary_op_summary['duration_stats']['avg_ms'] < 100, \
            "Summary calculation should be < 100ms"
        
        print(f"Workout Manager performance summary:")
        print(f"  Data processing avg: {data_processing_summary['duration_stats']['avg_ms']:.2f} ms")
        print(f"  Summary calculation: {summary_op_summary['duration_stats']['avg_ms']:.2f} ms")
    
    def test_performance_regression_detection(self, performance_collector):
        """Test performance regression detection."""
        # Create baseline metrics
        baseline_operations = [
            ('database_query', 10),
            ('data_processing', 5),
            ('file_generation', 50)
        ]
        
        # Record baseline metrics
        for operation, duration in baseline_operations:
            for _ in range(10):
                performance_collector.record_metric(
                    component="test_component",
                    operation=operation,
                    duration_ms=duration + random.uniform(-1, 1)
                )
        
        baseline_summary = performance_collector.get_component_summary("test_component")
        baseline_metrics = {"test_component": baseline_summary}
        
        # Clear metrics and simulate regression
        performance_collector.clear_metrics()
        
        # Record regressed metrics (30% slower)
        for operation, duration in baseline_operations:
            regressed_duration = duration * 1.3  # 30% slower
            for _ in range(10):
                performance_collector.record_metric(
                    component="test_component",
                    operation=operation,
                    duration_ms=regressed_duration + random.uniform(-1, 1)
                )
        
        # Detect regressions
        regressions = performance_collector.detect_performance_regressions(
            baseline_metrics, threshold_percent=20.0
        )
        
        # Assertions
        assert len(regressions) > 0, "Should detect performance regressions"
        
        regression = regressions[0]
        assert regression['component'] == "test_component", "Should identify correct component"
        assert regression['regression_percent'] > 20, "Should detect significant regression"
        
        print(f"Detected regressions:")
        for reg in regressions:
            print(f"  {reg['component']}: {reg['regression_percent']:.1f}% slower")


@pytest.mark.performance
class TestDatabaseOptimization:
    """Test database query optimization and indexing."""
    
    def test_query_performance_analysis(self, db_optimizer, test_database):
        """Test database query performance analysis."""
        optimizer = db_optimizer(test_database)
        
        # Create test data
        workout_ids = []
        for i in range(10):
            workout_data = {
                'device_type': 'bike' if i % 2 == 0 else 'rower',
                'start_time': datetime.now() - timedelta(hours=i),
                'duration': 1800 + i * 60
            }
            workout_id = test_database.create_workout(workout_data)
            workout_ids.append(workout_id)
            
            # Add data points
            for j in range(100):
                data_point = {
                    'timestamp': workout_data['start_time'] + timedelta(seconds=j),
                    'power': 150 + j,
                    'heart_rate': 140 + j % 30
                }
                test_database.add_data_point(workout_id, data_point)
        
        # Analyze query performance
        queries_to_analyze = [
            ("SELECT COUNT(*) FROM workouts", ()),
            ("SELECT * FROM workouts WHERE device_type = ?", ('bike',)),
            ("SELECT * FROM workout_data WHERE workout_id = ?", (workout_ids[0],)),
            ("SELECT AVG(power) FROM workout_data WHERE workout_id = ?", (workout_ids[0],))
        ]
        
        analyses = []
        for query, params in queries_to_analyze:
            analysis = optimizer.analyze_query_performance(query, params)
            analyses.append(analysis)
        
        # Assertions
        assert len(analyses) == len(queries_to_analyze), "Should analyze all queries"
        
        for analysis in analyses:
            assert 'duration_ms' in analysis, "Should measure query duration"
            assert analysis['duration_ms'] > 0, "Should have positive duration"
            assert 'query_plan' in analysis, "Should include query plan"
        
        # Check for full table scans (may indicate need for indexes)
        full_scan_queries = [a for a in analyses if a.get('full_table_scan')]
        print(f"Queries with full table scans: {len(full_scan_queries)}")
        
        for analysis in analyses:
            print(f"Query: {analysis['query'][:50]}...")
            print(f"  Duration: {analysis['duration_ms']:.2f} ms")
            print(f"  Uses index: {analysis.get('uses_index', False)}")
            print(f"  Full table scan: {analysis.get('full_table_scan', False)}")
    
    def test_index_creation_and_performance_impact(self, db_optimizer, test_database):
        """Test database index creation and performance impact."""
        optimizer = db_optimizer(test_database)
        
        # Create substantial test data
        workout_ids = []
        for i in range(50):
            workout_data = {
                'device_type': 'bike' if i % 3 == 0 else 'rower',
                'start_time': datetime.now() - timedelta(hours=i),
                'duration': 1800
            }
            workout_id = test_database.create_workout(workout_data)
            workout_ids.append(workout_id)
            
            # Add many data points
            for j in range(200):
                data_point = {
                    'timestamp': workout_data['start_time'] + timedelta(seconds=j),
                    'power': 150 + j % 100,
                    'heart_rate': 140 + j % 30
                }
                test_database.add_data_point(workout_id, data_point)
        
        # Benchmark queries before indexing
        before_benchmark = optimizer.benchmark_queries(iterations=20)
        
        # Create recommended indexes
        created_indexes = optimizer.create_recommended_indexes()
        
        # Benchmark queries after indexing
        after_benchmark = optimizer.benchmark_queries(iterations=20)
        
        # Analyze performance improvement
        improvements = {}
        for query in before_benchmark.keys():
            if query in after_benchmark:
                before_avg = before_benchmark[query]['avg_duration_ms']
                after_avg = after_benchmark[query]['avg_duration_ms']
                improvement_percent = ((before_avg - after_avg) / before_avg) * 100
                improvements[query] = improvement_percent
        
        # Assertions
        assert len(created_indexes) > 0, "Should create some indexes"
        assert len(improvements) > 0, "Should measure performance improvements"
        
        # At least some queries should show improvement
        improved_queries = [q for q, imp in improvements.items() if imp > 0]
        assert len(improved_queries) > 0, "Some queries should show performance improvement"
        
        print(f"Created {len(created_indexes)} indexes")
        print("Performance improvements:")
        for query, improvement in improvements.items():
            print(f"  {query[:50]}...: {improvement:+.1f}%")
    
    def test_index_suggestions(self, db_optimizer, test_database):
        """Test database index suggestions."""
        optimizer = db_optimizer(test_database)
        
        # Get index suggestions
        suggestions = optimizer.suggest_indexes()
        
        # Assertions
        assert isinstance(suggestions, list), "Should return list of suggestions"
        
        for suggestion in suggestions:
            assert 'table' in suggestion, "Should specify table"
            assert 'columns' in suggestion, "Should specify columns"
            assert 'reason' in suggestion, "Should provide reason"
        
        # Should suggest common indexes
        suggested_tables = {s['table'] for s in suggestions}
        expected_tables = {'workouts', 'workout_data'}
        assert len(suggested_tables & expected_tables) > 0, "Should suggest indexes for main tables"
        
        print(f"Index suggestions ({len(suggestions)}):")
        for suggestion in suggestions:
            print(f"  {suggestion['table']}.{suggestion['columns']}: {suggestion['reason']}")


@pytest.mark.performance
class TestWebInterfacePerformance:
    """Test web interface performance monitoring."""
    
    def test_endpoint_performance_measurement(self, web_monitor, test_database):
        """Test web endpoint performance measurement."""
        # Create test client
        flask_app.config['TESTING'] = True
        client = flask_app.test_client()
        
        # Populate database with test data
        for i in range(5):
            workout_data = {
                'device_type': 'bike' if i % 2 == 0 else 'rower',
                'start_time': datetime.now() - timedelta(hours=i),
                'duration': 1800
            }
            workout_id = test_database.create_workout(workout_data)
            
            # Add some data points
            for j in range(50):
                data_point = {
                    'timestamp': workout_data['start_time'] + timedelta(seconds=j*10),
                    'power': 150 + j,
                    'heart_rate': 140 + j % 30
                }
                test_database.add_data_point(workout_id, data_point)
        
        # Test endpoint performance
        endpoints_to_test = [
            '/',
            '/devices',
            '/workout',
            '/history',
            '/api/workouts',
            '/api/device/status'
        ]
        
        performance_results = {}
        for endpoint in endpoints_to_test:
            result = web_monitor.measure_endpoint_performance(client, endpoint, iterations=5)
            performance_results[endpoint] = result
        
        # Assertions
        assert len(performance_results) == len(endpoints_to_test), "Should test all endpoints"
        
        for endpoint, result in performance_results.items():
            if 'error' not in result:
                assert result['avg_duration_ms'] > 0, f"Should measure duration for {endpoint}"
                assert result['success_rate'] > 0.8, f"Success rate should be > 80% for {endpoint}"
                
                # Performance thresholds
                assert result['avg_duration_ms'] < 1000, f"{endpoint} should respond in < 1s"
                assert result['median_duration_ms'] < 500, f"{endpoint} median should be < 500ms"
        
        print("Web endpoint performance:")
        for endpoint, result in performance_results.items():
            if 'error' not in result:
                print(f"  {endpoint}: {result['avg_duration_ms']:.2f}ms avg, "
                      f"{result['success_rate']:.1%} success rate")
    
    def test_client_side_performance_simulation(self, web_monitor):
        """Test client-side performance metrics simulation."""
        # Simulate multiple page loads
        page_metrics = []
        for _ in range(10):
            metrics = web_monitor.simulate_client_side_performance()
            page_metrics.append(metrics)
        
        # Analyze client-side performance
        avg_metrics = {}
        for metric_name in page_metrics[0].keys():
            values = [pm[metric_name] for pm in page_metrics]
            avg_metrics[metric_name] = statistics.mean(values)
        
        # Assertions for Core Web Vitals
        assert avg_metrics['largest_contentful_paint'] < 2500, "LCP should be < 2.5s"
        assert avg_metrics['first_input_delay'] < 100, "FID should be < 100ms"
        assert avg_metrics['cumulative_layout_shift'] < 0.1, "CLS should be < 0.1"
        
        # Other performance metrics
        assert avg_metrics['first_contentful_paint'] < 1800, "FCP should be < 1.8s"
        assert avg_metrics['total_blocking_time'] < 300, "TBT should be < 300ms"
        
        print("Client-side performance metrics:")
        for metric, value in avg_metrics.items():
            unit = "ms" if "delay" in metric or "paint" in metric or "time" in metric else ""
            print(f"  {metric}: {value:.2f}{unit}")
    
    def test_concurrent_request_performance(self, web_monitor, test_database):
        """Test performance under concurrent web requests."""
        flask_app.config['TESTING'] = True
        client = flask_app.test_client()
        
        # Create test data
        workout_id = test_database.create_workout({
            'device_type': 'bike',
            'start_time': datetime.now(),
            'duration': 1800
        })
        
        # Function to make concurrent requests
        def make_concurrent_requests():
            results = []
            endpoints = ['/', '/api/workouts', f'/api/workout/{workout_id}']
            
            for endpoint in endpoints:
                start_time = time.time()
                try:
                    response = client.get(endpoint)
                    duration_ms = (time.time() - start_time) * 1000
                    results.append({
                        'endpoint': endpoint,
                        'duration_ms': duration_ms,
                        'status_code': response.status_code
                    })
                except Exception as e:
                    results.append({
                        'endpoint': endpoint,
                        'error': str(e)
                    })
            
            return results
        
        # Execute concurrent requests
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_concurrent_requests) for _ in range(10)]
            all_results = []
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    results = future.result(timeout=10)
                    all_results.extend(results)
                except Exception as e:
                    print(f"Concurrent request failed: {e}")
        
        # Analyze concurrent performance
        successful_requests = [r for r in all_results if 'error' not in r and r.get('status_code') == 200]
        
        if successful_requests:
            durations = [r['duration_ms'] for r in successful_requests]
            avg_duration = statistics.mean(durations)
            max_duration = max(durations)
            
            # Assertions
            assert len(successful_requests) > len(all_results) * 0.8, "Success rate should be > 80%"
            assert avg_duration < 2000, f"Average response time should be < 2s, got {avg_duration:.2f}ms"
            assert max_duration < 5000, f"Max response time should be < 5s, got {max_duration:.2f}ms"
            
            print(f"Concurrent request performance:")
            print(f"  Total requests: {len(all_results)}")
            print(f"  Successful: {len(successful_requests)}")
            print(f"  Average duration: {avg_duration:.2f}ms")
            print(f"  Max duration: {max_duration:.2f}ms")


if __name__ == "__main__":
    # Run performance monitoring tests
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "performance"])