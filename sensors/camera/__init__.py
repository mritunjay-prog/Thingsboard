"""
Camera sensor module for image and video capture functionality.
Provides comprehensive camera control with S3 upload integration and live streaming.
"""

from .camera_capture_service import CameraCaptureService
from .camera_streaming_service import CameraStreamingService

# Global camera service instances
_camera_capture_service = None
_camera_streaming_service = None

def get_camera_capture_service():
    """Get the global camera capture service instance"""
    global _camera_capture_service
    if _camera_capture_service is None:
        _camera_capture_service = CameraCaptureService()
    return _camera_capture_service

def get_camera_streaming_service():
    """Get the global camera streaming service instance"""
    global _camera_streaming_service
    if _camera_streaming_service is None:
        _camera_streaming_service = CameraStreamingService()
    return _camera_streaming_service

# Convenience wrapper functions for timed capture
def timed_camera_capture(
    capture_duration_seconds: int,
    burst_count: int,
    burst_interval_ms: int,
    save_location: str = None,
    device_id: str = None,
    stop_event = None,
    capture_params = None
):
    """
    Convenience function for timed camera capture.
    
    Args:
        capture_duration_seconds (int): Total duration to capture images
        burst_count (int): Number of images per burst
        burst_interval_ms (int): Interval between bursts in milliseconds
        save_location (str, optional): Directory to save captured images
        device_id (str, optional): Device identifier
        stop_event (threading.Event, optional): Stop event
        capture_params (dict, optional): Additional capture parameters
        
    Returns:
        dict: Capture results
    """
    camera_service = get_camera_capture_service()
    return camera_service.timed_camera_capture(
        capture_duration_seconds=capture_duration_seconds,
        burst_count=burst_count,
        burst_interval_ms=burst_interval_ms,
        save_location=save_location,
        device_id=device_id,
        stop_event=stop_event,
        capture_params=capture_params
    )

def estimate_camera_capture_session(
    capture_duration_seconds: int,
    burst_count: int,
    burst_interval_ms: int
):
    """
    Convenience function for estimating camera capture session.
    
    Args:
        capture_duration_seconds (int): Total duration to capture images
        burst_count (int): Number of images per burst
        burst_interval_ms (int): Interval between bursts in milliseconds
        
    Returns:
        dict: Estimated session results
    """
    camera_service = get_camera_capture_service()
    return camera_service.estimate_capture_session(
        capture_duration_seconds=capture_duration_seconds,
        burst_count=burst_count,
        burst_interval_ms=burst_interval_ms
    )

# Export key functions
__all__ = [
    'get_camera_capture_service',
    'get_camera_streaming_service',
    'CameraCaptureService',
    'CameraStreamingService',
    'timed_camera_capture',
    'estimate_camera_capture_session'
]
