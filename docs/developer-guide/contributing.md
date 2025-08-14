# Contributing Guidelines

Thank you for your interest in contributing to the Rogue Garmin Bridge project! This document provides guidelines and information for contributors.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Submission Process](#submission-process)
7. [Documentation](#documentation)
8. [Community](#community)

## Code of Conduct

### Our Pledge

We are committed to making participation in this project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior includes**:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes**:
- The use of sexualized language or imagery
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Project maintainers are responsible for clarifying standards of acceptable behavior and are expected to take appropriate and fair corrective action in response to any instances of unacceptable behavior.

## Getting Started

### Ways to Contribute

- **Bug Reports**: Help us identify and fix issues
- **Feature Requests**: Suggest new functionality
- **Code Contributions**: Implement features or fix bugs
- **Documentation**: Improve or expand documentation
- **Testing**: Help test new features and report issues
- **Community Support**: Help other users in discussions

### Before You Start

1. **Check Existing Issues**: Look for existing issues or discussions about your topic
2. **Read Documentation**: Familiarize yourself with the project architecture and APIs
3. **Understand the Scope**: Ensure your contribution aligns with project goals
4. **Start Small**: Consider starting with smaller issues to get familiar with the codebase

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git
- Bluetooth adapter with BLE support
- Code editor (VS Code recommended)

### Initial Setup

1. **Fork the Repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/rogue_garmin_bridge.git
   cd rogue_garmin_bridge
   ```

2. **Set Up Development Environment**
   ```bash
   # Create virtual environment
   python3.12 -m venv venv
   
   # Activate virtual environment
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Configure Git**
   ```bash
   # Add upstream remote
   git remote add upstream https://github.com/Douglas-Christian/rogue_garmin_bridge.git
   
   # Configure your identity
   git config user.name "Your Name"
   git config user.email "your.email@example.com"
   ```

4. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

5. **Verify Setup**
   ```bash
   # Run tests to ensure everything works
   pytest
   
   # Start application
   python src/web/app.py --use-simulator --device-type bike
   ```

### Development Tools

**Recommended VS Code Extensions**:
- Python
- Pylance
- Black Formatter
- Flake8
- GitLens
- REST Client

**Configuration Files**:
- `.vscode/settings.json`: VS Code settings
- `.vscode/launch.json`: Debug configurations
- `pyproject.toml`: Python project configuration
- `.pre-commit-config.yaml`: Pre-commit hooks

## Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:

**Line Length**: 88 characters (Black formatter default)

**Import Organization**:
```python
# Standard library imports
import os
import sys
from datetime import datetime

# Third-party imports
import flask
from bleak import BleakClient

# Local application imports
from src.ftms.ftms_manager import FTMSManager
from src.data.workout_manager import WorkoutManager
```

**Naming Conventions**:
- **Classes**: `PascalCase` (e.g., `WorkoutManager`)
- **Functions/Methods**: `snake_case` (e.g., `start_workout`)
- **Variables**: `snake_case` (e.g., `device_id`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`)
- **Private Methods**: `_snake_case` (e.g., `_validate_data`)

### Code Formatting

**Automatic Formatting**:
```bash
# Format code with Black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Check formatting
black --check src/ tests/
```

**Type Hints**:
Use type hints for all public functions and methods:
```python
from typing import List, Optional, Dict, Any

def process_workout_data(
    data_points: List[Dict[str, Any]], 
    device_type: str
) -> Optional[WorkoutSummary]:
    """Process workout data and return summary."""
    pass
```

### Documentation Standards

**Docstring Format** (Google Style):
```python
def calculate_training_load(
    power_data: List[int], 
    duration: int, 
    user_ftp: int
) -> float:
    """Calculate training load based on power data.
    
    Args:
        power_data: List of power values in watts
        duration: Workout duration in seconds
        user_ftp: User's Functional Threshold Power
        
    Returns:
        Training load value as a float
        
    Raises:
        ValueError: If power_data is empty or invalid
        
    Example:
        >>> power_data = [150, 160, 155, 145]
        >>> training_load = calculate_training_load(power_data, 3600, 200)
        >>> print(f"Training load: {training_load}")
    """
    pass
```

**Code Comments**:
- Use comments sparingly for complex logic
- Prefer self-documenting code with clear variable names
- Add TODO comments for future improvements
- Include references for complex algorithms

### Error Handling

**Exception Handling Pattern**:
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def connect_to_device(device_id: str) -> Optional[Device]:
    """Connect to FTMS device with proper error handling."""
    try:
        device = discover_device(device_id)
        if not device:
            logger.warning(f"Device {device_id} not found")
            return None
            
        connection = establish_connection(device)
        logger.info(f"Successfully connected to {device_id}")
        return device
        
    except BluetoothError as e:
        logger.error(f"Bluetooth error connecting to {device_id}: {e}")
        raise ConnectionError(f"Failed to connect to device: {e}")
    except Exception as e:
        logger.error(f"Unexpected error connecting to {device_id}: {e}")
        raise
```

**Custom Exceptions**:
```python
class RogueGarminBridgeError(Exception):
    """Base exception for Rogue Garmin Bridge."""
    pass

class DeviceConnectionError(RogueGarminBridgeError):
    """Raised when device connection fails."""
    pass

class DataValidationError(RogueGarminBridgeError):
    """Raised when data validation fails."""
    pass
```

### Logging Standards

**Logger Configuration**:
```python
import logging

# Module-level logger
logger = logging.getLogger(__name__)

# Log levels usage:
logger.debug("Detailed debugging information")
logger.info("General information about program execution")
logger.warning("Something unexpected happened, but program continues")
logger.error("Serious problem occurred")
logger.critical("Very serious error occurred")
```

**Structured Logging**:
```python
logger.info(
    "Workout started",
    extra={
        "workout_id": workout_id,
        "device_type": device_type,
        "user_id": user_id
    }
)
```

## Testing Guidelines

### Test Structure

**Test Organization**:
```
tests/
├── unit/                    # Unit tests
│   ├── test_ftms_manager.py
│   ├── test_workout_manager.py
│   └── test_fit_converter.py
├── integration/             # Integration tests
│   ├── test_data_flow.py
│   └── test_web_api.py
├── fixtures/                # Test data and fixtures
│   ├── sample_workouts.json
│   └── mock_devices.py
└── conftest.py             # Pytest configuration
```

### Writing Tests

**Unit Test Example**:
```python
import pytest
from unittest.mock import Mock, patch
from src.data.workout_manager import WorkoutManager

class TestWorkoutManager:
    """Test cases for WorkoutManager class."""
    
    @pytest.fixture
    def workout_manager(self):
        """Create WorkoutManager instance for testing."""
        return WorkoutManager()
    
    def test_start_workout_success(self, workout_manager):
        """Test successful workout start."""
        # Arrange
        device_type = "bike"
        
        # Act
        workout_id = workout_manager.start_workout(device_type)
        
        # Assert
        assert workout_id is not None
        assert len(workout_id) > 0
        assert workout_manager.get_workout_status(workout_id) == "active"
    
    def test_start_workout_invalid_device_type(self, workout_manager):
        """Test workout start with invalid device type."""
        # Arrange
        invalid_device_type = "invalid"
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid device type"):
            workout_manager.start_workout(invalid_device_type)
    
    @patch('src.data.workout_manager.database')
    def test_start_workout_database_error(self, mock_db, workout_manager):
        """Test workout start with database error."""
        # Arrange
        mock_db.save_workout.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            workout_manager.start_workout("bike")
```

**Integration Test Example**:
```python
import pytest
import requests
from src.web.app import create_app

class TestWorkoutAPI:
    """Integration tests for workout API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app(testing=True)
        with app.test_client() as client:
            yield client
    
    def test_start_workout_endpoint(self, client):
        """Test workout start API endpoint."""
        # Arrange
        payload = {
            "device_id": "test_device",
            "device_type": "bike"
        }
        
        # Act
        response = client.post('/api/workouts/start', json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'workout_id' in data['data']
```

### Test Coverage

**Coverage Requirements**:
- Minimum 80% overall coverage
- 90% coverage for critical components (FTMS Manager, Workout Manager)
- 100% coverage for utility functions

**Running Coverage**:
```bash
# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html
```

### Test Data and Fixtures

**Fixture Example**:
```python
# conftest.py
import pytest
from src.data.database_manager import DatabaseManager

@pytest.fixture
def sample_workout_data():
    """Provide sample workout data for testing."""
    return {
        "device_type": "bike",
        "duration": 1800,
        "data_points": [
            {"timestamp": "2025-01-12T10:30:00Z", "power": 150},
            {"timestamp": "2025-01-12T10:30:01Z", "power": 155}
        ]
    }

@pytest.fixture
def test_database():
    """Provide test database instance."""
    db = DatabaseManager(":memory:")  # In-memory SQLite
    db.create_tables()
    yield db
    db.close()
```

## Submission Process

### Branch Strategy

**Branch Naming**:
- `feature/description`: New features
- `bugfix/description`: Bug fixes
- `docs/description`: Documentation updates
- `refactor/description`: Code refactoring

**Example**:
```bash
git checkout -b feature/add-rower-support
git checkout -b bugfix/fix-connection-timeout
git checkout -b docs/update-api-reference
```

### Commit Guidelines

**Commit Message Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```bash
feat(ftms): add support for Rogue Echo Rower

- Implement rower-specific data processing
- Add stroke rate and distance calculations
- Update device discovery to include rowers

Closes #123

fix(connection): resolve Bluetooth connection timeout

The connection timeout was too aggressive, causing frequent
disconnections. Increased timeout from 10s to 30s and added
exponential backoff for reconnection attempts.

Fixes #456
```

### Pull Request Process

1. **Prepare Your Branch**
   ```bash
   # Update your fork
   git fetch upstream
   git checkout main
   git merge upstream/main
   git push origin main
   
   # Rebase your feature branch
   git checkout feature/your-feature
   git rebase main
   ```

2. **Run Pre-submission Checks**
   ```bash
   # Format code
   black src/ tests/
   isort src/ tests/
   
   # Run linting
   flake8 src/ tests/
   
   # Run tests
   pytest --cov=src
   
   # Type checking
   mypy src/
   ```

3. **Create Pull Request**
   - Use descriptive title and description
   - Reference related issues
   - Include screenshots for UI changes
   - Add test results and coverage information

**Pull Request Template**:
```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Coverage maintained or improved

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added for new functionality

## Related Issues
Closes #123
Fixes #456
```

### Review Process

**Review Criteria**:
- Code quality and style compliance
- Test coverage and quality
- Documentation completeness
- Performance impact
- Security considerations
- Backward compatibility

**Review Timeline**:
- Initial review within 48 hours
- Follow-up reviews within 24 hours
- Approval requires at least one maintainer review

## Documentation

### Documentation Types

**Code Documentation**:
- Inline comments for complex logic
- Docstrings for all public functions and classes
- Type hints for function signatures
- README updates for new features

**User Documentation**:
- User manual updates
- Installation guide changes
- Troubleshooting guide additions
- API reference updates

**Developer Documentation**:
- Architecture documentation
- Contributing guidelines
- Development setup instructions
- API documentation

### Documentation Standards

**Writing Style**:
- Clear and concise language
- Active voice preferred
- Step-by-step instructions
- Examples and code snippets

**Structure**:
- Logical organization with clear headings
- Table of contents for long documents
- Cross-references between related sections
- Consistent formatting and style

### Documentation Tools

**Markdown**:
- Use standard Markdown syntax
- Include code blocks with language specification
- Use tables for structured data
- Add images and diagrams where helpful

**API Documentation**:
- OpenAPI/Swagger specifications
- Request/response examples
- Error code documentation
- SDK examples

## Community

### Communication Channels

**GitHub**:
- Issues for bug reports and feature requests
- Discussions for general questions and ideas
- Pull requests for code contributions
- Wiki for community documentation

**Best Practices**:
- Search existing issues before creating new ones
- Use clear, descriptive titles
- Provide detailed reproduction steps for bugs
- Include system information and logs
- Be respectful and constructive in discussions

### Getting Help

**For Contributors**:
- Check existing documentation first
- Search GitHub issues and discussions
- Ask questions in GitHub discussions
- Tag maintainers for urgent issues

**For Users**:
- Read user documentation
- Check troubleshooting guide
- Search GitHub issues
- Create new issue with detailed information

### Recognition

**Contributors**:
- All contributors are recognized in CONTRIBUTORS.md
- Significant contributions highlighted in release notes
- Community recognition for helpful support

**Maintainers**:
- Project maintainers have commit access
- Responsible for code review and releases
- Guide project direction and standards

## Release Process

### Version Numbering

We follow Semantic Versioning (SemVer):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes (backward compatible)

### Release Cycle

**Regular Releases**:
- Minor releases every 2-3 months
- Patch releases as needed for critical bugs
- Major releases for significant changes

**Release Process**:
1. Feature freeze and testing period
2. Release candidate creation
3. Community testing and feedback
4. Final release and documentation update

Thank you for contributing to the Rogue Garmin Bridge project! Your contributions help make fitness tracking more accessible and enjoyable for everyone.