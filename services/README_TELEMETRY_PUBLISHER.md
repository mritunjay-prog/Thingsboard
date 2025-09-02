# Telemetry Publisher Service

## Overview

The **Telemetry Publisher Service** is a centralized service that consolidates all telemetry publishing functions from `core/api.py` into a single, organized service located in the `@services/` folder. This service provides a clean, maintainable way to publish telemetry data to ThingsBoard MQTT.

## 🎯 **Purpose**

- **Centralize** all telemetry publishing logic in one location
- **Simplify** the main API file (`core/api.py`)
- **Improve** code organization and maintainability
- **Provide** consistent error handling and logging
- **Enable** easy testing and debugging of telemetry publishing

## 📁 **File Structure**

```
services/
├── telemetry_publisher.py          # Main telemetry publisher service
└── README_TELEMETRY_PUBLISHER.md  # This documentation

core/
├── api.py                          # Updated to use telemetry publisher service
└── ...                            # Other core files
```

## 🔧 **Integration Changes**

### **Before (Old API Structure)**
```python
# core/api.py - Multiple publish functions scattered throughout
def publish_lidar_telemetry(telemetry_data):
    # LiDAR publishing logic
    
def publish_occupancy_telemetry(occupancy_data):
    # Occupancy publishing logic
    
def publish_proximity_alert_telemetry(proximity_data):
    # Proximity alert publishing logic
    
def publish_environmental_telemetry(telemetry_data, sensor_type):
    # Environmental publishing logic
    
def publish_telemetry(telemetry_data):
    # General telemetry publishing logic
```

### **After (New Centralized Structure)**
```python
# core/api.py - Clean imports
from services.telemetry_publisher import (
    get_telemetry_publisher,
    publish_lidar_telemetry,
    publish_occupancy_telemetry,
    publish_proximity_alert_telemetry,
    publish_environmental_telemetry,
    publish_telemetry
)

# Initialize service with MQTT client
telemetry_publisher = get_telemetry_publisher(client)
```

## 🚀 **Features**

### **1. Centralized Publishing**
- All telemetry publishing functions in one service
- Consistent MQTT topic handling
- Unified error handling and logging

### **2. MQTT Client Management**
- Automatic MQTT client detection
- Client availability checking
- Graceful fallback when client unavailable

### **3. Comprehensive Logging**
- Detailed success/failure logging
- Telemetry data extraction and display
- Error tracking and reporting

### **4. Status Monitoring**
- Publish count tracking
- Error count tracking
- Success rate calculation
- Service health monitoring

## 📡 **Available Publishing Functions**

### **1. `publish_lidar_telemetry(telemetry_data)`**
- **Purpose**: Publish LiDAR telemetry data
- **Input**: LiDAR telemetry data in ThingsBoard format
- **Output**: Boolean success status
- **Logging**: Success/failure with telemetry details

### **2. `publish_occupancy_telemetry(occupancy_data)`**
- **Purpose**: Publish LiDAR occupancy detection data
- **Input**: Occupancy telemetry data
- **Output**: Boolean success status
- **Logging**: Occupancy detection details (object dimensions, distance)

### **3. `publish_proximity_alert_telemetry(proximity_data)`**
- **Purpose**: Publish ultrasonic proximity alert data
- **Input**: Proximity alert telemetry data
- **Output**: Boolean success status
- **Logging**: Proximity alert details (sensor ID, distance, threshold)

### **4. `publish_environmental_telemetry(telemetry_data, sensor_type)`**
- **Purpose**: Publish environmental sensor data
- **Input**: Environmental telemetry data + sensor type
- **Output**: Boolean success status
- **Logging**: Sensor-specific details (temperature, humidity, air quality, light levels)
- **Sensor Types**: `environment`, `air_quality`, `light_level`

### **5. `publish_telemetry(telemetry_data)`**
- **Purpose**: Publish general telemetry data
- **Input**: General telemetry data
- **Output**: Boolean success status
- **Logging**: Telemetry metrics count and ultrasonic file saving
- **Special Features**: Automatic ultrasonic telemetry file saving

## 🔄 **Usage Examples**

### **Basic Usage**
```python
from services.telemetry_publisher import publish_lidar_telemetry

# Publish LiDAR data
telemetry_data = {
    "ts": int(time.time() * 1000),
    "values": {
        "lidar.point_count": 360,
        "lidar.scan_rate_hz": 10.0
    }
}

success = publish_lidar_telemetry(telemetry_data)
if success:
    print("✅ LiDAR telemetry published successfully")
else:
    print("❌ LiDAR telemetry publishing failed")
```

### **Service Instance Usage**
```python
from services.telemetry_publisher import get_telemetry_publisher

# Get publisher instance
publisher = get_telemetry_publisher(mqtt_client)

# Publish using instance methods
success = publisher.publish_lidar_telemetry(telemetry_data)
success = publisher.publish_environmental_telemetry(env_data, "environment")

# Check service status
status = publisher.get_status()
print(f"Publish count: {status['publish_count']}")
print(f"Success rate: {status['success_rate']:.2%}")
```

### **Environmental Sensor Integration**
```python
from services.telemetry_publisher import publish_environmental_telemetry

# Environment conditions
env_data = {
    "ts": int(time.time() * 1000),
    "values": {
        "environment.temperature_c": 25.5,
        "environment.humidity_percent": 65.0,
        "environment.pressure_hpa": 1013.25
    }
}
publish_environmental_telemetry(env_data, "environment")

# Air quality
air_data = {
    "ts": int(time.time() * 1000),
    "values": {
        "air_quality.pm2_5_ugm3": 15.2,
        "air_quality.aqi": 52,
        "air_quality.aqi_category": "moderate"
    }
}
publish_environmental_telemetry(air_data, "air_quality")

# Light levels
light_data = {
    "ts": int(time.time() * 1000),
    "values": {
        "light.ambient_lux": 920.8,
        "light.uv_index": 4.1,
        "light.day_night_state": "day"
    }
}
publish_environmental_telemetry(light_data, "light_level")
```

## 📊 **Service Status**

### **Status Information**
```python
status = publisher.get_status()

# Available fields:
{
    "service": "telemetry_publisher",
    "mqtt_client_available": True/False,
    "publish_count": 123,           # Total successful publishes
    "error_count": 5,               # Total failed publishes
    "success_rate": 0.961           # Success rate (0.0 to 1.0)
}
```

### **Monitoring Integration**
```python
# Check if service is healthy
if status['mqtt_client_available'] and status['success_rate'] > 0.9:
    print("✅ Telemetry publisher is healthy")
else:
    print("⚠️ Telemetry publisher needs attention")
```

## 🔧 **Configuration**

### **MQTT Client Setup**
```python
# In core/api.py
from services.telemetry_publisher import get_telemetry_publisher

# Initialize MQTT client
client = mqtt.Client()
client.username_pw_set(device_token)

# Initialize telemetry publisher with MQTT client
telemetry_publisher = get_telemetry_publisher(client)
print("✅ Telemetry publisher service initialized with MQTT client")
```

### **Error Handling**
The service automatically handles:
- Missing MQTT client
- MQTT publishing failures
- Invalid telemetry data
- Import errors for optional dependencies

## 🧪 **Testing**

### **Standalone Testing**
```bash
# Test the service without MQTT client
python3 services/telemetry_publisher.py

# Test integration
python3 test_telemetry_publisher_integration.py
```

### **Integration Testing**
```python
# Test with mock MQTT client
import unittest
from unittest.mock import Mock

class TestTelemetryPublisher(unittest.TestCase):
    def setUp(self):
        self.mock_mqtt = Mock()
        self.publisher = TelemetryPublisher(self.mock_mqtt)
    
    def test_publish_lidar(self):
        telemetry_data = {"ts": 1234567890, "values": {"test": "data"}}
        result = self.publisher.publish_lidar_telemetry(telemetry_data)
        self.assertTrue(result)
        self.mock_mqtt.publish.assert_called_once()
```

## 📈 **Benefits**

### **1. Code Organization**
- **Before**: 5 publish functions scattered in `core/api.py`
- **After**: Single service file with organized methods

### **2. Maintainability**
- **Before**: Changes require editing main API file
- **After**: Changes isolated to service file

### **3. Testing**
- **Before**: Hard to test individual publish functions
- **After**: Easy to test service methods independently

### **4. Reusability**
- **Before**: Functions tied to main API
- **After**: Service can be imported anywhere

### **5. Error Handling**
- **Before**: Inconsistent error handling across functions
- **After**: Unified error handling and logging

## 🔄 **Migration Path**

### **Step 1: Import Service**
```python
# Add to core/api.py
from services.telemetry_publisher import (
    get_telemetry_publisher,
    publish_lidar_telemetry,
    publish_occupancy_telemetry,
    publish_proximity_alert_telemetry,
    publish_environmental_telemetry,
    publish_telemetry
)
```

### **Step 2: Initialize Service**
```python
# After MQTT client setup
telemetry_publisher = get_telemetry_publisher(client)
```

### **Step 3: Remove Old Functions**
- Delete old `publish_*` functions from `core/api.py`
- Keep function calls (they now use imported functions)

### **Step 4: Test Integration**
- Run integration tests
- Verify all telemetry publishing works
- Check logging and error handling

## 🚨 **Troubleshooting**

### **Common Issues**

#### **1. Import Errors**
```python
# Error: ModuleNotFoundError: No module named 'telemetry_publisher'
# Solution: Ensure services/ is in Python path
sys.path.append('services')
```

#### **2. MQTT Client Not Available**
```python
# Warning: MQTT client not available for telemetry publishing
# Solution: Initialize service with MQTT client
telemetry_publisher = get_telemetry_publisher(mqtt_client)
```

#### **3. Function Not Found**
```python
# Error: NameError: name 'publish_lidar_telemetry' is not defined
# Solution: Import convenience functions
from services.telemetry_publisher import publish_lidar_telemetry
```

### **Debug Mode**
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check service status
status = telemetry_publisher.get_status()
print(f"Service status: {status}")
```

## 📋 **API Reference**

### **TelemetryPublisher Class**

#### **Methods**
- `__init__(mqtt_client=None)` - Initialize publisher
- `set_mqtt_client(mqtt_client)` - Set MQTT client
- `publish_lidar_telemetry(telemetry_data)` - Publish LiDAR data
- `publish_occupancy_telemetry(occupancy_data)` - Publish occupancy data
- `publish_proximity_alert_telemetry(proximity_data)` - Publish proximity alerts
- `publish_environmental_telemetry(telemetry_data, sensor_type)` - Publish environmental data
- `publish_telemetry(telemetry_data)` - Publish general telemetry
- `get_status()` - Get service status

#### **Properties**
- `mqtt_client` - Current MQTT client instance
- `publish_count` - Total successful publishes
- `error_count` - Total failed publishes

### **Convenience Functions**
- `publish_lidar_telemetry(telemetry_data)` - Direct LiDAR publishing
- `publish_occupancy_telemetry(occupancy_data)` - Direct occupancy publishing
- `publish_proximity_alert_telemetry(proximity_data)` - Direct proximity publishing
- `publish_environmental_telemetry(telemetry_data, sensor_type)` - Direct environmental publishing
- `publish_telemetry(telemetry_data)` - Direct general telemetry publishing

## 🎉 **Conclusion**

The **Telemetry Publisher Service** successfully centralizes all telemetry publishing functionality into a single, maintainable service. This integration provides:

- ✅ **Cleaner API code** - Removed 5 publish functions from `core/api.py`
- ✅ **Better organization** - All publishing logic in one service file
- ✅ **Improved maintainability** - Changes isolated to service file
- ✅ **Enhanced testing** - Easy to test publishing functions independently
- ✅ **Consistent behavior** - Unified error handling and logging
- ✅ **Easy integration** - Simple import and initialization

The service is now ready for production use and provides a solid foundation for future telemetry publishing enhancements.
