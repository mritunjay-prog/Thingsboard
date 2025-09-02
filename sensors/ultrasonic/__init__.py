"""
Ultrasonic Sensor Module

This module provides ultrasonic sensor functionality for distance measurement
and telemetry data generation with temperature compensation.
"""

from .ultrasonic_service import UltrasonicControlService
from .ultrasonic_streaming import UltrasonicStreamingService
from .proximity_detector import ProximityDetector, get_proximity_detector
from .telemetry_file_saver import (
    save_ultrasonic_telemetry_to_file,
    get_ultrasonic_telemetry_file_status,
    reset_ultrasonic_telemetry_file,
    get_ultrasonic_telemetry_summary
)
import time
import random
from typing import Dict, Any, Optional

# Global instances
_ultrasonic_control_service = None
_ultrasonic_streaming_service = None
_proximity_detector = None

def get_ultrasonic_control_service():
    """Get the global ultrasonic control service instance"""
    global _ultrasonic_control_service
    if _ultrasonic_control_service is None:
        _ultrasonic_control_service = UltrasonicControlService()
    return _ultrasonic_control_service

def get_ultrasonic_streaming_service(telemetry_callback=None):
    """Get the global ultrasonic streaming service instance"""
    global _ultrasonic_streaming_service
    if _ultrasonic_streaming_service is None:
        _ultrasonic_streaming_service = UltrasonicStreamingService(telemetry_callback)
        # Connect proximity detector with streaming service for real-time processing
        proximity_detector = get_ultrasonic_proximity_detector()
        _ultrasonic_streaming_service.set_proximity_detector(proximity_detector)
    return _ultrasonic_streaming_service

def get_ultrasonic_proximity_detector(telemetry_callback=None):
    """Get the global ultrasonic proximity detector instance"""
    global _proximity_detector
    if _proximity_detector is None:
        _proximity_detector = get_proximity_detector(telemetry_callback)
    return _proximity_detector

def get_ultrasonic_telemetry_data() -> Dict[str, Any]:
    """
    Generate ultrasonic telemetry data with temperature compensation.
    
    Returns:
        Dictionary containing ultrasonic telemetry data in ThingsBoard format
    """
    current_time = int(time.time() * 1000)
    
    # Generate data for 4 ultrasonic sensors with temperature compensation
    telemetry_data = {
        "ts": current_time,
        "values": {}
    }
    
    # Temperature compensation is typically enabled for modern ultrasonic sensors
    temp_compensation_enabled = random.choice([True, True, True, False])  # 75% chance enabled
    
    for sensor_id in range(1, 5):
        # Generate realistic distance readings (5cm to 400cm range)
        distance = round(random.uniform(5.0, 400.0), 1)
        
        # Confidence based on distance and environmental factors
        # Closer objects generally have higher confidence
        if distance < 50:
            confidence = round(random.uniform(0.95, 0.99), 2)
        elif distance < 150:
            confidence = round(random.uniform(0.90, 0.97), 2)
        elif distance < 300:
            confidence = round(random.uniform(0.85, 0.94), 2)
        else:
            confidence = round(random.uniform(0.80, 0.91), 2)
        
        # Add sensor data to telemetry
        telemetry_data["values"].update({
            f"ultrasonic.sensor_{sensor_id}.distance_cm": distance,
            f"ultrasonic.sensor_{sensor_id}.confidence": confidence,
            f"ultrasonic.sensor_{sensor_id}.temperature_compensated": temp_compensation_enabled
        })
    
    return telemetry_data

def get_ultrasonic_summary() -> Dict[str, Any]:
    """
    Get summary statistics from ultrasonic sensor data.
    
    Returns:
        Dictionary containing ultrasonic summary statistics
    """
    # Get current telemetry data
    telemetry = get_ultrasonic_telemetry_data()
    values = telemetry.get("values", {})
    
    # Extract distances from all sensors
    distances = []
    confidences = []
    temp_compensated_count = 0
    
    for sensor_id in range(1, 5):
        distance = values.get(f"ultrasonic.sensor_{sensor_id}.distance_cm", 0)
        confidence = values.get(f"ultrasonic.sensor_{sensor_id}.confidence", 0)
        temp_comp = values.get(f"ultrasonic.sensor_{sensor_id}.temperature_compensated", False)
        
        distances.append(distance)
        confidences.append(confidence)
        if temp_comp:
            temp_compensated_count += 1
    
    # Calculate summary statistics
    if distances:
        avg_distance = round(sum(distances) / len(distances), 1)
        min_distance = round(min(distances), 1)
        max_distance = round(max(distances), 1)
        avg_confidence = round(sum(confidences) / len(confidences), 2)
    else:
        avg_distance = min_distance = max_distance = avg_confidence = 0
    
    return {
        "ultrasonic.avg_distance_cm": avg_distance,
        "ultrasonic.min_distance_cm": min_distance,
        "ultrasonic.max_distance_cm": max_distance,
        "ultrasonic.avg_confidence": avg_confidence,
        "ultrasonic.sensors_active": 4,
        "ultrasonic.temp_compensated_sensors": temp_compensated_count,
        "ultrasonic.system_status": "operational"
    }

# Convenience wrapper functions for timed capture
def timed_ultrasonic_capture(
    sample_rate_hz: float,
    capture_duration_seconds: int,
    save_location: str,
    device_id: str = None,
    stop_event = None,
    capture_params = None
):
    """
    Convenience function for timed ultrasonic capture.
    
    Args:
        sample_rate_hz (float): Sample rate in Hz
        capture_duration_seconds (int): Total duration to capture data
        save_location (str): Directory to save telemetry files
        device_id (str, optional): Device identifier
        stop_event (threading.Event, optional): Stop event
        capture_params (dict, optional): Additional capture parameters
        
    Returns:
        dict: Capture results
    """
    ultrasonic_service = get_ultrasonic_control_service()
    return ultrasonic_service.timed_ultrasonic_capture(
        sample_rate_hz=sample_rate_hz,
        capture_duration_seconds=capture_duration_seconds,
        save_location=save_location,
        device_id=device_id,
        stop_event=stop_event,
        capture_params=capture_params
    )

def estimate_ultrasonic_capture_session(
    sample_rate_hz: float,
    capture_duration_seconds: int
):
    """
    Convenience function for estimating ultrasonic capture session.
    
    Args:
        sample_rate_hz (float): Sample rate in Hz
        capture_duration_seconds (int): Total duration to capture data
        
    Returns:
        dict: Estimated session results
    """
    ultrasonic_service = get_ultrasonic_control_service()
    return ultrasonic_service.estimate_ultrasonic_capture_session(
        sample_rate_hz=sample_rate_hz,
        capture_duration_seconds=capture_duration_seconds
    )

# Export the control service instance for direct access
ultrasonic_control_service = get_ultrasonic_control_service()

# Export all public functions and classes
__all__ = [
    'get_ultrasonic_control_service',
    'get_ultrasonic_streaming_service', 
    'get_ultrasonic_proximity_detector',
    'get_ultrasonic_telemetry_data',
    'get_ultrasonic_summary',
    'timed_ultrasonic_capture',
    'estimate_ultrasonic_capture_session',
    'ultrasonic_control_service',
    'UltrasonicControlService',
    'UltrasonicStreamingService',
    'ProximityDetector',
    'get_proximity_detector',
    'save_ultrasonic_telemetry_to_file',
    'get_ultrasonic_telemetry_file_status',
    'reset_ultrasonic_telemetry_file',
    'get_ultrasonic_telemetry_summary'
]
