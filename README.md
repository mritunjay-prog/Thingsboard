# IoT Sensor Management System - Production Grade

A comprehensive, production-ready IoT sensor management system with advanced logging, diagnostics, and monitoring capabilities.

## 🏗️ Project Structure

```
iot-sensor-system/
├── core/                   # Main application and API files
├── sensors/                # Sensor modules and utilities
├── device_logging/                # Logging and diagnostics
├── services/               # Services for media processing and file management
├── utils/                  # Production-grade utilities package
├── examples/               # Integration examples and demos
├── tests/                  # Testing utilities
├── config/                 # Configuration files
├── docs/                   # Documentation
├── device_logs/            # Generated log files
└── media_files/            # Generated media files
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r docs/requirements.txt
```

### 2. Configure the System
```bash
# Copy and edit configuration
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml with your settings
```

### 3. Start the API Service

**Recommended approach:**
```bash
# Start with automatic device provisioning
python run_api.py

# Force re-provision device if needed
python run_api.py --force-provision

# Skip provisioning (use existing device info)
python run_api.py --skip-provision
```

**Simple approach:**
```bash
# Minimal startup (handles provisioning automatically)
python start_api.py
```

**Direct approach:**
```bash
# Run core API directly (handles its own provisioning)
python core/api.py
```

### 4. Test Network Diagnostics
```bash
python tests/quick_test.py
```

## 📁 Module Overview

### Core (`core/`)
- **api.py** - Main MQTT API service with RPC handlers
- **APIProvision.py** - Device provisioning and ThingsBoard integration
- **get_jwt_token.py** - JWT token management for ThingsBoard

### Sensors (`sensors/`)
- **lidar_collector.py** - LiDAR sensor data collection
- **adhoc_pointcloud_capture.py** - On-demand point cloud capture
- **camera_command_sender.py** - Camera control and commands
- **video_capture_service.py** - Video recording functionality
- **video_streaming_service.py** - Live video streaming

### Logging (`device_logging/`)
- **enhanced_device_logger.py** - Enhanced device logging (legacy)
- **streaming_logger.py** - Streaming session logging (legacy)
- **network_diagnostics.py** - Network diagnostics and testing

### Services (`services/`)
- **media_upload_service.py** - S3 upload and media management

### Utils (`utils/`)
- **unified_logger.py** - Production-grade unified logging system
- **config_manager.py** - Configuration management
- **sensor_manager.py** - Centralized sensor coordination
- **diagnostics_utils.py** - Comprehensive diagnostics

### Examples (`examples/`)
- **production_api_integration.py** - Production API integration example
- **unified_logging_integration.py** - Unified logging usage example

### Tests (`tests/`)
- **quick_test.py** - Quick functionality tests
- **test_network_diagnostics.py** - Network diagnostics testing

## 🔧 Configuration

The system uses YAML configuration files located in `config/`:

- **config.yaml** - Main system configuration
- **config.properties** - Legacy configuration (for backward compatibility)

## 📊 Monitoring and Logging

The system provides comprehensive logging and monitoring:

- **Device Logs** - Stored in `device_logs/`
- **Media Files** - Stored in `media_files/`
- **Unified Logging** - Production-grade logging with rotation
- **Performance Metrics** - Built-in performance tracking
- **Health Monitoring** - Continuous system health checks

## 🔌 API Integration

The system integrates with ThingsBoard via MQTT and supports RPC commands:

- `diagnostics.network` - Network diagnostics
- `sensors.capture.all` - Comprehensive sensor data collection
- `camera.video.capture` - Video recording
- `storage.retrieve` - Data retrieval and S3 upload

## 🛠️ Development

### Adding New Sensors
1. Create sensor module in `sensors/`
2. Register with `utils/sensor_manager.py`
3. Add configuration to `config/config.yaml`

### Adding New Diagnostics
1. Extend `utils/diagnostics_utils.py`
2. Add RPC handler in `core/api.py`
3. Update documentation

## 📚 Documentation

- Each module folder contains its own README
- API documentation in docstrings
- Configuration examples in `config/`
- Integration examples in `examples/`

## 🤝 Contributing

1. Follow the existing folder structure
2. Add comprehensive logging
3. Include error handling
4. Update documentation
5. Add tests for new functionality

## 📄 License

This project is part of the IoT Sensor Management System.

---

**Production-Ready IoT Sensor Management** - Built for enterprise-grade reliability and performance.
