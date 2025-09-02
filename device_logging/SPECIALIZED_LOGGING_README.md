# Specialized Telemetry Logging System

This document describes the new specialized telemetry logging system that provides different types of logging for different sensor components, with particular focus on LiDAR telemetry that shows exactly what data is being sent.

## Overview

The specialized logging system consists of three main components:

1. **Enhanced Device Logger** - General purpose logging for all sensors
2. **LiDAR Telemetry Logger** - Specialized logging for LiDAR operations
3. **Camera Telemetry Logger** - Specialized logging for camera operations

## Features

### 🔍 LiDAR Telemetry Logger

- **Session-based logging** with unique scan IDs
- **Detailed telemetry data** showing exactly what LiDAR data is being sent
- **Performance tracking** including scan times, point counts, and efficiency metrics
- **Structured data logging** with metadata for each scan
- **Error tracking** with context and detailed error information
- **Organized log files** in dedicated directories:
  - `data/logs/lidar/scans/` - Individual scan logs
  - `data/logs/lidar/telemetry/` - Telemetry data logs
  - `data/logs/lidar/errors/` - Error logs
  - `data/logs/lidar/performance/` - Performance metrics

#### What LiDAR Data is Logged

The LiDAR telemetry logger captures and logs:

- **Scan Parameters**: Resolution, scan rate, range filters
- **Telemetry Data**: Point counts, scan duration, occupancy detection
- **Range Information**: Min/max range values
- **Performance Metrics**: Scan efficiency, points per second
- **Sensor Status**: Active/inactive, error states
- **Data Format**: Point cloud format, compression ratios

#### Example LiDAR Log Entry

```
2024-01-15 14:30:25 | LIDAR[SCAN:telemetry_1705327825] | INFO | log_telemetry_data:123 | LiDAR telemetry data captured | Data: {
  "data_type": "telemetry",
  "telemetry_data": {
    "points_count": 3600,
    "scan_time_ms": 100.5,
    "occupancy_detected": true,
    "range_min": 0.15,
    "range_max": 95.8,
    "resolution_deg": 0.1,
    "scan_rate_hz": 10.0,
    "sensor_status": "normal",
    "data_format": "telemetry_summary"
  },
  "session_stats": {
    "points_collected": 3600,
    "scan_duration_ms": 100.5,
    "session_duration": 5
  }
}
```

### 📷 Camera Telemetry Logger

- **Capture session tracking** with unique capture IDs
- **Frame-by-frame logging** for detailed camera operations
- **Camera parameters** including resolution, frame rate, exposure settings
- **Motion and occupancy detection** logging
- **Image quality metrics** and focus information

### 🔧 Enhanced Device Logger

- **General sensor logging** for all device components
- **Session management** with automatic cleanup
- **Structured data logging** with JSON support
- **Performance monitoring** across all sensors

## Usage

### Basic Setup

```python
from device_logging import (
    setup_enhanced_device_logging,
    setup_lidar_telemetry_logging,
    setup_camera_telemetry_logging
)

# Initialize loggers
device_logger = setup_enhanced_device_logging("my_device")
lidar_logger = setup_lidar_telemetry_logging("my_device")
camera_logger = setup_camera_telemetry_logging("my_device")
```

### LiDAR Telemetry Logging

```python
# Start a scan session
scan_id = "scan_001"
scan_params = {
    "resolution": 0.1,
    "scan_rate_hz": 10.0,
    "range_filter": {"min": 0.1, "max": 100.0}
}

scan_logger = lidar_logger.start_scan_session(scan_id, scan_params)

# Log telemetry data
telemetry_data = {
    "points_count": 3600,
    "scan_time_ms": 100.5,
    "occupancy_detected": True,
    "range_min": 0.15,
    "range_max": 95.8,
    "resolution_deg": 0.1,
    "scan_rate_hz": 10.0,
    "sensor_status": "normal",
    "data_format": "pointcloud"
}

lidar_logger.log_telemetry_data(scan_id, telemetry_data, "scan")

# Log scan summary
summary_data = {
    "quality_score": 0.95,
    "compression_ratio": 0.8,
    "scan_completion": 100.0
}
lidar_logger.log_scan_summary(scan_id, summary_data)

# End scan session
lidar_logger.end_scan_session(scan_id)
```

### Camera Telemetry Logging

```python
# Start a capture session
capture_id = "capture_001"
capture_params = {
    "resolution": "1920x1080",
    "frame_rate": 30.0,
    "exposure_time_ms": 16.67,
    "iso": 100
}

capture_logger = camera_logger.start_capture_session(capture_id, capture_params)

# Log capture data
capture_data = {
    "resolution": "1920x1080",
    "frame_rate": 30.0,
    "exposure_time_ms": 16.67,
    "iso": 100,
    "focus_distance": 2.5,
    "motion_detected": True,
    "occupancy_detected": False,
    "light_level": 128,
    "focus_quality": 0.95,
    "image_format": "JPEG",
    "capture_time_ms": 33.33
}

camera_logger.log_capture_data(capture_id, capture_data, "frame")

# End capture session
camera_logger.end_capture_session(capture_id)
```

### Error Logging

```python
try:
    # Some LiDAR operation
    lidar_data = collect_lidar_data()
except Exception as e:
    # Log error with context
    lidar_logger.log_lidar_error(scan_id, e, "data_collection", {
        "operation": "collect_lidar_data",
        "timestamp": time.time()
    })
```

## Log File Structure

```
data/logs/
├── lidar/
│   ├── lidar_main.log              # Main LiDAR logger
│   ├── scans/                      # Individual scan logs
│   │   ├── scan_001_1705327800_1705327825.log
│   │   └── scan_002_1705327830_1705327855.log
│   ├── telemetry/                  # Telemetry data logs
│   ├── errors/                     # Error logs
│   └── performance/                # Performance metrics
├── camera/
│   ├── camera_main.log             # Main camera logger
│   ├── captures/                   # Individual capture logs
│   ├── streaming/                  # Streaming logs
│   └── errors/                     # Error logs
└── device_logs/                    # Enhanced device logs
    ├── main_1705327800_1705327900.log
    ├── lidar_1705327800_1705327850.log
    └── camera_1705327800_1705327880.log
```

## Performance Monitoring

### LiDAR Performance Metrics

- Total scans performed
- Total points collected
- Average scan time
- Points per second efficiency
- Error count and types
- Active scan sessions

### Camera Performance Metrics

- Total captures performed
- Total frames captured
- Average capture time
- Active capture sessions
- Error count and types

## Integration with API

The specialized logging system is fully integrated with the main API (`core/api.py`):

- **Telemetry Simulation**: Automatically logs all LiDAR and camera telemetry data
- **RPC Methods**: Logs LiDAR control operations with detailed context
- **Sensor Capture**: Tracks comprehensive sensor data collection
- **Error Handling**: Captures and logs all sensor errors

## Testing

Run the test script to verify the logging system:

```bash
python3 test_specialized_logging.py
```

This will:
1. Test LiDAR telemetry logging with multiple scan sessions
2. Test camera telemetry logging with multiple capture sessions
3. Test enhanced device logging across all sensors
4. Generate sample log files in the appropriate directories

## Benefits

1. **Visibility**: See exactly what LiDAR data is being sent
2. **Debugging**: Detailed error tracking with context
3. **Performance**: Monitor sensor efficiency and performance
4. **Organization**: Structured log files for easy analysis
5. **Integration**: Seamless integration with existing systems
6. **Scalability**: Session-based logging for multiple concurrent operations

## Configuration

The logging system automatically creates necessary directories and files. Log levels and formats can be customized by modifying the logger classes.

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure write access to `data/logs/` directory
2. **Missing Dependencies**: Verify all required Python packages are installed
3. **Log File Corruption**: Check disk space and file permissions

### Debug Mode

Enable debug logging by setting log levels to DEBUG in the logger classes.

## Future Enhancements

- **Real-time log streaming** to external systems
- **Log compression** and archival
- **Advanced analytics** and reporting
- **Integration** with monitoring dashboards
- **Custom log formats** for different use cases


