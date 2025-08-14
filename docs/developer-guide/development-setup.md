# Development Setup Guide

This guide provides comprehensive instructions for setting up a development environment for the Rogue Garmin Bridge project.

## Prerequisites

### System Requirements

**Operating System**:
- Windows 10/11 (64-bit)
- macOS 10.15 (Catalina) or later
- Linux (Ubuntu 20.04+, Debian 10+, or equivalent)

**Hardware Requirements**:
- 4GB RAM minimum (8GB recommended)
- 2GB free disk space
- Bluetooth adapter with BLE support
- Internet connection for dependency installation

### Required Software

**Python 3.12+**:
- Required for `pyftms` library compatibility
- Download from [python.org](https://www.python.org/downloads/)
- Ensure pip is included and up to date

**Git**:
- Version control system
- Download from [git-scm.com](https://git-scm.com/)
- Configure with your name and email

**Code Editor**:
- Visual Studio Code (recommended)
- PyCharm
- Sublime Text
- Vim/Neovim

## Development Environment Setup

### 1. Repository Setup

**Clone the Repository**:
```bash
# Clone your fork (replace YOUR_USERNAME)
git clone https://github.com/YOUR_USERNAME/rogue_garmin_bridge.git
cd rogue_garmin_bridge

# Add upstream remote
git remote add upstream https://github.com/Douglas-Christian/rogue_garmin_bridge.git

# Verify remotes
git remote -v
```

**Configure Git**:
```bash
# Set your identity
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Optional: Set up GPG signing
git config user.signingkey YOUR_GPG_KEY_ID
git config commit.gpgsign true
```

### 2. Python Environment Setup

**Create Virtual Environment**:
```bash
# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Verify Python version
python --version  # Should show 3.12+
```

**Install Dependencies**:
```bash
# Upgrade pip
pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Verify installation
pip list
```

### 3. Development Tools Setup

**Pre-commit Hooks**:
```bash
# Install pre-commit hooks
pre-commit install

# Test pre-commit hooks
pre-commit run --all-files
```

**Environment Variables**:
Create a `.env` file in the project root:
```bash
# .env file
DEBUG=True
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///data/workouts_dev.db
LOG_LEVEL=DEBUG
```

**Development Configuration**:
Create `config/development.py`:
```python
import os
from config.base import Config

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data/workouts_dev.db')
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    LOG_TO_FILE = True
    
    # FTMS Settings
    USE_SIMULATOR = True
    SIMULATOR_DEVICE_TYPE = 'bike'
    
    # Performance
    CHART_UPDATE_INTERVAL = 500  # Faster updates for development
    DATA_RETENTION_DAYS = 30     # Less data retention for development
```

### 4. IDE Configuration

#### Visual Studio Code Setup

**Install Extensions**:
```bash
# Install VS Code extensions via command line
code --install-extension ms-python.python
code --install-extension ms-python.pylance
code --install-extension ms-python.black-formatter
code --install-extension ms-python.flake8
code --install-extension ms-python.mypy-type-checker
code --install-extension eamodio.gitlens
code --install-extension humao.rest-client
```

**VS Code Settings** (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".coverage": true,
        "htmlcov": true
    },
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

**Launch Configuration** (`.vscode/launch.json`):
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flask App",
            "type": "python",
            "request": "launch",
            "program": "src/web/app.py",
            "args": ["--debug", "--use-simulator", "--device-type", "bike"],
            "console": "integratedTerminal",
            "env": {
                "FLASK_ENV": "development",
                "DEBUG": "True"
            }
        },
        {
            "name": "Run Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal"
        },
        {
            "name": "Debug Test",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["${file}", "-v", "-s"],
            "console": "integratedTerminal"
        }
    ]
}
```

#### PyCharm Setup

**Project Configuration**:
1. Open project in PyCharm
2. Configure Python interpreter: Settings → Project → Python Interpreter
3. Select virtual environment: `./venv/bin/python`
4. Enable Django support if needed

**Code Style Configuration**:
1. Settings → Editor → Code Style → Python
2. Set line length to 88 (Black formatter default)
3. Enable "Optimize imports on the fly"
4. Configure import sorting to match isort settings

### 5. Database Setup

**Development Database**:
```bash
# Create data directory
mkdir -p data

# Initialize development database
python -c "
from src.data.database_manager import DatabaseManager
db = DatabaseManager('data/workouts_dev.db')
db.create_tables()
print('Development database initialized')
"
```

**Test Database**:
```bash
# Test database is created automatically during tests
# Using in-memory SQLite for speed
pytest tests/unit/test_database.py -v
```

### 6. Bluetooth Development Setup

#### Linux Setup

**Install Bluetooth Dependencies**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install bluetooth bluez libbluetooth-dev

# Enable Bluetooth service
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Add user to bluetooth group
sudo usermod -a -G bluetooth $USER
```

**Configure Permissions**:
```bash
# Create udev rule for development
sudo tee /etc/udev/rules.d/99-bluetooth-dev.rules << EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="8087", ATTRS{idProduct}=="0025", MODE="0666"
KERNEL=="hci*", GROUP="bluetooth", MODE="0664"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### Windows Setup

**Bluetooth Driver Verification**:
1. Open Device Manager
2. Expand "Bluetooth" section
3. Verify Bluetooth adapter is present and enabled
4. Update drivers if needed

**Windows Subsystem for Linux (WSL)**:
```bash
# Note: Bluetooth support in WSL is limited
# Use Windows native Python for Bluetooth development
# Or use Docker with --privileged flag
```

#### macOS Setup

**Bluetooth Permissions**:
1. System Preferences → Security & Privacy → Privacy
2. Select "Bluetooth" from the list
3. Add Terminal or your IDE to allowed applications
4. Grant necessary permissions

### 7. Testing Setup

**Test Configuration**:
Create `pytest.ini` in project root:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=src
    --cov-report=term-missing
    --cov-report=html
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    simulator: Tests requiring simulator
```

**Test Environment Variables**:
Create `tests/.env`:
```bash
TESTING=True
DATABASE_URL=sqlite:///:memory:
USE_SIMULATOR=True
LOG_LEVEL=WARNING
```

**Run Test Suite**:
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_workout_manager.py -v
```

### 8. Development Workflow

#### Daily Development Routine

**Start Development Session**:
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Update from upstream
git fetch upstream
git checkout main
git merge upstream/main

# Start development server
python src/web/app.py --debug --use-simulator --device-type bike
```

**Code Quality Checks**:
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Run tests
pytest
```

#### Feature Development Workflow

**Create Feature Branch**:
```bash
# Create and switch to feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ... edit files ...

# Stage and commit changes
git add .
git commit -m "feat: add your feature description"
```

**Pre-commit Validation**:
```bash
# Pre-commit hooks run automatically, but you can run manually
pre-commit run --all-files

# Fix any issues and commit again
git add .
git commit -m "fix: address pre-commit issues"
```

**Push and Create PR**:
```bash
# Push feature branch
git push origin feature/your-feature-name

# Create pull request on GitHub
# Use the GitHub web interface or GitHub CLI
gh pr create --title "Add your feature" --body "Description of changes"
```

### 9. Debugging Setup

#### Application Debugging

**Debug Configuration**:
```python
# src/web/app.py debug mode
if __name__ == '__main__':
    import os
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=debug_mode,
        use_reloader=debug_mode
    )
```

**Logging Configuration for Development**:
```python
# src/utils/logging_config.py
import logging
import sys

def setup_development_logging():
    """Configure logging for development environment."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/development.log')
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('bleak').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
```

#### Bluetooth Debugging

**Enable Bluetooth Logging**:
```python
# Enable detailed Bluetooth logging
import logging
logging.getLogger('bleak').setLevel(logging.DEBUG)
logging.getLogger('pyftms').setLevel(logging.DEBUG)
```

**Bluetooth Diagnostic Tools**:
```bash
# Linux Bluetooth debugging
sudo btmon  # Monitor Bluetooth traffic

# Check Bluetooth status
bluetoothctl
> show
> scan on
> devices

# Windows Bluetooth debugging
# Use Bluetooth LE Explorer from Microsoft Store
```

### 10. Performance Profiling

#### Application Profiling

**Profile Flask Application**:
```python
# Add to src/web/app.py for development
from werkzeug.middleware.profiler import ProfilerMiddleware

if app.config.get('PROFILING'):
    app.wsgi_app = ProfilerMiddleware(
        app.wsgi_app,
        restrictions=[30],  # Show top 30 functions
        profile_dir='profiles'
    )
```

**Memory Profiling**:
```bash
# Install memory profiler
pip install memory-profiler

# Profile specific function
python -m memory_profiler src/data/workout_manager.py

# Line-by-line profiling
@profile
def your_function():
    # Your code here
    pass
```

#### Database Profiling

**SQLite Query Analysis**:
```python
# Enable SQLite query logging
import sqlite3
sqlite3.enable_callback_tracebacks(True)

# Log slow queries
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### 11. Docker Development Environment

#### Development Docker Setup

**Dockerfile.dev**:
```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bluetooth \
    bluez \
    libbluetooth-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements*.txt ./
RUN pip install -r requirements.txt
RUN pip install -r requirements-dev.txt

# Copy source code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 developer
USER developer

EXPOSE 5000

CMD ["python", "src/web/app.py", "--host", "0.0.0.0", "--use-simulator"]
```

**docker-compose.dev.yml**:
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "5000:5000"
    volumes:
      - .:/app
      - /app/venv  # Exclude venv from volume mount
    environment:
      - DEBUG=True
      - FLASK_ENV=development
      - USE_SIMULATOR=True
    privileged: true  # Required for Bluetooth access
    network_mode: host  # Required for Bluetooth on Linux
```

**Run Development Environment**:
```bash
# Build and run development container
docker-compose -f docker-compose.dev.yml up --build

# Run tests in container
docker-compose -f docker-compose.dev.yml exec app pytest

# Shell access
docker-compose -f docker-compose.dev.yml exec app bash
```

### 12. Troubleshooting Development Issues

#### Common Issues and Solutions

**Python Version Issues**:
```bash
# Check Python version
python --version
which python

# If wrong version, recreate virtual environment
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Dependency Conflicts**:
```bash
# Clear pip cache
pip cache purge

# Reinstall dependencies
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

**Bluetooth Permission Issues (Linux)**:
```bash
# Check user groups
groups $USER

# Add to bluetooth group if missing
sudo usermod -a -G bluetooth $USER

# Logout and login again
```

**Port Already in Use**:
```bash
# Find process using port 5000
lsof -i :5000  # Linux/macOS
netstat -ano | findstr :5000  # Windows

# Kill process
kill -9 <PID>  # Linux/macOS
taskkill /PID <PID> /F  # Windows
```

**Database Lock Issues**:
```bash
# Remove database lock
rm data/workouts_dev.db-wal
rm data/workouts_dev.db-shm

# Or recreate database
rm data/workouts_dev.db
python -c "from src.data.database_manager import DatabaseManager; DatabaseManager('data/workouts_dev.db').create_tables()"
```

#### Getting Help

**Debug Information Collection**:
```bash
# System information
python --version
pip list
git status
git log --oneline -5

# Application logs
tail -50 logs/development.log

# Test results
pytest --tb=long -v
```

**Community Support**:
- GitHub Issues: Report bugs and ask questions
- GitHub Discussions: General development questions
- Code Review: Request feedback on pull requests

This development setup guide provides everything needed to start contributing to the Rogue Garmin Bridge project. Follow the steps carefully and refer back to this guide when setting up new development environments.