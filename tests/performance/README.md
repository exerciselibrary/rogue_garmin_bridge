# Performance and Stress Testing Suite

This directory contains comprehensive performance and stress tests for the Rogue Garmin Bridge application. The test suite validates system performance under various conditions and helps identify potential bottlenecks and optimization opportunities.

## Test Categories

### 1. Load Testing (`test_load_testing.py`)

Tests system performance with extended workout sessions and high data volumes:

- **Extended Workout Sessions**: 2+ hour workouts with continuous data processing
- **Memory Usage Validation**: Monitors for memory leaks and garbage collection efficiency
- **Database Performance**: Tests with large datasets and high insert rates
- **Resource Monitoring**: Tracks CPU, memory, and system resource usage
- **Concurrent Processing**: Multiple devices processing data simultaneously

**Key Metrics:**
- Memory growth should be < 100MB for 2-hour sessions
- Database insert rate should be > 50 points/second
- CPU usage should average < 50% during extended operations
- No significant object leaks or memory fragmentation

### 2. Stress Testing (`test_stress_testing.py`)

Tests system resilience under adverse conditions:

- **Connection Interruption**: Various Bluetooth disconnection patterns
- **Resource Constraints**: Memory pressure, CPU load, disk space limitations
- **Concurrent Access**: Multiple users and devices simultaneously
- **Chaos Engineering**: Random failures and error injection

**Scenarios:**
- Brief connection dropouts (2s every 30s)
- Extended connection loss (10s every 2 minutes)
- Intermittent connectivity issues
- Memory pressure (500MB allocation)
- CPU constraints (80% sustained load)
- Random database errors and network delays

### 3. Performance Monitoring (`test_performance_monitoring.py`)

Implements comprehensive performance metrics collection and analysis:

- **Metrics Collection**: Real-time performance data gathering
- **Database Optimization**: Query analysis and index recommendations
- **Web Interface Performance**: Response time and throughput testing
- **Regression Detection**: Automated performance regression identification

**Features:**
- Component-level performance tracking
- Database query plan analysis
- Index creation and performance impact measurement
- Client-side performance simulation
- Performance regression detection with configurable thresholds

## Running the Tests

### Quick Start

Run all performance tests:
```bash
python tests/performance/run_performance_tests.py
```

Run specific test category:
```bash
python tests/performance/run_performance_tests.py --category load
python tests/performance/run_performance_tests.py --category stress
python tests/performance/run_performance_tests.py --category monitoring
```

### Advanced Usage

Verbose output with custom report directory:
```bash
python tests/performance/run_performance_tests.py --verbose --output-dir my_reports
```

Generate report from existing results:
```bash
python tests/performance/run_performance_tests.py --report-only
```

Clean up test artifacts after completion:
```bash
python tests/performance/run_performance_tests.py --cleanup
```

### Using pytest directly

Run load tests only:
```bash
pytest tests/performance/test_load_testing.py -v -m performance
```

Run stress tests with specific markers:
```bash
pytest tests/performance/test_stress_testing.py -v -m stress
```

Run with custom markers:
```bash
pytest tests/performance/ -v -m "performance or stress" --tb=short
```

## Test Configuration

Performance thresholds and test parameters are configured in `performance_config.json`:

```json
{
  "performance_thresholds": {
    "memory": {
      "max_growth_mb_2hr": 100,
      "max_peak_mb": 300
    },
    "database": {
      "min_insert_rate_per_sec": 50,
      "max_query_time_ms": 100
    },
    "web_interface": {
      "max_response_time_ms": 1000,
      "min_success_rate_percent": 95
    }
  }
}
```

## Performance Metrics

### System Resource Monitoring

The test suite monitors:
- **Memory Usage**: RSS, VMS, growth patterns, garbage collection efficiency
- **CPU Usage**: Average, peak, sustained load patterns
- **Thread Count**: Thread creation and cleanup
- **File Descriptors**: Resource handle management

### Database Performance

Tracks database operations:
- **Query Performance**: Execution time, query plans, index usage
- **Insert Rates**: Data point insertion throughput
- **Transaction Handling**: Rollback and recovery performance
- **Index Effectiveness**: Performance impact of database indexes

### Web Interface Metrics

Measures web application performance:
- **Response Times**: Average, median, P95, P99 response times
- **Throughput**: Requests per second under load
- **Success Rates**: Error rates and availability
- **Concurrent Performance**: Multi-user access patterns

### Connection Management

Evaluates Bluetooth connectivity:
- **Connection Recovery**: Time to reconnect after interruption
- **Data Continuity**: Percentage of data retained during disruptions
- **Error Handling**: Graceful degradation and recovery

## Test Reports

The test runner generates comprehensive reports in multiple formats:

### Markdown Report
- Executive summary with pass/fail rates
- Detailed test results with performance metrics
- Performance threshold compliance
- Optimization recommendations

### JSON Results
- Machine-readable test results
- Detailed performance metrics
- Historical comparison data
- Raw measurement data

### Performance Metrics Export
- Time-series performance data
- Resource usage patterns
- Query performance statistics
- System health indicators

## Performance Optimization

### Database Optimization

The test suite includes automatic database optimization:

1. **Index Analysis**: Identifies missing indexes based on query patterns
2. **Query Optimization**: Analyzes query execution plans
3. **Performance Benchmarking**: Measures query performance before/after optimization
4. **Index Recommendations**: Suggests optimal indexes for common queries

### Memory Management

Monitors and optimizes memory usage:

1. **Leak Detection**: Identifies memory leaks and object accumulation
2. **Garbage Collection**: Analyzes GC efficiency and patterns
3. **Memory Profiling**: Tracks memory allocation patterns
4. **Resource Cleanup**: Validates proper resource disposal

### Connection Optimization

Improves Bluetooth connection reliability:

1. **Recovery Patterns**: Tests various reconnection strategies
2. **Error Handling**: Validates graceful error recovery
3. **Data Buffering**: Tests data retention during disconnections
4. **Connection Pooling**: Evaluates connection management efficiency

## Continuous Integration

### Automated Testing

The performance tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Performance Tests
  run: |
    python tests/performance/run_performance_tests.py --category all
    
- name: Upload Performance Report
  uses: actions/upload-artifact@v2
  with:
    name: performance-report
    path: performance_reports/
```

### Performance Regression Detection

Automated detection of performance regressions:
- Compares current results with baseline metrics
- Configurable threshold for regression detection (default: 20%)
- Alerts on significant performance degradation
- Historical trend analysis

### Monitoring Integration

Integration with monitoring systems:
- Exports metrics in Prometheus format
- Supports custom alerting rules
- Historical performance tracking
- Dashboard integration

## Troubleshooting

### Common Issues

1. **Test Timeouts**: Increase timeout values for slow systems
2. **Memory Constraints**: Reduce test data size for limited memory systems
3. **Database Locks**: Ensure proper test isolation and cleanup
4. **Bluetooth Issues**: Use simulator mode for systems without Bluetooth

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python tests/performance/run_performance_tests.py --verbose
```

### Test Isolation

Each test uses isolated resources:
- Temporary databases for each test
- Separate log files
- Independent configuration
- Cleanup after test completion

## Contributing

### Adding New Performance Tests

1. Create test class inheriting from appropriate base class
2. Use performance fixtures for resource monitoring
3. Include appropriate pytest markers (`@pytest.mark.performance`, `@pytest.mark.stress`)
4. Document expected performance characteristics
5. Add assertions for performance thresholds

### Performance Test Guidelines

- **Realistic Scenarios**: Use realistic data patterns and volumes
- **Measurable Metrics**: Include quantifiable performance assertions
- **Resource Cleanup**: Ensure proper cleanup after tests
- **Deterministic Results**: Minimize test result variability
- **Documentation**: Document performance expectations and thresholds

### Example Test Structure

```python
@pytest.mark.performance
class TestNewFeaturePerformance:
    async def test_feature_performance(self, performance_collector, resource_monitor):
        # Setup
        performance_collector.start_collection()
        resource_monitor.start_monitoring()
        
        # Test execution with performance tracking
        start_time = time.time()
        # ... test code ...
        duration = time.time() - start_time
        
        # Performance assertions
        assert duration < 1.0, "Operation should complete in < 1s"
        
        # Cleanup
        performance_collector.stop_collection()
        resource_monitor.stop_monitoring()
```

## Performance Baselines

### Target Performance Characteristics

- **Startup Time**: < 5 seconds
- **Memory Usage**: < 50MB baseline, < 100MB growth per 2-hour session
- **Database Operations**: > 50 inserts/second, < 100ms query time
- **Web Response**: < 500ms median, < 1s P95
- **Connection Recovery**: < 30 seconds average
- **CPU Usage**: < 50% average during normal operation

### Benchmark Results

Performance benchmarks are maintained in the `performance_reports/` directory with historical comparisons and trend analysis.

## Support

For questions about performance testing:
1. Check the test documentation and comments
2. Review performance configuration in `performance_config.json`
3. Examine test reports for detailed metrics
4. Use debug mode for troubleshooting test issues