# Rogue Garmin Bridge Test Suite

This directory contains the comprehensive test suite for the Rogue Garmin Bridge project.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── pytest.ini              # Test-specific pytest configuration
├── unit/                    # Unit tests for individual components
├── integration/             # Integration tests for component interactions
├── simulator/               # Tests using FTMS simulator
├── fit_validation/          # Tests for FIT file validation
├── fixtures/                # Test data and fixtures
│   └── sample_workouts.json # Sample workout data for testing
└── utils/                   # Test utilities and helpers
    ├── mock_devices.py      # Mock FTMS devices and Bluetooth utilities
    ├── database_utils.py    # Database testing utilities
    └── fit_validation.py    # FIT file validation utilities
```

## Running Tests

### Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Activate virtual environment (if using):
   ```bash
   # Windows
   .\venv\Scripts\Activate.ps1
   
   # Linux/Mac
   source venv/bin/activate
   ```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests only
pytest tests/simulator/               # Simulator tests only
pytest tests/fit_validation/          # FIT validation tests only

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing
```

### Using Test Markers

Tests are organized using pytest markers:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only simulator tests
pytest -m simulator

# Run only FIT validation tests
pytest -m fit_validation

# Run slow tests
pytest -m slow

# Exclude slow tests
pytest -m "not slow"
```

### Parallel Test Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto                       # Auto-detect CPU cores
pytest -n 4                          # Use 4 processes
```

### Using the Makefile

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration
make test-simulator
make test-fit

# Run with coverage
make test-coverage

# Run slow tests
make test-slow

# Run all tests including slow ones
make test-all

# Clean up test artifacts
make clean
```

### Using the Test Runner Script

```bash
# Run all tests
python run_tests.py

# Run specific categories
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --simulator
python run_tests.py --fit

# Run with coverage
python run_tests.py --coverage

# Run with linting
python run_tests.py --lint

# Format code
python run_tests.py --format

# Run everything
python run_tests.py --all
```

## Test Fixtures

The test suite provides several useful fixtures:

### Database Fixtures
- `test_database`: Clean test database for each test
- `test_data_dir`: Temporary directory for test files

### Mock Device Fixtures
- `mock_ftms_device`: Mock FTMS device for testing
- `mock_ftms_manager`: Mock FTMS manager
- `mock_bluetooth_device`: Mock Bluetooth device

### Data Fixtures
- `sample_workout_data`: Sample workout data for bikes and rowers
- `realistic_workout_scenarios`: Realistic workout scenarios based on actual data
- `expected_fit_file_structure`: Expected FIT file structure for validation
- `test_data_factory`: Factory for generating test data

## Writing Tests

### Unit Test Example

```python
import pytest
from src.data.workout_manager import WorkoutManager

class TestWorkoutManager:
    def test_create_workout(self, test_database):
        """Test workout creation."""
        manager = WorkoutManager(database=test_database)
        
        workout_data = {
            "device_type": "bike",
            "start_time": datetime.now(),
            "duration": 600
        }
        
        workout_id = manager.create_workout(workout_data)
        assert workout_id is not None
        assert workout_id > 0
```

### Integration Test Example

```python
import pytest
from tests.utils.mock_devices import MockFTMSManager

@pytest.mark.integration
class TestDataFlow:
    async def test_end_to_end_data_flow(self, test_database):
        """Test complete data flow from device to database."""
        # Setup components
        ftms_manager = MockFTMSManager()
        workout_manager = WorkoutManager(database=test_database)
        
        # Test data flow
        await ftms_manager.start_scanning()
        devices = ftms_manager.get_discovered_devices()
        assert len(devices) > 0
```

### Simulator Test Example

```python
import pytest
from tests.utils.mock_devices import MockFTMSDevice

@pytest.mark.simulator
class TestSimulator:
    async def test_realistic_bike_simulation(self):
        """Test realistic bike workout simulation."""
        device = MockFTMSDevice("bike")
        await device.connect()
        
        device.start_workout()
        
        # Collect data for 10 seconds
        data_points = []
        for _ in range(10):
            await asyncio.sleep(1)
            data_points.append(device.current_data.copy())
        
        device.stop_workout()
        
        # Validate data progression
        assert len(data_points) == 10
        assert all(point["power"] > 0 for point in data_points)
```

### FIT Validation Test Example

```python
import pytest
from tests.utils.fit_validation import FITFileValidator

@pytest.mark.fit_validation
class TestFITValidation:
    def test_fit_file_structure(self, test_data_factory):
        """Test FIT file structure validation."""
        # Create test workout data
        workout_data = test_data_factory.create_workout_session("bike", 600)
        
        # Generate FIT file
        fit_file_path = create_test_fit_file(
            workout_data, 
            workout_data["data_points"]
        )
        
        # Validate FIT file
        validator = FITFileValidator()
        result = validator.validate_fit_file(fit_file_path)
        
        assert result["valid"]
        assert len(result["errors"]) == 0
```

## Test Configuration

### Environment Variables

Tests automatically set these environment variables:
- `TESTING=true`: Indicates test environment
- `LOG_LEVEL=DEBUG`: Sets debug logging level

### Pytest Configuration

Key pytest settings in `pytest.ini`:
- Test discovery patterns
- Coverage settings
- Markers for test categorization
- Timeout settings
- Warning filters

### CI/CD Integration

The test suite integrates with GitHub Actions:
- Runs on multiple Python versions (3.8, 3.9, 3.10, 3.11)
- Includes code quality checks (flake8, black, isort, mypy)
- Generates coverage reports
- Runs slow tests separately

## Test Data

### Sample Workouts

The `tests/fixtures/sample_workouts.json` file contains:
- Bike workout scenarios (short, medium, interval)
- Rower workout scenarios (standard, endurance)
- Error scenarios (connection drops, invalid data, missing data)

### Mock Devices

Mock devices provide realistic simulation:
- Proper workout phase progression (warmup, main, cooldown)
- Realistic data patterns based on actual workout logs
- Configurable error injection for testing edge cases
- Support for both bike and rower device types

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the virtual environment is activated and dependencies are installed
2. **Database Errors**: Check that test database cleanup is working properly
3. **Async Test Issues**: Make sure `pytest-asyncio` is installed and configured
4. **Coverage Issues**: Verify that the `src` directory is in the Python path

### Debug Mode

Run tests with debug output:
```bash
pytest -v -s --tb=long --log-cli-level=DEBUG
```

### Test Isolation

Each test runs in isolation with:
- Fresh test database
- Clean temporary directories
- Reset environment variables
- Separate mock objects

## Contributing

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Use appropriate markers (`@pytest.mark.unit`, etc.)
3. Include docstrings explaining what the test validates
4. Use fixtures for common setup/teardown
5. Ensure tests are deterministic and don't depend on external services
6. Add slow tests to the `@pytest.mark.slow` category if they take >1 second