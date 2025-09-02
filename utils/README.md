# IoT Sensor Management Utilities - Production Grade

This package provides a comprehensive set of production-grade utilities for managing IoT sensors and devices. Each utility is designed with enterprise-level features including comprehensive logging, error handling, performance monitoring, and detailed reporting.

## 🚀 Features

### Core Utilities

- **Sensor Manager** - Centralized coordination of all sensors and utilities
- **Diagnostics Utilities** - Comprehensive network, system, and sensor diagnostics
- **Configuration Manager** - Centralized configuration with environment variable support
- **Logger Factory** - Production-grade logging with rotation and structured output
- **Camera Utilities** - Camera sensor testing, image capture, performance analysis
- **LiDAR Utilities** - Point cloud processing, occupancy detection, obstacle analysis
- **Environment Utilities** - Temperature, humidity, pressure monitoring with alerting
- **System Utilities** - Health monitoring, resource usage, temperature tracking
- **Network Utilities** - Connectivity testing, MQTT operations, HTTP API testing
- **Media Utilities** - File management, S3 operations, automated cleanup

### Production Features

- **Device-Specific Logging** - Separate log files per sensor with rotation and structured JSON output
- **Comprehensive Error Handling** - Graceful failure handling with detailed logging and recovery
- **Performance Monitoring** - Real-time metrics, timing, and performance analysis
- **Health Checks** - Automated system and sensor health monitoring with alerting
- **Report Generation** - Detailed JSON reports for all operations with export capabilities
- **Concurrent Operations** - Thread-safe operations with parallel processing
- **Configuration Management** - Centralized configuration with YAML/JSON/INI support and hot-reloading
- **Continuous Monitoring** - Background health monitoring with trend analysis
- **Automated Diagnostics** - Comprehensive diagnostics with recommendations

## 📁 Package Structure

```
utils/
├── __init__.py                 # Package initialization and exports
├── README.md                   # This documentation
├── config_manager.py           # Configuration management with multiple format support
├── logger_factory.py           # Production-grade logging factory
├── sensor_manager.py           # Main sensor coordination and management
├── diagnostics_utils.py        # Comprehensive diagnostics utilities
├── camera_utils.py             # Camera sensor utilities
├── lidar_utils.py              # LiDAR sensor utilities
├── environment_utils.py        # Environment sensor utilities
├── system_utils.py             # System monitoring utilities
├── network_utils.py            # Network and connectivity utilities
└── media_utils.py              # Media file management utilities
```

## 🚀 Quick Start

### Basic Usage

```python
from utils import SensorManager, ConfigManager

# Initialize with configuration
config_manager = ConfigManager("config.yaml")
sensor_manager = SensorManager()

# Register sensors (example with your existing network diagnostics)
from network_diagnostics import NetworkDiagnostics
network_sensor = NetworkDiagnostics(device_id="your_device_id")
sensor_manager.register_sensor("network", network_sensor)

# Run comprehensive diagnostics
results = sensor_manager.run_comprehensive_diagnostics({
    "include_network": True,
    "include_system": True,
    "network_params": {
        "tests": ["ping", "dns", "traceroute", "speed_test"],
        "target_host": "thingsboard.server.com",
        "duration_seconds": 30
    }
})

# Start health monitoring
sensor_manager.start_health_monitoring(interval_seconds=300)

# Generate master report
report = sensor_manager.create_master_report()
report_path = sensor_manager.export_report(report)
```

### Configuration Management

```python
from utils import ConfigManager

# Load configuration from YAML/JSON/INI
config = ConfigManager("config.yaml")

# Access configuration values
network_config = config.get_network_config()
sensor_config = config.get_sensor_config()

# Set values programmatically
config.set("sensors", "timeout_seconds", 45)
config.save_config()

# Environment variable overrides
# IOT_DEVICE_ID=device123 python your_script.py
```

### Advanced Logging

```python
from utils import LoggerFactory, ConfigManager

config = ConfigManager()
logger_factory = LoggerFactory(config)

# Get specialized loggers
sensor_logger = logger_factory.get_sensor_logger("camera")
performance_logger = logger_factory.get_performance_logger("diagnostics")
audit_logger = logger_factory.get_audit_logger()

# Performance timing
performance_logger.start_timer("sensor_test")
# ... perform operations ...
duration = performance_logger.end_timer("sensor_test")

# Structured logging with extra data
logger_factory.log_system_event("sensor_failure", "Camera sensor disconnected", {
    "sensor_id": "cam_001",
    "error_code": "CONN_LOST",
    "retry_count": 3
})
```

### Comprehensive Diagnostics

```python
from utils import DiagnosticsUtils, ConfigManager, LoggerFactory

config = ConfigManager()
logger_factory = LoggerFactory(config)
diagnostics = DiagnosticsUtils(config, logger_factory)

# Run full diagnostics
results = diagnostics.run_comprehensive_diagnostics({
    "include_network": True,
    "include_system": True,
    "network_params": {
        "tests": ["ping", "traceroute", "dns", "speed_test", "port_scan"],
        "target_host": "your.server.com",
        "duration_seconds": 60,
        "ports": [22, 80, 443, 1883, 8080]
    }
})

# Export detailed report
report_path = diagnostics.export_diagnostics_report(results, "json")
```

## 🔧 Configuration

### Configuration File Format (config.yaml)

```yaml
system:
  device_id: "PSM100-001"
  device_name: "Parking Sensor 001"
  environment: "production"
  debug_mode: false
  location:
    latitude: 40.7128
    longitude: -74.0060

sensors:
  enabled: true
  timeout_seconds: 30
  retry_attempts: 3
  sampling_rate_hz: 1.0
  health_check_interval: 300

network:
  connection_timeout: 10
  read_timeout: 30
  max_retries: 3
  mqtt_keepalive: 60
  thingsboard_url: "https://your-thingsboard.com"
  jwt_token: "your_jwt_token"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  max_file_size: "10MB"
  backup_count: 5
  log_directory: "./logs"
```

### Environment Variables

```bash
# System configuration
export IOT_DEVICE_ID="PSM100-001"
export IOT_DEVICE_NAME="Parking Sensor 001"
export IOT_ENVIRONMENT="production"
export IOT_DEBUG_MODE="false"

# Network configuration
export THINGSBOARD_URL="https://your-thingsboard.com"
export JWT_TOKEN="your_jwt_token"

# Logging configuration
export IOT_LOG_LEVEL="INFO"
export IOT_LOG_DIR="./logs"
```

## 📊 Monitoring and Health Checks

### Health Monitoring

```python
# Start continuous health monitoring
sensor_manager.start_health_monitoring(interval_seconds=300)

# Add custom alert callbacks
def alert_handler(alert):
    print(f"ALERT: {alert['type']} - {alert['message']}")
    # Send to monitoring system, email, etc.

sensor_manager.health_monitor.add_alert_callback(alert_handler)

# Get health trends
trends = sensor_manager.get_health_trends(hours=24)
print(f"Overall health trend: {trends['overall_health_trend']}")
```

### Performance Monitoring

```python
# Get operational statistics
stats = sensor_manager.get_operation_statistics()
print(f"Success rate: {stats['operation_stats']['successful_operations']} / {stats['operation_stats']['total_operations']}")

# Get log statistics
log_stats = logger_factory.get_log_statistics()
print(f"Total log size: {log_stats['total_log_size_mb']} MB")
```

## 🔌 Integration with Existing Code

### Integrating Network Diagnostics

```python
# Update your existing api.py
from utils import SensorManager, DiagnosticsUtils

# Initialize in your main application
sensor_manager = SensorManager("config.yaml")

# In your RPC handler for diagnostics.network
elif method == "diagnostics.network":
    # Use the production-grade diagnostics
    results = sensor_manager.run_comprehensive_diagnostics({
        "include_network": True,
        "include_system": False,
        "network_params": params
    })
    
    response = results["network_diagnostics"]
```

### Migrating Existing Sensors

```python
# Wrap your existing sensor classes
class LegacySensorWrapper:
    def __init__(self, legacy_sensor):
        self.sensor = legacy_sensor
    
    def collect_data(self):
        try:
            data = self.sensor.get_data()  # Your existing method
            return {"success": True, "data": data, "data_points": len(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_health(self):
        try:
            status = self.sensor.status()  # Your existing method
            return {"healthy": status == "ok", "status": status}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

# Register with sensor manager
legacy_sensor = YourExistingSensor()
wrapped_sensor = LegacySensorWrapper(legacy_sensor)
sensor_manager.register_sensor("legacy_sensor", wrapped_sensor)
```

## 📈 Performance Optimization

### Best Practices

1. **Parallel Operations**: Use the built-in parallel processing for sensor operations
2. **Caching**: Implement caching for frequently accessed configuration values
3. **Resource Management**: Monitor resource usage and set appropriate timeouts
4. **Log Management**: Configure appropriate log rotation and cleanup policies
5. **Health Monitoring**: Use reasonable intervals to balance monitoring and performance

### Resource Usage Guidelines

```python
# Configure for your environment
config = {
    "sensors": {
        "timeout_seconds": 30,      # Adjust based on sensor response times
        "retry_attempts": 3,        # Balance reliability vs. speed
        "health_check_interval": 300 # 5 minutes for production
    },
    "logging": {
        "max_file_size": "10MB",    # Adjust based on disk space
        "backup_count": 5           # Keep reasonable history
    }
}
```

## 🛠 Troubleshooting

### Common Issues

**Configuration not loading:**
```bash
# Check file permissions and format
ls -la config.yaml
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

**Logging issues:**
```python
# Check log directory permissions
import os
log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)
print(f"Log directory writable: {os.access(log_dir, os.W_OK)}")
```

**Sensor registration failures:**
```python
# Verify sensor interface
sensor = YourSensor()
required_methods = ['collect_data', 'check_health']
for method in required_methods:
    print(f"{method}: {hasattr(sensor, method)}")
```

### Debug Mode

```python
# Enable debug mode for detailed logging
config_manager.set("system", "debug_mode", True)
config_manager.set("logging", "level", "DEBUG")
```

## 📚 API Reference

### SensorManager

- `register_sensor(name, instance, config)` - Register a sensor
- `test_all_sensors()` - Test all registered sensors
- `check_all_sensors_health()` - Check health of all sensors
- `run_comprehensive_diagnostics(params)` - Run full diagnostics
- `start_health_monitoring(interval)` - Start continuous monitoring
- `create_master_report()` - Generate comprehensive report

### ConfigManager

- `get(section, key, default)` - Get configuration value
- `set(section, key, value)` - Set configuration value
- `get_sensor_config()` - Get sensor configuration
- `get_network_config()` - Get network configuration
- `save_config()` - Save configuration to file
- `reload_config()` - Reload from file

### LoggerFactory

- `get_logger(name, sensor_type)` - Get standard logger
- `get_sensor_logger(sensor_name)` - Get sensor-specific logger
- `get_performance_logger(name)` - Get performance logger
- `log_system_event(type, message, data)` - Log system events

## 🤝 Contributing

1. Follow the existing code style and patterns
2. Add comprehensive logging to all operations
3. Include error handling for all external operations
4. Write tests for new functionality
5. Update documentation for new features

## 📄 License

This project is part of the IoT Sensor Management System. See the main project license for details.

---

**Production-Ready IoT Sensor Management Utilities** - Built for enterprise-grade reliability and performance.