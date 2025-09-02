"""
LiDAR sensor module for ThingsBoard integration.

This module provides comprehensive LiDAR functionality including:
- Control service for start/stop/reset operations
- Telemetry streaming service for continuous data generation
- Data collection and file saving capabilities
- Occupancy detection based on LiDAR data
"""

from .lidar_control_service import LidarControlService
from .lidar_telemetry_streaming import LidarTelemetryStreamingService
from .lidar_collector import LidarDataCollector
from .occupancy_detector import OccupancyDetector
from .telemetry_file_saver import save_lidar_telemetry_to_file, get_lidar_telemetry_file_status

# Global service instances (singleton pattern)
_lidar_control_service = None
_lidar_streaming_service = None
_lidar_data_collector = None
_occupancy_detector = None

def get_lidar_control_service():
    """Get the global LiDAR control service instance"""
    global _lidar_control_service
    if _lidar_control_service is None:
        _lidar_control_service = LidarControlService()
        # Connect with data collector and streaming service
        collector = get_lidar_data_collector()
        _lidar_control_service.set_data_collector(collector)
    return _lidar_control_service

def get_lidar_streaming_service(telemetry_callback=None):
    """Get the global LiDAR streaming service instance"""
    global _lidar_streaming_service
    if _lidar_streaming_service is None:
        _lidar_streaming_service = LidarTelemetryStreamingService(telemetry_callback)
        # Connect with data collector
        collector = get_lidar_data_collector()
        _lidar_streaming_service.set_data_collector(collector)
    return _lidar_streaming_service

def get_lidar_data_collector():
    """Get the global LiDAR data collector instance"""
    global _lidar_data_collector
    if _lidar_data_collector is None:
        _lidar_data_collector = LidarDataCollector()
    return _lidar_data_collector

def get_occupancy_detector(telemetry_callback=None):
    """Get the global occupancy detector instance"""
    global _occupancy_detector
    if _occupancy_detector is None:
        _occupancy_detector = OccupancyDetector(telemetry_callback)
        # Connect with data collector
        collector = get_lidar_data_collector()
        _occupancy_detector.set_data_collector(collector)
        # Connect collector to occupancy detector for real-time processing
        collector.set_occupancy_detector(_occupancy_detector)
    return _occupancy_detector

# Convenience functions for API usage
def get_lidar_telemetry_data():
    """Get current LiDAR telemetry data"""
    collector = get_lidar_data_collector()
    return collector.get_current_telemetry()

def get_lidar_summary():
    """Get LiDAR summary data"""
    collector = get_lidar_data_collector()
    return collector.get_summary_data()

# Convenience wrapper functions for timed capture
def timed_lidar_capture(
    capture_duration_seconds: int,
    point_cloud_format: str = "pcd",
    save_location: str = None,
    device_id: str = None,
    stop_event = None,
    capture_params = None
):
    """
    Convenience function for timed LiDAR capture.
    
    Args:
        capture_duration_seconds (int): Total duration to capture LiDAR data
        point_cloud_format (str): Point cloud format ("pcd", "las", or "ply")
        save_location (str, optional): Directory to save captured data
        device_id (str, optional): Device identifier
        stop_event (threading.Event, optional): Stop event
        capture_params (dict, optional): Additional capture parameters
        
    Returns:
        dict: Capture results
    """
    lidar_service = get_lidar_control_service()
    return lidar_service.timed_lidar_capture(
        capture_duration_seconds=capture_duration_seconds,
        point_cloud_format=point_cloud_format,
        save_location=save_location,
        device_id=device_id,
        stop_event=stop_event,
        capture_params=capture_params
    )

def estimate_lidar_capture_session(
    capture_duration_seconds: int,
    scan_rate_hz: float = None
):
    """
    Convenience function for estimating LiDAR capture session.
    
    Args:
        capture_duration_seconds (int): Total duration to capture LiDAR data
        scan_rate_hz (float, optional): Override scan rate
        
    Returns:
        dict: Estimated session results
    """
    lidar_service = get_lidar_control_service()
    return lidar_service.estimate_lidar_capture_session(
        capture_duration_seconds=capture_duration_seconds,
        scan_rate_hz=scan_rate_hz
    )

# Export the main service reference for backward compatibility
lidar_control_service = get_lidar_control_service()

# Export key functions
__all__ = [
    'get_lidar_control_service',
    'get_lidar_streaming_service',
    'get_lidar_data_collector',
    'get_occupancy_detector',
    'get_lidar_telemetry_data',
    'get_lidar_summary',
    'timed_lidar_capture',
    'estimate_lidar_capture_session',
    'LidarControlService',
    'LidarTelemetryStreamingService',
    'LidarDataCollector',
    'OccupancyDetector',
    'save_lidar_telemetry_to_file',
    'get_lidar_telemetry_file_status',
    'lidar_control_service'
]
