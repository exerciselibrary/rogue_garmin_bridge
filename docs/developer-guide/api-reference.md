# API Reference

This document provides comprehensive documentation for all REST API endpoints and WebSocket interfaces available in the Rogue Garmin Bridge application.

## Base URL

All API endpoints are relative to the base URL:
```
http://localhost:5000/api
```

## Authentication

Currently, the API uses session-based authentication. Future versions may include API key authentication for programmatic access.

## Response Format

All API responses follow a consistent JSON format:

**Success Response**:
```json
{
    "success": true,
    "data": {
        // Response data
    },
    "message": "Operation completed successfully"
}
```

**Error Response**:
```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message",
        "details": {
            // Additional error context
        }
    }
}
```

## Device Management API

### List Available Devices

Discover and list all available FTMS devices.

**Endpoint**: `GET /api/devices/discover`

**Response**:
```json
{
    "success": true,
    "data": {
        "devices": [
            {
                "id": "device_001",
                "name": "Rogue Echo Bike",
                "type": "bike",
                "address": "AA:BB:CC:DD:EE:FF",
                "rssi": -45,
                "services": ["fitness_machine"],
                "manufacturer": "Rogue Fitness",
                "is_connected": false
            }
        ]
    }
}
```

### Get Device Status

Get current status of a specific device.

**Endpoint**: `GET /api/devices/{device_id}/status`

**Parameters**:
- `device_id` (string): Unique device identifier

**Response**:
```json
{
    "success": true,
    "data": {
        "device_id": "device_001",
        "name": "Rogue Echo Bike",
        "connection_status": "connected",
        "signal_strength": "good",
        "signal_rssi": -42,
        "data_rate": 1.0,
        "last_seen": "2025-01-12T10:30:00Z",
        "battery_level": 85,
        "firmware_version": "1.2.3",
        "connection_quality": {
            "stability": 0.95,
            "packet_loss": 0.02,
            "latency_ms": 15
        }
    }
}
```

### Connect to Device

Establish connection to a specific device.

**Endpoint**: `POST /api/devices/{device_id}/connect`

**Parameters**:
- `device_id` (string): Unique device identifier

**Request Body**:
```json
{
    "timeout": 30,
    "auto_reconnect": true,
    "connection_options": {
        "preferred_connection_interval": 1000,
        "signal_threshold": -70
    }
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "device_id": "device_001",
        "connection_status": "connected",
        "connection_time": "2025-01-12T10:30:00Z"
    }
}
```

### Disconnect from Device

Disconnect from a specific device.

**Endpoint**: `POST /api/devices/{device_id}/disconnect`

**Parameters**:
- `device_id` (string): Unique device identifier

**Response**:
```json
{
    "success": true,
    "data": {
        "device_id": "device_001",
        "connection_status": "disconnected",
        "disconnection_time": "2025-01-12T10:35:00Z"
    }
}
```

### Run Device Diagnostics

Run comprehensive diagnostics on device connection.

**Endpoint**: `POST /api/devices/{device_id}/diagnostics`

**Response**:
```json
{
    "success": true,
    "data": {
        "device_id": "device_001",
        "diagnostics": {
            "bluetooth_adapter": {
                "status": "ok",
                "version": "5.0",
                "driver": "Intel Wireless Bluetooth"
            },
            "device_connection": {
                "status": "ok",
                "signal_strength": "good",
                "data_transmission": "stable"
            },
            "data_quality": {
                "status": "ok",
                "packet_loss": 0.01,
                "data_completeness": 0.99
            },
            "recommendations": [
                "Connection quality is excellent",
                "No issues detected"
            ]
        }
    }
}
```

## Workout Management API

### Start Workout

Begin a new workout session.

**Endpoint**: `POST /api/workouts/start`

**Request Body**:
```json
{
    "device_id": "device_001",
    "device_type": "bike",
    "workout_settings": {
        "auto_pause": true,
        "recording_interval": 1,
        "power_smoothing": true
    },
    "user_profile": {
        "weight_kg": 75,
        "age": 30,
        "max_heart_rate": 190
    }
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "workout_id": "workout_12345",
        "start_time": "2025-01-12T10:30:00Z",
        "device_type": "bike",
        "status": "active"
    }
}
```

### Get Live Workout Data

Get real-time data for an active workout.

**Endpoint**: `GET /api/workouts/{workout_id}/live`

**Parameters**:
- `workout_id` (string): Unique workout identifier

**Response**:
```json
{
    "success": true,
    "data": {
        "workout_id": "workout_12345",
        "status": "active",
        "elapsed_time": 1800,
        "current_metrics": {
            "power": 150,
            "heart_rate": 145,
            "cadence": 85,
            "speed": 22.5,
            "distance": 11.25,
            "calories": 245
        },
        "average_metrics": {
            "power": 142,
            "heart_rate": 138,
            "cadence": 82,
            "speed": 21.8
        },
        "peak_metrics": {
            "power": 180,
            "heart_rate": 155,
            "cadence": 95,
            "speed": 25.2
        },
        "workout_phase": "main",
        "connection_quality": "good",
        "data_points_count": 1800
    }
}
```

### End Workout

Complete and save a workout session.

**Endpoint**: `POST /api/workouts/{workout_id}/end`

**Parameters**:
- `workout_id` (string): Unique workout identifier

**Response**:
```json
{
    "success": true,
    "data": {
        "workout_id": "workout_12345",
        "end_time": "2025-01-12T11:00:00Z",
        "duration": 1800,
        "summary": {
            "total_distance": 15.5,
            "total_calories": 320,
            "average_power": 142,
            "max_power": 180,
            "average_heart_rate": 138,
            "max_heart_rate": 155,
            "training_load": 85
        },
        "status": "completed"
    }
}
```

### Pause/Resume Workout

Pause or resume an active workout.

**Endpoint**: `POST /api/workouts/{workout_id}/pause`
**Endpoint**: `POST /api/workouts/{workout_id}/resume`

**Response**:
```json
{
    "success": true,
    "data": {
        "workout_id": "workout_12345",
        "status": "paused",
        "pause_time": "2025-01-12T10:45:00Z"
    }
}
```

### Add Workout Marker

Add a marker/lap to the current workout.

**Endpoint**: `POST /api/workouts/{workout_id}/markers`

**Request Body**:
```json
{
    "marker_type": "lap",
    "note": "End of warm-up phase",
    "timestamp": "2025-01-12T10:35:00Z"
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "marker_id": "marker_001",
        "workout_id": "workout_12345",
        "marker_type": "lap",
        "timestamp": "2025-01-12T10:35:00Z",
        "elapsed_time": 300
    }
}
```

## Workout History API

### List Workouts

Get a list of all workouts with optional filtering.

**Endpoint**: `GET /api/workouts`

**Query Parameters**:
- `page` (integer): Page number (default: 1)
- `limit` (integer): Items per page (default: 20, max: 100)
- `device_type` (string): Filter by device type ("bike", "rower")
- `start_date` (string): Filter workouts after date (ISO 8601)
- `end_date` (string): Filter workouts before date (ISO 8601)
- `min_duration` (integer): Minimum duration in seconds
- `max_duration` (integer): Maximum duration in seconds
- `sort` (string): Sort field ("date", "duration", "distance", "calories")
- `order` (string): Sort order ("asc", "desc")

**Response**:
```json
{
    "success": true,
    "data": {
        "workouts": [
            {
                "id": "workout_12345",
                "device_type": "bike",
                "start_time": "2025-01-12T10:30:00Z",
                "end_time": "2025-01-12T11:00:00Z",
                "duration": 1800,
                "total_distance": 15.5,
                "total_calories": 320,
                "average_power": 142,
                "max_power": 180,
                "average_heart_rate": 138,
                "training_load": 85,
                "has_fit_file": true
            }
        ],
        "pagination": {
            "page": 1,
            "limit": 20,
            "total": 150,
            "pages": 8
        }
    }
}
```

### Get Workout Details

Get detailed information about a specific workout.

**Endpoint**: `GET /api/workouts/{workout_id}`

**Parameters**:
- `workout_id` (string): Unique workout identifier

**Response**:
```json
{
    "success": true,
    "data": {
        "id": "workout_12345",
        "device_type": "bike",
        "start_time": "2025-01-12T10:30:00Z",
        "end_time": "2025-01-12T11:00:00Z",
        "duration": 1800,
        "summary": {
            "total_distance": 15.5,
            "total_calories": 320,
            "average_power": 142,
            "max_power": 180,
            "average_heart_rate": 138,
            "max_heart_rate": 155,
            "training_load": 85
        },
        "phases": [
            {
                "phase": "warmup",
                "start_time": 0,
                "duration": 300,
                "average_power": 80
            },
            {
                "phase": "main",
                "start_time": 300,
                "duration": 1200,
                "average_power": 160
            },
            {
                "phase": "cooldown",
                "start_time": 1500,
                "duration": 300,
                "average_power": 90
            }
        ],
        "markers": [
            {
                "id": "marker_001",
                "type": "lap",
                "timestamp": "2025-01-12T10:35:00Z",
                "elapsed_time": 300,
                "note": "End of warm-up"
            }
        ],
        "data_quality": {
            "completeness": 0.99,
            "accuracy": 0.95,
            "missing_points": 18
        }
    }
}
```

### Get Workout Data Points

Get time-series data for a specific workout.

**Endpoint**: `GET /api/workouts/{workout_id}/data`

**Query Parameters**:
- `start_time` (integer): Start time offset in seconds
- `end_time` (integer): End time offset in seconds
- `interval` (integer): Data point interval in seconds (for decimation)
- `metrics` (string): Comma-separated list of metrics to include

**Response**:
```json
{
    "success": true,
    "data": {
        "workout_id": "workout_12345",
        "data_points": [
            {
                "timestamp": "2025-01-12T10:30:00Z",
                "elapsed_time": 0,
                "power": 0,
                "heart_rate": 95,
                "cadence": 0,
                "speed": 0,
                "distance": 0,
                "calories": 0
            },
            {
                "timestamp": "2025-01-12T10:30:01Z",
                "elapsed_time": 1,
                "power": 45,
                "heart_rate": 98,
                "cadence": 60,
                "speed": 12.5,
                "distance": 0.003,
                "calories": 1
            }
        ],
        "metrics_included": ["power", "heart_rate", "cadence", "speed", "distance", "calories"],
        "total_points": 1800,
        "decimation_factor": 1
    }
}
```

### Delete Workout

Delete a specific workout and all associated data.

**Endpoint**: `DELETE /api/workouts/{workout_id}`

**Parameters**:
- `workout_id` (string): Unique workout identifier

**Response**:
```json
{
    "success": true,
    "data": {
        "workout_id": "workout_12345",
        "deleted": true,
        "deletion_time": "2025-01-12T12:00:00Z"
    }
}
```

## FIT File API

### Generate FIT File

Generate a Garmin FIT file for a specific workout.

**Endpoint**: `POST /api/workouts/{workout_id}/fit`

**Parameters**:
- `workout_id` (string): Unique workout identifier

**Request Body**:
```json
{
    "device_settings": {
        "manufacturer": "Rogue Fitness",
        "product": "Echo Bike",
        "serial_number": "12345"
    },
    "processing_options": {
        "speed_smoothing": true,
        "power_smoothing": false,
        "include_training_load": true
    }
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "fit_file_id": "fit_12345",
        "workout_id": "workout_12345",
        "file_size": 45678,
        "generation_time": "2025-01-12T12:00:00Z",
        "download_url": "/api/workouts/workout_12345/fit/download",
        "validation": {
            "is_valid": true,
            "garmin_compatible": true,
            "training_load_included": true
        }
    }
}
```

### Download FIT File

Download the generated FIT file.

**Endpoint**: `GET /api/workouts/{workout_id}/fit/download`

**Parameters**:
- `workout_id` (string): Unique workout identifier

**Response**: Binary FIT file data with appropriate headers
```
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="workout_12345.fit"
```

### Validate FIT File

Validate a FIT file for Garmin Connect compatibility.

**Endpoint**: `POST /api/workouts/{workout_id}/fit/validate`

**Response**:
```json
{
    "success": true,
    "data": {
        "is_valid": true,
        "garmin_compatible": true,
        "validation_results": {
            "file_structure": "valid",
            "required_messages": "present",
            "data_ranges": "valid",
            "training_load": "calculated",
            "device_identification": "correct"
        },
        "warnings": [],
        "errors": []
    }
}
```

### Analyze FIT File

Get detailed analysis of a generated FIT file.

**Endpoint**: `GET /api/workouts/{workout_id}/fit/analyze`

**Response**:
```json
{
    "success": true,
    "data": {
        "file_info": {
            "size": 45678,
            "creation_time": "2025-01-12T12:00:00Z",
            "protocol_version": "2.0",
            "profile_version": "21.67"
        },
        "messages": {
            "file_id": 1,
            "activity": 1,
            "session": 1,
            "lap": 3,
            "record": 1800,
            "device_info": 1
        },
        "data_summary": {
            "duration": 1800,
            "distance": 15500,
            "calories": 320,
            "training_load": 85
        },
        "compatibility": {
            "garmin_connect": true,
            "strava": true,
            "training_peaks": true
        }
    }
}
```

## Settings API

### Get User Settings

Get current user settings and preferences.

**Endpoint**: `GET /api/settings`

**Response**:
```json
{
    "success": true,
    "data": {
        "user_profile": {
            "name": "John Doe",
            "age": 30,
            "weight_kg": 75,
            "height_cm": 180,
            "max_heart_rate": 190,
            "fitness_level": "intermediate"
        },
        "unit_preferences": {
            "distance": "metric",
            "weight": "metric",
            "temperature": "celsius"
        },
        "workout_preferences": {
            "auto_start": true,
            "auto_pause": true,
            "recording_interval": 1,
            "power_smoothing": true
        },
        "system_settings": {
            "connection_timeout": 30,
            "reconnection_attempts": 3,
            "data_retention_days": 365
        }
    }
}
```

### Update User Settings

Update user settings and preferences.

**Endpoint**: `PUT /api/settings`

**Request Body**:
```json
{
    "user_profile": {
        "weight_kg": 76,
        "max_heart_rate": 188
    },
    "workout_preferences": {
        "auto_start": false,
        "power_smoothing": false
    }
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "updated": true,
        "update_time": "2025-01-12T12:00:00Z",
        "changes": [
            "user_profile.weight_kg",
            "user_profile.max_heart_rate",
            "workout_preferences.auto_start",
            "workout_preferences.power_smoothing"
        ]
    }
}
```

### Export Settings

Export all settings for backup purposes.

**Endpoint**: `GET /api/settings/export`

**Response**:
```json
{
    "success": true,
    "data": {
        "export_time": "2025-01-12T12:00:00Z",
        "version": "1.0",
        "settings": {
            // Complete settings object
        }
    }
}
```

### Import Settings

Import settings from backup.

**Endpoint**: `POST /api/settings/import`

**Request Body**:
```json
{
    "settings": {
        // Complete settings object from export
    },
    "merge_strategy": "overwrite"
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "imported": true,
        "import_time": "2025-01-12T12:00:00Z",
        "changes_count": 15
    }
}
```

## System API

### Get System Status

Get current system status and health information.

**Endpoint**: `GET /api/system/status`

**Response**:
```json
{
    "success": true,
    "data": {
        "application": {
            "version": "1.0.0",
            "uptime": 86400,
            "status": "healthy"
        },
        "database": {
            "status": "connected",
            "size_mb": 125,
            "workout_count": 150,
            "last_backup": "2025-01-11T12:00:00Z"
        },
        "bluetooth": {
            "adapter_present": true,
            "adapter_enabled": true,
            "connected_devices": 1
        },
        "performance": {
            "memory_usage_mb": 45,
            "cpu_usage_percent": 12,
            "disk_usage_percent": 35
        }
    }
}
```

### Get System Information

Get detailed system information.

**Endpoint**: `GET /api/system/info`

**Response**:
```json
{
    "success": true,
    "data": {
        "system": {
            "os": "Windows 10",
            "python_version": "3.12.0",
            "architecture": "x86_64"
        },
        "application": {
            "version": "1.0.0",
            "build_date": "2025-01-01T00:00:00Z",
            "git_commit": "abc123def456"
        },
        "dependencies": {
            "flask": "2.3.0",
            "pyftms": "1.0.0",
            "bleak": "0.20.0"
        },
        "bluetooth": {
            "adapter_name": "Intel Wireless Bluetooth",
            "adapter_version": "5.0",
            "driver_version": "22.120.0"
        }
    }
}
```

### Run System Diagnostics

Run comprehensive system diagnostics.

**Endpoint**: `POST /api/system/diagnostics`

**Response**:
```json
{
    "success": true,
    "data": {
        "overall_status": "healthy",
        "diagnostics": {
            "database": {
                "status": "ok",
                "connection_test": "passed",
                "integrity_check": "passed"
            },
            "bluetooth": {
                "status": "ok",
                "adapter_test": "passed",
                "scan_test": "passed"
            },
            "file_system": {
                "status": "ok",
                "permissions": "correct",
                "disk_space": "sufficient"
            },
            "network": {
                "status": "ok",
                "web_server": "running",
                "port_availability": "ok"
            }
        },
        "recommendations": [
            "System is operating normally",
            "No issues detected"
        ]
    }
}
```

## WebSocket API

### Real-time Workout Data

Connect to receive real-time workout data updates.

**Endpoint**: `ws://localhost:5000/ws/workout/{workout_id}`

**Connection Parameters**:
- `workout_id` (string): Active workout identifier

**Message Types**:

**Data Update Message**:
```json
{
    "type": "data_update",
    "timestamp": "2025-01-12T10:30:15Z",
    "workout_id": "workout_12345",
    "data": {
        "elapsed_time": 15,
        "power": 145,
        "heart_rate": 142,
        "cadence": 85,
        "speed": 22.1,
        "distance": 0.092,
        "calories": 3
    }
}
```

**Status Update Message**:
```json
{
    "type": "status_update",
    "timestamp": "2025-01-12T10:30:15Z",
    "workout_id": "workout_12345",
    "status": "active",
    "connection_quality": "good"
}
```

**Phase Change Message**:
```json
{
    "type": "phase_change",
    "timestamp": "2025-01-12T10:35:00Z",
    "workout_id": "workout_12345",
    "previous_phase": "warmup",
    "current_phase": "main"
}
```

### Device Status Updates

Connect to receive real-time device status updates.

**Endpoint**: `ws://localhost:5000/ws/devices`

**Message Types**:

**Connection Status Message**:
```json
{
    "type": "connection_status",
    "timestamp": "2025-01-12T10:30:00Z",
    "device_id": "device_001",
    "status": "connected",
    "signal_strength": "good"
}
```

**Device Discovery Message**:
```json
{
    "type": "device_discovered",
    "timestamp": "2025-01-12T10:30:00Z",
    "device": {
        "id": "device_002",
        "name": "Rogue Echo Rower",
        "type": "rower",
        "rssi": -38
    }
}
```

## Error Codes

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `DEVICE_NOT_FOUND` | Specified device not found | 404 |
| `DEVICE_NOT_CONNECTED` | Device is not connected | 400 |
| `CONNECTION_FAILED` | Failed to establish device connection | 500 |
| `WORKOUT_NOT_FOUND` | Specified workout not found | 404 |
| `WORKOUT_NOT_ACTIVE` | Workout is not currently active | 400 |
| `INVALID_PARAMETERS` | Invalid request parameters | 400 |
| `BLUETOOTH_UNAVAILABLE` | Bluetooth adapter not available | 503 |
| `DATABASE_ERROR` | Database operation failed | 500 |
| `FIT_GENERATION_FAILED` | FIT file generation failed | 500 |
| `VALIDATION_ERROR` | Data validation failed | 400 |

### Error Response Examples

**Device Not Found**:
```json
{
    "success": false,
    "error": {
        "code": "DEVICE_NOT_FOUND",
        "message": "Device with ID 'device_001' not found",
        "details": {
            "device_id": "device_001",
            "available_devices": ["device_002", "device_003"]
        }
    }
}
```

**Connection Failed**:
```json
{
    "success": false,
    "error": {
        "code": "CONNECTION_FAILED",
        "message": "Failed to connect to device",
        "details": {
            "device_id": "device_001",
            "reason": "Device not in pairing mode",
            "suggestions": [
                "Ensure device is powered on",
                "Put device in pairing mode",
                "Check Bluetooth is enabled"
            ]
        }
    }
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **General API**: 100 requests per minute per IP
- **Real-time Data**: 10 requests per second per workout
- **File Downloads**: 10 downloads per minute per IP

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1641988800
```

## SDK and Client Libraries

### Python SDK Example

```python
from rogue_garmin_bridge_sdk import RogueGarminBridgeClient

# Initialize client
client = RogueGarminBridgeClient(base_url="http://localhost:5000")

# Discover devices
devices = client.devices.discover()

# Connect to device
client.devices.connect(devices[0].id)

# Start workout
workout = client.workouts.start(device_id=devices[0].id)

# Get live data
live_data = client.workouts.get_live_data(workout.id)

# End workout
summary = client.workouts.end(workout.id)

# Generate FIT file
fit_file = client.workouts.generate_fit(workout.id)
```

### JavaScript SDK Example

```javascript
import { RogueGarminBridgeClient } from 'rogue-garmin-bridge-sdk';

// Initialize client
const client = new RogueGarminBridgeClient('http://localhost:5000');

// Discover devices
const devices = await client.devices.discover();

// Connect to device
await client.devices.connect(devices[0].id);

// Start workout
const workout = await client.workouts.start({
    deviceId: devices[0].id,
    deviceType: 'bike'
});

// Subscribe to real-time data
client.workouts.subscribeToLiveData(workout.id, (data) => {
    console.log('Live data:', data);
});

// End workout
const summary = await client.workouts.end(workout.id);
```

This API reference provides comprehensive documentation for integrating with the Rogue Garmin Bridge application programmatically.