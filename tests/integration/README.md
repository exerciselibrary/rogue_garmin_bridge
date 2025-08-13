# Integration Tests for Rogue Garmin Bridge

This directory contains comprehensive integration tests for the Rogue Garmin Bridge project, covering data flow validation across all system components.

## Test Structure

### 1. End-to-End Data Flow Tests (`test_end_to_end_data_flow.py`)
- **Purpose**: Test complete workflow from simulator to FIT file generation
- **Coverage**: 
  - Complete bike and rower workout flows
  - Data consistency across all system components
  - Workout session management with realistic data volumes
  - Error propagation and recovery mechanisms
  - Performance testing under load
  - Memory usage monitoring

### 2. Web API Integration Tests (`test_web_api_integration.py`)
- **Purpose**: Test all REST endpoints with various data scenarios
- **Coverage**:
  - Device discovery and connection APIs
  - Workout management endpoints
  - Real-time data updates and status polling
  - File upload/download functionality
  - Error handling and response formatting
  - Concurrent API request handling

### 3. Cross-Component Integration Tests (`test_cross_component_integration.py`)
- **Purpose**: Test integration between system components
- **Coverage**:
  - FTMS Manager to Workout Manager data flow
  - Workout Manager to Database integration
  - Database to FIT Converter pipeline
  - Component error handling and graceful degradation
  - Transaction handling and data integrity

## Requirements Covered

These integration tests fulfill the following requirements from the specification:

- **3.2**: Integration tests validate data flow between components
- **5.1, 5.2, 5.3, 5.4**: Web interface functionality and real-time updates
- **6.3, 6.4**: Error handling and graceful degradation
- **8.1, 8.2, 8.4**: Performance and reliability under various conditions

## Running the Tests

### Prerequisites

1. Install required dependencies:
   ```bash
   pip install pytest pytest-asyncio pytest-cov
   ```

2. Ensure the project structure is set up correctly with all source modules available.

### Running All Integration Tests

```bash
# From the project root directory
python -m pytest tests/integration/ -v

# Or use the test runner script
python tests/integration/run_integration_tests.py -v
```

### Running Specific Test Categories

```bash
# End-to-end tests only
python tests/integration/run_integration_tests.py --end-to-end

# Web API tests only
python tests/integration/run_integration_tests.py --web-api

# Cross-component tests only
python tests/integration/run_integration_tests.py --cross-component
```

### Running Tests with Pattern Matching

```bash
# Run tests matching a specific pattern
python tests/integration/run_integration_tests.py -k "test_complete_bike_workout"

# Run tests for a specific component
python tests/integration/run_integration_tests.py -k "ftms"
```

### Running with Coverage

```bash
# Run with coverage report
python -m pytest tests/integration/ --cov=src --cov-report=html
```

## Test Environment

The integration tests create isolated test environments for each test:

- **Temporary Directories**: Each test creates its own temporary directory for databases and files
- **Mock Components**: Uses realistic mocks and simulators for hardware components
- **Database Isolation**: Each test uses a separate SQLite database
- **Automatic Cleanup**: All temporary resources are cleaned up after each test

## Test Data

The tests use realistic workout data patterns based on analysis of actual workout logs:

- **Bike Workouts**: Power 0-250W, Cadence 0-40 RPM, Speed 0-25 km/h
- **Rower Workouts**: Power 0-300W, Stroke Rate 18-32 SPM
- **Heart Rate**: Realistic progression patterns (90-180 BPM)
- **Workout Phases**: Warm-up, main workout, intervals, cool-down

## Performance Benchmarks

The tests include performance benchmarks to ensure system reliability:

- **Data Rate**: Minimum 0.8 Hz data processing
- **Response Time**: API responses < 100ms average
- **Memory Usage**: < 100MB growth during extended sessions
- **File Generation**: FIT files generated within reasonable time limits

## Error Scenarios Tested

The integration tests cover various error scenarios:

- **Connection Failures**: Bluetooth device connection issues
- **Database Errors**: SQLite connection and transaction failures
- **Data Processing Errors**: Invalid or corrupted workout data
- **File System Errors**: Disk space and permission issues
- **Memory Pressure**: Large dataset processing
- **Concurrent Access**: Multiple simultaneous operations

## Debugging Failed Tests

### Common Issues

1. **Import Errors**: Ensure all source modules are in the Python path
2. **Database Locks**: Check for lingering database connections
3. **File Permissions**: Verify write permissions for temporary directories
4. **Async Issues**: Ensure proper async/await usage in test code

### Debug Mode

Run tests with maximum verbosity and logging:

```bash
python tests/integration/run_integration_tests.py -v --tb=long
```

### Individual Test Debugging

Run a specific test with detailed output:

```bash
python -m pytest tests/integration/test_end_to_end_data_flow.py::TestEndToEndDataFlow::test_complete_bike_workout_flow -v -s
```

## Contributing

When adding new integration tests:

1. Follow the existing test structure and naming conventions
2. Use appropriate fixtures for test setup and cleanup
3. Include both positive and negative test cases
4. Add performance assertions where relevant
5. Document any special requirements or setup needed
6. Ensure tests are deterministic and don't depend on external resources

## Test Markers

The tests use pytest markers for categorization:

- `@pytest.mark.integration`: General integration tests
- `@pytest.mark.asyncio`: Async tests requiring event loop
- `@pytest.mark.slow`: Tests that take longer to execute

Run specific marker categories:

```bash
# Run only async tests
python -m pytest tests/integration/ -m asyncio

# Skip slow tests
python -m pytest tests/integration/ -m "not slow"
```