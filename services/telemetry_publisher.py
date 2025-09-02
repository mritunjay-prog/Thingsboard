#!/usr/bin/env python3
"""
Telemetry Publisher Service

Centralized service for publishing telemetry data to ThingsBoard MQTT.
Consolidates all publish functions from core/api.py for better organization.
"""

import json
import time
from typing import Dict, Any, Optional
from datetime import datetime


class TelemetryPublisher:
    """
    Centralized telemetry publisher for all sensor types.
    Handles MQTT publishing, database saving, and logging.
    """
    
    def __init__(self, mqtt_client=None):
        """
        Initialize the telemetry publisher
        
        Args:
            mqtt_client: MQTT client instance for publishing
        """
        self.mqtt_client = mqtt_client
        self.publish_count = 0
        self.error_count = 0
        
        print("📡 Telemetry Publisher Service initialized")
    
    def set_mqtt_client(self, mqtt_client):
        """Set the MQTT client for publishing"""
        self.mqtt_client = mqtt_client
        print("✅ MQTT client set for telemetry publisher")
    
    def _publish_to_mqtt(self, topic: str, payload: Dict[str, Any]) -> bool:
        """
        Publish data to MQTT topic
        
        Args:
            topic: MQTT topic to publish to
            payload: Data payload to publish
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            if self.mqtt_client:
                self.mqtt_client.publish(topic, json.dumps(payload))
                self.publish_count += 1
                return True
            else:
                print("⚠️ Warning: MQTT client not available for telemetry publishing")
                return False
        except Exception as e:
            print(f"❌ Error publishing to MQTT: {e}")
            self.error_count += 1
            return False
    
    def publish_lidar_telemetry(self, telemetry_data: Dict[str, Any]) -> bool:
        """
        Publish LiDAR telemetry data to ThingsBoard
        
        Args:
            telemetry_data: LiDAR telemetry data in ThingsBoard format
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Publish to MQTT
            success = self._publish_to_mqtt("v1/devices/me/telemetry", telemetry_data)
            
            if success:
                print(f"📡 LiDAR telemetry published successfully")
            else:
                print(f"⚠️ LiDAR telemetry MQTT publishing failed")
            
            return success
            
        except Exception as e:
            print(f"❌ Error publishing LiDAR telemetry: {e}")
            return False
    
    def publish_occupancy_telemetry(self, occupancy_data: Dict[str, Any]) -> bool:
        """
        Publish occupancy telemetry data to ThingsBoard
        
        Args:
            occupancy_data: Dictionary containing occupancy telemetry data
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Publish to MQTT
            success = self._publish_to_mqtt("v1/devices/me/telemetry", occupancy_data)
            
            if success:
                # Extract and log occupancy details
                occupancy_detected = occupancy_data.get('values', {}).get('lidar.occupancy.detected', False)
                if occupancy_detected:
                    object_height = occupancy_data.get('values', {}).get('lidar.occupancy.object_height', 0)
                    object_width = occupancy_data.get('values', {}).get('lidar.occupancy.object_width', 0)
                    distance = occupancy_data.get('values', {}).get('lidar.occupancy.distance_from_sensor', 0)
                    print(f"🚗 OCCUPANCY DETECTED: {object_height}m x {object_width}m vehicle at {distance}m distance - Published to MQTT!")
                else:
                    print(f"⚪ Space empty - no telemetry sent")
                
                return True
            else:
                print(f"⚠️ Occupancy telemetry MQTT publishing failed")
                return False
                
        except Exception as e:
            print(f"❌ Error publishing occupancy telemetry: {e}")
            return False
    
    def publish_proximity_alert_telemetry(self, proximity_data: Dict[str, Any]) -> bool:
        """
        Publish proximity alert telemetry data to ThingsBoard
        
        Args:
            proximity_data: Dictionary containing proximity alert telemetry data
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Publish to MQTT
            success = self._publish_to_mqtt("v1/devices/me/telemetry", proximity_data)
            
            if success:
                # Extract and log proximity details
                sensor_id = proximity_data.get('values', {}).get('ultrasonic.proximity_alert.sensor_id', 0)
                distance_cm = proximity_data.get('values', {}).get('ultrasonic.proximity_alert.distance_cm', 0)
                threshold_cm = proximity_data.get('values', {}).get('ultrasonic.proximity_alert.threshold_cm', 0)
                duration_ms = proximity_data.get('values', {}).get('ultrasonic.proximity_alert.duration_ms', 0)
                object_approaching = proximity_data.get('values', {}).get('ultrasonic.proximity_alert.object_approaching', False)
                
                approach_status = "approaching" if object_approaching else "stationary"
                print(f"🚨 PROXIMITY ALERT: Sensor {sensor_id} detected {approach_status} object at {distance_cm}cm (threshold: {threshold_cm}cm, duration: {duration_ms}ms) - Published to MQTT!")
                
                return True
            else:
                print(f"⚠️ Proximity alert telemetry MQTT publishing failed")
                return False
                
        except Exception as e:
            print(f"❌ Error publishing proximity alert telemetry: {e}")
            return False
    
    def publish_environmental_telemetry(self, telemetry_data: Dict[str, Any], sensor_type: str) -> bool:
        """
        Publish environmental telemetry data to ThingsBoard
        
        Args:
            telemetry_data: Dictionary containing environmental telemetry data
            sensor_type: Type of environmental sensor (environment, air_quality, light_level)
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Publish to MQTT
            success = self._publish_to_mqtt("v1/devices/me/telemetry", telemetry_data)
            
            if success:
                # Extract and log environmental details
                values = telemetry_data.get("values", {})
                value_count = len(values)
                
                if sensor_type == "environment":
                    temp = values.get("environment.temperature_c", 0)
                    humidity = values.get("environment.humidity_percent", 0)
                    pressure = values.get("environment.pressure_hpa", 0)
                    print(f"🌡️ Environment: {temp}°C, {humidity}%RH, {pressure}hPa - Published to MQTT!")
                elif sensor_type == "air_quality":
                    pm25 = values.get("air_quality.pm2_5_ugm3", 0)
                    aqi = values.get("air_quality.aqi", 0)
                    category = values.get("air_quality.aqi_category", "unknown")
                    print(f"🌬️ Air Quality: PM2.5:{pm25}μg/m³, AQI:{aqi}({category}) - Published to MQTT!")
                elif sensor_type == "light_level":
                    lux = values.get("light.ambient_lux", 0)
                    uv = values.get("light.uv_index", 0)
                    state = values.get("light.day_night_state", "unknown")
                    print(f"💡 Light: {lux}lux, UV:{uv}, {state} - Published to MQTT!")
                else:
                    print(f"📡 Environmental telemetry published: {value_count} metrics - Published to MQTT!")
                
                return True
            else:
                print(f"⚠️ Environmental telemetry MQTT publishing failed")
                return False
                
        except Exception as e:
            print(f"❌ Error publishing environmental telemetry: {e}")
            return False
    
    def publish_telemetry(self, telemetry_data: Dict[str, Any]) -> bool:
        """
        Publish general telemetry data to ThingsBoard
        
        Args:
            telemetry_data: Dictionary containing telemetry data in ThingsBoard format
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Publish to MQTT
            success = self._publish_to_mqtt("v1/devices/me/telemetry", telemetry_data)
            
            if success:
                # Check if this is ultrasonic telemetry data and save it
                if "values" in telemetry_data:
                    values = telemetry_data["values"]
                    ultrasonic_keys = [key for key in values.keys() if key.startswith("ultrasonic.sensor_")]
                    
                    if ultrasonic_keys:
                        # This is ultrasonic telemetry data - save it to file
                        try:
                            from sensors.ultrasonic import save_ultrasonic_telemetry_to_file
                            save_ultrasonic_telemetry_to_file(telemetry_data)
                            print(f"📡 Ultrasonic telemetry published & saved: {len(ultrasonic_keys)} sensor metrics")
                        except ImportError:
                            print(f"📡 Ultrasonic telemetry published (file save not available): {len(ultrasonic_keys)} sensor metrics")
                        except Exception as save_error:
                            print(f"⚠️ Failed to save ultrasonic telemetry: {save_error}")
                            print(f"📡 Ultrasonic telemetry published (save failed): {len(ultrasonic_keys)} sensor metrics")
                    else:
                        print(f"📡 Telemetry published: {len(telemetry_data.get('values', {}))} metrics")
                else:
                    print(f"📡 Telemetry published: {len(telemetry_data)} data points")
                
                return True
            else:
                print(f"⚠️ General telemetry MQTT publishing failed")
                return False
                
        except Exception as e:
            print(f"❌ Error publishing telemetry: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get publisher service status
        
        Returns:
            Dictionary containing service status information
        """
        return {
            "service": "telemetry_publisher",
            "mqtt_client_available": self.mqtt_client is not None,
            "publish_count": self.publish_count,
            "error_count": self.error_count,
            "success_rate": (self.publish_count / (self.publish_count + self.error_count)) if (self.publish_count + self.error_count) > 0 else 0
        }


# Global instance
_telemetry_publisher = None

def get_telemetry_publisher(mqtt_client=None) -> TelemetryPublisher:
    """Get global telemetry publisher instance"""
    global _telemetry_publisher
    if _telemetry_publisher is None:
        _telemetry_publisher = TelemetryPublisher(mqtt_client)
    elif mqtt_client and _telemetry_publisher.mqtt_client != mqtt_client:
        _telemetry_publisher.set_mqtt_client(mqtt_client)
    return _telemetry_publisher


# Convenience functions for direct use
def publish_lidar_telemetry(telemetry_data: Dict[str, Any]) -> bool:
    """Convenience function to publish LiDAR telemetry"""
    publisher = get_telemetry_publisher()
    return publisher.publish_lidar_telemetry(telemetry_data)

def publish_occupancy_telemetry(occupancy_data: Dict[str, Any]) -> bool:
    """Convenience function to publish occupancy telemetry"""
    publisher = get_telemetry_publisher()
    return publisher.publish_occupancy_telemetry(occupancy_data)

def publish_proximity_alert_telemetry(proximity_data: Dict[str, Any]) -> bool:
    """Convenience function to publish proximity alert telemetry"""
    publisher = get_telemetry_publisher()
    return publisher.publish_proximity_alert_telemetry(proximity_data)

def publish_environmental_telemetry(telemetry_data: Dict[str, Any], sensor_type: str) -> bool:
    """Convenience function to publish environmental telemetry"""
    publisher = get_telemetry_publisher()
    return publisher.publish_environmental_telemetry(telemetry_data, sensor_type)

def publish_telemetry(telemetry_data: Dict[str, Any]) -> bool:
    """Convenience function to publish general telemetry"""
    publisher = get_telemetry_publisher()
    return publisher.publish_telemetry(telemetry_data)


# Command line interface for testing
if __name__ == "__main__":
    print("🧪 Testing Telemetry Publisher Service")
    
    # Test without MQTT client
    publisher = TelemetryPublisher()
    
    # Test data
    test_telemetry = {
        "ts": int(time.time() * 1000),
        "values": {
            "test.sensor.value": 42.5,
            "test.sensor.status": "active"
        }
    }
    
    # Test publishing (will fail without MQTT client)
    result = publisher.publish_telemetry(test_telemetry)
    print(f"Test publish result: {result}")
    
    # Show status
    status = publisher.get_status()
    print(f"Publisher status: {status}")
