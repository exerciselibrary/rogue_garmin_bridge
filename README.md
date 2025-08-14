# Rogue Garmin Bridge

A comprehensive Python application that bridges Rogue fitness equipment (Echo Bike and Rower) to Garmin Connect, providing seamless workout tracking, real-time monitoring, and advanced data management capabilities.

## Overview

Rogue Garmin Bridge connects to Rogue Echo Bike and Rower equipment via Bluetooth Low Energy (BLE) using the Fitness Machine Service (FTMS) standard through the `pyftms` library. It collects workout metrics, processes the data in real-time, and converts it to the Garmin FIT file format for upload to Garmin Connect. The application features a modern web-based interface with comprehensive device management, workout monitoring, and data analysis tools.

## Key Features

### 🔗 **Advanced Device Connectivity**
* **FTMS Bluetooth Support**: Robust BLE connectivity using `pyftms` library
* **Device Pairing Wizard**: Step-by-step guidance for connecting equipment
* **Auto-reconnection**: Automatic reconnection with exponential backoff
* **Connection Quality Monitoring**: Real-time signal strength and data rate indicators
* **Comprehensive Diagnostics**: Built-in troubleshooting and system health checks

### 📊 **Real-time Workout Monitoring**
* **Live Metrics Display**: Power, heart rate, cadence/stroke rate, speed, distance, and calories
* **Interactive Charts**: Real-time data visualization with responsive design
* **Workout Phase Tracking**: Automatic detection of warm-up, main workout, and cool-down phases
* **Performance Indicators**: Power zones, training load, and intensity metrics
* **Data Decimation**: Optimized chart rendering for smooth performance

### 📈 **Advanced Workout History & Analytics**
* **Comprehensive History**: Detailed workout records with filtering and search
* **Performance Analysis**: Charts, trends, and statistical analysis
* **Workout Comparison**: Side-by-side comparison of multiple sessions
* **Export Capabilities**: Multiple format support (JSON, CSV, FIT)
* **Data Visualization**: Interactive charts with zoom, pan, and metric selection

### ⚙️ **Enhanced Settings & Configuration**
* **User Profile Management**: Complete profile with unit preferences and biometric data
* **Workout Preferences**: Customizable auto-start, data recording intervals, and power smoothing
* **System Configuration**: Connection timeouts, logging levels, and device type preferences
* **Backup & Restore**: Complete data backup and restore functionality
* **Data Management**: Storage monitoring, cleanup tools, and export options

### 🔧 **Development & Testing Tools**
* **FTMS Device Simulator**: Realistic simulation for testing without physical hardware
* **Comprehensive Test Suite**: Unit, integration, and end-to-end testing
* **FIT File Analysis**: Tools for validating and analyzing generated FIT files
* **Performance Monitoring**: Built-in performance metrics and optimization

## System Requirements

* Python 3.12+ (due to `pyftms` dependency)
* Bluetooth adapter with BLE support
* Operating System: Windows, macOS, or Linux (Raspberry Pi compatible)
* Web browser for accessing the user interface

## Prerequisites

* Python 3.12 or higher
* pip (Python package installer)
* Git (optional, for cloning the repository)

## Installation

1. Clone the repository (or download and extract the ZIP file):
    ```
    git clone https://github.com/Douglas-Christian/rogue_garmin_bridge.git
    cd rogue_garmin_bridge
    ```

2. Create and activate a virtual environment (optional but recommended):
    ```
    python3.12 -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3. Install the required dependencies:
    ```
    pip install -r requirements.txt
    ```

## Usage

1. Navigate to the project directory:
    ```
    cd rogue_garmin_bridge
    ```

2. Start the web application:
    ```
    python3.12 src/web/app.py
    ```

3. Open a web browser and navigate to:
    ```
    http://localhost:5000
    ```

### Quick Start Guide

#### 1. Device Connection
* **New Users**: Use the Device Pairing Wizard for step-by-step guidance
* **Echo Bike**: Press and hold "Connect" button for 2 seconds until you hear beeps
* **Echo Rower**: Select "Connect" → "Connect to App" from the menu
* Navigate to "Devices" page, click "Discover Devices", and connect to your equipment

#### 2. Workout Tracking
* Navigate to the "Workout" page
* Click "Start Workout" to begin real-time tracking
* Monitor live metrics: power, heart rate, cadence/stroke rate, speed, distance, calories
* View real-time charts and performance indicators
* Click "End Workout" when finished

#### 3. Workout Analysis
* Navigate to "History" page to view all past workouts
* Use filters and search to find specific sessions
* Click on any workout for detailed analysis with interactive charts
* Compare multiple workouts side-by-side
* Export data in various formats (JSON, CSV, FIT)

#### 4. Garmin Connect Integration
* Select a workout from the History page
* Click "Generate FIT" to create a Garmin-compatible file
* Download and manually upload to Garmin Connect
* FIT files include proper training load calculation for accurate Garmin metrics

#### 5. Settings & Configuration
* Navigate to "Settings" to configure user profile and preferences
* Set up workout preferences (auto-start, data recording intervals, power smoothing)
* Configure system settings (connection timeouts, logging, unit preferences)
* Use backup/restore functionality to protect your data

## Recent Major Updates (2025)

### 🚀 **Complete Web Interface Overhaul**
* **Enhanced Device Management**: Advanced connection management with pairing wizard, diagnostics, and troubleshooting guides
* **Real-time Monitoring Improvements**: Optimized data polling, client-side caching, and responsive charts with proper data decimation
* **Advanced Workout History**: Comprehensive filtering, search, detailed analysis, and comparison capabilities
* **Settings & Configuration Management**: Complete user profile system, workout preferences, and data management tools

### 🔧 **Technical Improvements**
* **Migration to `pyftms`**: Replaced `pycycling` with `pyftms` for more robust FTMS communication and improved rower support
* **Python 3.12 Requirement**: Updated to Python 3.12 for latest `pyftms` compatibility
* **Enhanced FIT File Generation**: Proper training load calculation and improved speed metrics for Garmin Connect compatibility
* **Comprehensive Testing**: Added extensive unit, integration, and simulator-based testing
* **Performance Optimization**: Improved data processing, memory usage, and UI responsiveness

### 📊 **Data & Analytics Enhancements**
* **Advanced Workout Analysis**: Power zones, training phases, and performance metrics
* **Export & Backup System**: Multiple export formats with complete backup and restore functionality
* **Storage Management**: Built-in storage monitoring and cleanup tools
* **FIT File Analysis Tools**: Validation and comparison tools for ensuring Garmin Connect compatibility

## Project Structure

```
rogue_garmin_bridge/
├── src/                           # Source code
│   ├── ftms/                      # FTMS connectivity and device management
│   │   ├── ftms_manager.py        # Unified device management interface
│   │   ├── ftms_connector.py      # Real device BLE connectivity
│   │   └── ftms_simulator.py      # Device simulator for testing
│   ├── data/                      # Data processing and storage
│   │   ├── database.py            # SQLite database operations
│   │   ├── workout_manager.py     # Workout session management
│   │   └── data_processor.py      # Data analysis and processing
│   ├── fit/                       # FIT file generation and analysis
│   │   ├── fit_converter.py       # Garmin FIT format conversion
│   │   ├── fit_analyzer.py        # FIT file analysis tools
│   │   ├── fit_processor.py       # Advanced FIT processing
│   │   └── speed_calculator.py    # Speed calculation utilities
│   ├── web/                       # Web interface (Flask application)
│   │   ├── app.py                 # Main Flask application
│   │   ├── templates/             # HTML templates
│   │   │   ├── devices.html       # Enhanced device management
│   │   │   ├── workout.html       # Real-time workout monitoring
│   │   │   ├── history.html       # Advanced workout history
│   │   │   └── settings.html      # Comprehensive settings management
│   │   └── static/                # Static assets
│   │       ├── css/style.css      # Enhanced styling
│   │       └── js/                # JavaScript modules
│   │           ├── device-management.js    # Device connection management
│   │           ├── workout-monitoring.js   # Real-time workout display
│   │           └── workout-history.js      # History and analytics
│   └── utils/                     # Utility modules
│       └── logging_config.py      # Centralized logging configuration
├── tests/                         # Comprehensive test suite
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── fixtures/                  # Test data and fixtures
├── docs/                          # Documentation
│   └── testing_with_simulator.md  # Simulator usage guide
├── fit_files/                     # Generated FIT files (runtime)
├── logs/                          # Application logs (runtime)
└── requirements.txt               # Python dependencies
```

## Web Interface Features

### Device Management
* **Enhanced Connection Interface**: Real-time status indicators, signal strength monitoring
* **Device Pairing Wizard**: Step-by-step guidance for new users
* **Auto-reconnection**: Automatic reconnection with user feedback
* **Diagnostic Tools**: Built-in system health checks and troubleshooting guides

### Workout Monitoring
* **Real-time Charts**: Interactive, responsive charts with data decimation
* **Performance Metrics**: Power zones, training load, and intensity indicators
* **Workout Phases**: Automatic detection of warm-up, main workout, and cool-down
* **Connection Quality**: Live monitoring of data rate and signal strength

### Workout History & Analytics
* **Advanced Filtering**: Search and filter by date, duration, type, and metrics
* **Detailed Analysis**: Interactive charts with zoom, pan, and metric selection
* **Workout Comparison**: Side-by-side comparison of multiple sessions
* **Export Options**: JSON, CSV, and FIT format exports with date range selection

### Settings & Configuration
* **User Profile**: Complete biometric data with unit preference management
* **Workout Preferences**: Auto-start, data recording intervals, power smoothing
* **System Settings**: Connection timeouts, logging levels, device preferences
* **Data Management**: Backup/restore, storage monitoring, and cleanup tools

## Configuration

### Web Interface Configuration
All configuration is available through the comprehensive Settings page in the web interface:

* **User Profile**: Personal information, biometric data, unit preferences
* **Workout Preferences**: Default settings, auto-start options, data recording
* **System Configuration**: Connection settings, logging, device preferences
* **Data Management**: Backup/restore, export options, storage cleanup

### Environment Variables
Advanced users can also configure via environment variables:

* `PORT`: Web server port (default: 5000)
* `DEBUG`: Enable debug mode (default: False)
* `DATABASE_URL`: Database location (default: SQLite in data directory)
* `SECRET_KEY`: Session encryption key (required for production)

## Development & Testing

### FTMS Device Simulator

For development and testing without physical hardware:

```bash
# Start with simulator enabled
python3.12 src/web/app.py --use-simulator --device-type bike
python3.12 src/web/app.py --use-simulator --device-type rower

# Or enable via web interface Settings page
```

The simulator provides realistic workout data and supports all application features. See [Testing with the FTMS Simulator](docs/testing_with_simulator.md) for detailed usage instructions.

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/                    # Unit tests
pytest tests/integration/             # Integration tests
pytest -m simulator                  # Simulator tests

# Run with coverage
pytest --cov=src --cov-report=html

# Run performance tests
pytest -m slow
```

### FIT File Analysis Tools

Built-in tools for analyzing and validating FIT files:

* **FIT Analyzer**: `src/fit/fit_analyzer.py` - Comprehensive FIT file analysis
* **FIT Processor**: `src/fit/fit_processor.py` - Advanced processing and validation
* **Speed Calculator**: `src/fit/speed_calculator.py` - Speed calculation utilities

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Troubleshooting

### Built-in Diagnostics

The application includes comprehensive diagnostic tools accessible via the web interface:

* **Device Diagnostics**: Navigate to Devices page → "Run Diagnostics" for system health checks
* **Connection Quality Monitoring**: Real-time signal strength, data rate, and connection stability metrics
* **Troubleshooting Guides**: Built-in guides for common connection and data issues

### Common Issues

* **Bluetooth Connection Problems**: 
  - Use the Device Pairing Wizard for step-by-step guidance
  - Check Bluetooth adapter BLE support and drivers
  - Ensure `bluez` (Linux) or appropriate BLE drivers are installed
  
* **Device Not Found**: 
  - Verify equipment is powered on and in pairing mode
  - Use the connection quality indicators to check signal strength
  - Try the auto-reconnection feature if connection drops
  
* **Data Issues**: 
  - Check connection quality metrics in the Devices page
  - Use the built-in FIT file analysis tools for validation
  - Review workout data in the History page for completeness

### Advanced Troubleshooting

* **Log Analysis**: Check application logs in the `logs/` directory
* **Database Issues**: Use the backup/restore functionality in Settings
* **Performance Problems**: Monitor system resources via the diagnostic tools
* **FIT File Validation**: Use the built-in FIT analysis tools for Garmin Connect compatibility

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

* Rogue Fitness for their FTMS-compatible equipment
* The Garmin Connect team for their fitness platform
* All contributors to the Python libraries used in this project, especially the `pyftms` and `bleak` libraries.
