# Design Document

## Overview

This design document outlines the completion of the Rogue Garmin Bridge project, focusing on comprehensive testing, simulator enhancements, and final implementation for both Rogue Echo Bike and Rower equipment. The design builds upon the existing architecture while adding robust testing frameworks, realistic simulation capabilities, and comprehensive documentation.

## Architecture

The system maintains its existing modular architecture with enhancements to support comprehensive testing and improved reliability:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Test Framework │    │   Documentation │
│   (Flask App)   │    │   (pytest)      │    │   (Markdown)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Workout Manager │   FTMS Manager  │      FIT Converter          │
│                 │                 │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┬─────────────────┬─────────────────────────────┐
│    Database     │ FTMS Connector/ │      FIT Processor          │
│   (SQLite)      │   Simulator     │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## Components and Interfaces

### 1. Enhanced FTMS Simulator

**Purpose**: Provide realistic workout simulation based on actual recorded data from workout.log

**Key Enhancements**:
- Data pattern analysis from workout.log to create realistic workout profiles
- Support for both bike and rower workout scenarios
- Configurable workout phases (warm-up, main workout, intervals, cool-down)
- Proper timestamp handling and data consistency
- Error injection capabilities for testing edge cases

**Data Sources**:
- Workout.log analysis reveals typical patterns:
  - Bike workouts: Power 0-250W, Cadence 0-40 RPM, Speed 0-25 km/h
  - Heart rate progression: 90-102 BPM during recorded session
  - Distance accumulation: Consistent with speed calculations
  - Realistic workout phases with intensity variations

**Implementation Details**:
```python
class EnhancedFTMSSimulator:
    def __init__(self, device_type: str, workout_profile: str = "standard"):
        self.device_type = device_type  # "bike" or "rower"
        self.workout_profile = workout_profile  # "standard", "intervals", "endurance"
        self.workout_phases = self._load_workout_phases()
        
    def _load_workout_phases(self):
        # Load realistic workout phases based on workout.log analysis
        return {
            "warmup": {"duration": 300, "intensity": 0.3},
            "main": {"duration": 1200, "intensity": 0.7},
            "intervals": {"duration": 600, "intensity": 0.9},
            "cooldown": {"duration": 300, "intensity": 0.2}
        }
```

### 2. Comprehensive Test Framework

**Purpose**: Ensure code quality and prevent regressions through automated testing

**Test Categories**:

1. **Unit Tests**:
   - Individual function testing with mocked dependencies
   - Data validation and processing logic
   - FIT file generation components
   - Database operations

2. **Integration Tests**:
   - End-to-end data flow testing
   - FTMS Manager to Workout Manager communication
   - Database to FIT file conversion pipeline
   - Web API endpoint testing

3. **Simulator Tests**:
   - Realistic workout scenario validation
   - Data consistency checks
   - Performance under load
   - Error handling and recovery

4. **FIT File Validation Tests**:
   - Garmin Connect compatibility verification
   - Training load calculation accuracy
   - Device identification correctness
   - Speed calculation validation

**Test Structure**:
```
tests/
├── unit/
│   ├── test_ftms_manager.py
│   ├── test_workout_manager.py
│   ├── test_fit_converter.py
│   └── test_database.py
├── integration/
│   ├── test_data_flow.py
│   ├── test_web_api.py
│   └── test_end_to_end.py
├── simulator/
│   ├── test_bike_simulation.py
│   ├── test_rower_simulation.py
│   └── test_workout_scenarios.py
├── fit_validation/
│   ├── test_fit_compatibility.py
│   └── test_training_load.py
└── fixtures/
    ├── sample_workouts.json
    └── expected_fit_files/
```

### 3. FIT File Enhancement

**Purpose**: Ensure full Garmin Connect compatibility and accurate training load calculations

**Key Improvements**:
- Enhanced device identification for proper training load calculation
- Improved speed calculation algorithms based on workout.log analysis
- Comprehensive message type support (File ID, Activity, Session, Lap, Record)
- Validation against Garmin FIT SDK specifications

**Speed Calculation Enhancement**:
Based on workout.log analysis, the current system shows device-reported average speeds are inaccurate (0.13-1.07 km/h vs calculated 17+ km/h). The enhanced system will:
- Use instantaneous speed values for calculations
- Apply outlier filtering (2 standard deviations)
- Maintain running averages with proper weighting
- Validate against distance accumulation

### 4. Error Handling and Logging

**Purpose**: Provide comprehensive error handling and diagnostic capabilities

**Logging Strategy**:
- Structured logging with component-specific loggers
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Log rotation and size management
- Performance metrics logging

**Error Handling Patterns**:
- Graceful degradation for non-critical failures
- Automatic retry mechanisms for transient errors
- User-friendly error messages in web interface
- Detailed error context for debugging

### 5. Web Interface Completion

**Purpose**: Provide a complete, user-friendly interface for all application features

**Key Features**:
- Real-time workout monitoring with smooth updates
- Comprehensive workout history with charts and statistics
- Device connection management with clear status indicators
- FIT file download with proper naming conventions
- Settings management for user preferences

**Performance Optimizations**:
- Efficient data polling mechanisms
- Client-side caching for static data
- Optimized database queries
- Responsive design for various screen sizes

## Data Models

### Enhanced Workout Data Model

```python
@dataclass
class WorkoutDataPoint:
    timestamp: datetime
    device_type: str  # "bike" or "rower"
    
    # Common fields
    power: Optional[int] = None
    heart_rate: Optional[int] = None
    calories: Optional[int] = None
    distance: Optional[float] = None
    
    # Bike-specific fields
    cadence: Optional[int] = None
    speed: Optional[float] = None
    
    # Rower-specific fields
    stroke_rate: Optional[int] = None
    stroke_count: Optional[int] = None
    
    # Metadata
    data_quality: str = "good"  # "good", "estimated", "interpolated"
    source: str = "device"  # "device", "simulator", "calculated"
```

### Test Data Model

```python
@dataclass
class TestWorkoutScenario:
    name: str
    device_type: str
    duration_seconds: int
    expected_metrics: Dict[str, Any]
    data_points: List[WorkoutDataPoint]
    validation_rules: List[Callable]
```

## Testing Strategy

### 1. Simulator-Based Testing

**Realistic Workout Scenarios**:
- Short workout (5 minutes) - basic functionality
- Medium workout (20 minutes) - standard session from workout.log
- Long workout (60 minutes) - endurance session
- Interval workout - high/low intensity patterns
- Error scenarios - connection drops, invalid data

**Data Validation**:
- Timestamp consistency and uniqueness
- Metric accumulation (distance, calories)
- Average calculations accuracy
- Peak value tracking

### 2. FIT File Validation

**Compatibility Testing**:
- Upload to Garmin Connect test account
- Training load calculation verification
- VO2 max contribution validation
- Activity type recognition

**Data Integrity Testing**:
- All required message types present
- Field value ranges within specifications
- Timestamp sequence validation
- Device identification accuracy

### 3. Performance Testing

**Load Testing**:
- Extended workout sessions (2+ hours)
- High-frequency data generation (>1Hz)
- Multiple concurrent connections
- Memory usage monitoring

**Stress Testing**:
- Connection interruption recovery
- Database corruption handling
- Disk space exhaustion scenarios
- Network connectivity issues

## Error Handling

### 1. Connection Error Handling

**Bluetooth Connection Issues**:
- Automatic reconnection attempts with exponential backoff
- Clear user notification of connection status
- Graceful fallback to simulator mode for testing
- Connection quality monitoring and reporting

**Network Error Handling**:
- Offline mode support for data collection
- Automatic sync when connectivity restored
- Local data backup and recovery
- Web interface offline indicators

### 2. Data Processing Error Handling

**Invalid Data Handling**:
- Data validation with configurable thresholds
- Outlier detection and filtering
- Missing data interpolation
- Data quality indicators

**Database Error Handling**:
- Transaction rollback on failures
- Database corruption detection and repair
- Automatic backup creation
- Data export capabilities for recovery

### 3. FIT File Error Handling

**Generation Errors**:
- Validation before file creation
- Partial data handling
- Format compliance checking
- Alternative export formats (CSV, JSON)

**Upload Errors**:
- Retry mechanisms for transient failures
- Clear error messages for user action
- Manual upload fallback options
- File integrity verification

## Performance Considerations

### 1. Real-time Data Processing

**Optimization Strategies**:
- Efficient data structures for metric calculations
- Minimal memory allocation during data processing
- Asynchronous processing for non-critical operations
- Database connection pooling

### 2. Web Interface Performance

**Client-side Optimizations**:
- Efficient chart rendering with data decimation
- Progressive loading for large datasets
- Client-side caching of static data
- Optimized polling intervals

**Server-side Optimizations**:
- Database query optimization with proper indexing
- Response caching for frequently accessed data
- Efficient JSON serialization
- Connection keep-alive for WebSocket updates

### 3. Storage Optimization

**Database Design**:
- Proper indexing for common queries
- Data archiving for old workouts
- Efficient schema design
- Regular maintenance procedures

**File Management**:
- FIT file cleanup policies
- Log rotation and compression
- Temporary file cleanup
- Storage usage monitoring

## Security Considerations

### 1. Data Privacy

**Local Data Protection**:
- Database encryption at rest
- Secure file permissions
- User data anonymization options
- GDPR compliance considerations

### 2. Network Security

**Web Interface Security**:
- HTTPS enforcement in production
- Session management and timeout
- Input validation and sanitization
- CSRF protection

### 3. Bluetooth Security

**Device Communication**:
- Secure pairing procedures
- Connection authentication
- Data transmission validation
- Device identity verification

## Deployment Enhancements

### 1. Docker Improvements

**Enhanced Container Support**:
- Multi-stage builds for smaller images
- Health check endpoints
- Proper signal handling
- Resource limit configuration

### 2. Configuration Management

**Environment-based Configuration**:
- Development, testing, and production configs
- Secret management for sensitive data
- Feature flag support
- Runtime configuration updates

### 3. Monitoring and Observability

**Application Monitoring**:
- Health check endpoints
- Performance metrics collection
- Error rate monitoring
- Resource usage tracking

**Logging and Alerting**:
- Structured logging with correlation IDs
- Log aggregation and analysis
- Alert thresholds for critical issues
- Performance degradation detection