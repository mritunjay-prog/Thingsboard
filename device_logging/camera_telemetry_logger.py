import logging
import time
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import socket
import atexit
import json
import threading

class CameraTelemetryLogger:
    """Specialized logger for camera telemetry operations with detailed data logging."""
    
    def __init__(self, device_name: Optional[str] = None, log_base_dir: str = "data/logs/camera"):
        self.device_name = device_name or self._get_device_name()
        self.log_base_dir = Path(log_base_dir)
        
        # Create specialized log directories
        self.log_base_dir.mkdir(parents=True, exist_ok=True)
        (self.log_base_dir / "telemetry").mkdir(exist_ok=True)
        (self.log_base_dir / "captures").mkdir(exist_ok=True)
        (self.log_base_dir / "streaming").mkdir(exist_ok=True)
        (self.log_base_dir / "errors").mkdir(exist_ok=True)
        
        # Store active sessions
        self._active_captures: Dict[str, Dict] = {}
        self._active_streams: Dict[str, Dict] = {}
        self._capture_loggers: Dict[str, logging.Logger] = {}
        self._stream_loggers: Dict[str, logging.Logger] = {}
        
        # Thread lock for concurrent operations
        self._lock = threading.Lock()
        
        # Performance tracking
        self._performance_stats = {
            'total_captures': 0,
            'total_frames': 0,
            'errors_count': 0,
            'start_time': time.time()
        }
        
        # Register cleanup on exit
        atexit.register(self._cleanup_all_sessions)
        
        # Setup main camera logger
        self.main_logger = self._create_main_logger()
        self.main_logger.info(f"Camera Telemetry Logger initialized for device: {self.device_name}")
        
        print(f"📷 Camera Telemetry Logger initialized for device: {self.device_name}")
    
    def _get_device_name(self) -> str:
        """Get device name from hostname."""
        try:
            return socket.gethostname().replace('.', '_').replace('-', '_')
        except Exception:
            return "unknown_device"
    
    def _create_main_logger(self) -> logging.Logger:
        """Create main camera logger."""
        log_file = self.log_base_dir / "camera_main.log"
        
        logger = logging.getLogger(f"{self.device_name}_camera_main")
        logger.setLevel(logging.DEBUG)
        
        if logger.handlers:
            logger.handlers.clear()
        
        # Create file handler
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | CAMERA[MAIN] | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def start_capture_session(self, capture_id: str, capture_params: Dict) -> logging.Logger:
        """Start a new camera capture session with dedicated logger."""
        with self._lock:
            if capture_id in self._active_captures:
                return self._capture_loggers[capture_id]
            
            start_epoch = int(time.time())
            
            # Create session info
            self._active_captures[capture_id] = {
                'capture_id': capture_id,
                'start_time': start_epoch,
                'end_time': None,
                'capture_params': capture_params,
                'status': 'active',
                'frames_captured': 0
            }
            
            # Create dedicated logger for this capture
            logger_name = f"{self.device_name}_camera_capture_{capture_id}_{start_epoch}"
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
            
            if logger.handlers:
                logger.handlers.clear()
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s | CAMERA[CAPTURE:%(capture_id)s] | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Custom filter to add capture_id
            class CaptureFilter(logging.Filter):
                def __init__(self, capture_id):
                    super().__init__()
                    self.capture_id = capture_id
                
                def filter(self, record):
                    record.capture_id = capture_id
                    return True
            
            # Create file handler
            log_file = self.log_base_dir / "captures" / f"capture_{capture_id}_{start_epoch}_active.log"
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.addFilter(CaptureFilter(capture_id))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            self._capture_loggers[capture_id] = logger
            
            # Log capture session start
            logger.info(f"Camera capture session started", extra={
                'capture_params': capture_params,
                'session_start': start_epoch
            })
            
            self.main_logger.info(f"New camera capture session started: {capture_id}")
            return logger
    
    def log_capture_data(self, capture_id: str, capture_data: Dict, data_type: str = "frame"):
        """Log camera capture data with detailed information."""
        if capture_id not in self._active_captures:
            self.main_logger.warning(f"Attempted to log capture data for unknown capture: {capture_id}")
            return
        
        capture_logger = self._capture_loggers[capture_id]
        capture_session = self._active_captures[capture_id]
        
        # Update session statistics
        if data_type == "frame":
            capture_session['frames_captured'] += 1
            
            # Update global performance stats
            with self._lock:
                self._performance_stats['total_captures'] += 1
                self._performance_stats['total_frames'] += 1
        
        # Create detailed log message
        log_message = f"Camera {data_type} data captured"
        
        # Log with structured data
        capture_logger.info(log_message, extra={
            'data_type': data_type,
            'capture_data': capture_data,
            'session_stats': {
                'frames_captured': capture_session['frames_captured'],
                'session_duration': int(time.time()) - capture_session['start_time']
            }
        })
        
        # Also log to main logger for overview
        self.main_logger.info(f"Capture data logged for {capture_id}: {data_type}", extra={
            'capture_id': capture_id,
            'data_type': data_type,
            'frames_captured': capture_session['frames_captured']
        })
    
    def log_camera_error(self, session_id: str, error: Exception, context: str = "", error_data: Dict = None):
        """Log camera-specific errors with context."""
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': time.time(),
            'session_id': session_id
        }
        
        if error_data:
            error_info['error_data'] = error_data
        
        # Log to main logger
        self.main_logger.error(f"Camera error in {session_id}: {error}", extra=error_info)
        
        # Update error count
        with self._lock:
            self._performance_stats['errors_count'] += 1
    
    def end_capture_session(self, capture_id: str):
        """End camera capture session and finalize logging."""
        if capture_id not in self._active_captures:
            return
        
        with self._lock:
            capture_session = self._active_captures[capture_id]
            end_epoch = int(time.time())
            capture_session['end_time'] = end_epoch
            
            # Log session end
            if capture_id in self._capture_loggers:
                logger = self._capture_loggers[capture_id]
                logger.info(f"Camera capture session ended for {capture_id}", extra={
                    'session_duration': end_epoch - capture_session['start_time'],
                    'total_frames': capture_session['frames_captured']
                })
                
                # Clean up logger
                del self._capture_loggers[capture_id]
            
            # Log to main logger
            self.main_logger.info(f"Camera capture session {capture_id} ended", extra={
                'capture_id': capture_id,
                'duration_seconds': end_epoch - capture_session['start_time'],
                'frames_captured': capture_session['frames_captured']
            })
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive camera performance summary."""
        uptime = time.time() - self._performance_stats['start_time']
        
        return {
            'device_name': self.device_name,
            'uptime_seconds': round(uptime, 2),
            'total_captures': self._performance_stats['total_captures'],
            'total_frames': self._performance_stats['total_frames'],
            'errors_count': self._performance_stats['errors_count'],
            'active_captures': len([c for c in self._active_captures.values() if c['end_time'] is None]),
            'summary_generated_at': datetime.now().isoformat()
        }
    
    def _cleanup_all_sessions(self):
        """Cleanup function called on exit."""
        active_captures = list(self._active_captures.keys())
        
        for capture_id in active_captures:
            if self._active_captures[capture_id]['end_time'] is None:
                self.end_capture_session(capture_id)

# Global instance
_camera_telemetry_logger_instance: Optional[CameraTelemetryLogger] = None

def setup_camera_telemetry_logging(device_name: Optional[str] = None, log_base_dir: str = "data/logs/camera") -> CameraTelemetryLogger:
    """Setup camera telemetry logging system."""
    global _camera_telemetry_logger_instance
    
    try:
        print(f"🔧 Setting up camera telemetry logging for device: {device_name}")
        print(f"📁 Log base directory: {log_base_dir}")
        
        _camera_telemetry_logger_instance = CameraTelemetryLogger(device_name, log_base_dir)
        
        if _camera_telemetry_logger_instance is None:
            raise RuntimeError("CameraTelemetryLogger constructor returned None")
        
        print(f"✅ Camera telemetry logging setup completed successfully")
        return _camera_telemetry_logger_instance
        
    except Exception as e:
        print(f"❌ Failed to setup camera telemetry logging: {e}")
        print(f"   Device name: {device_name}")
        print(f"   Log base directory: {log_base_dir}")
        import traceback
        traceback.print_exc()
        
        # Return a minimal logger to prevent None errors
        try:
            print("🔄 Attempting to create fallback camera logger...")
            fallback_logger = CameraTelemetryLogger("fallback_device", "data/logs/camera/fallback")
            _camera_telemetry_logger_instance = fallback_logger
            print("✅ Fallback camera logger created successfully")
            return fallback_logger
        except Exception as fallback_error:
            print(f"❌ Failed to create fallback camera logger: {fallback_error}")
            # Create a minimal mock logger to prevent crashes
            class MockCameraLogger:
                def __init__(self):
                    self.device_name = device_name or "unknown_device"
                
                def start_capture_session(self, capture_id, capture_params):
                    print(f"[MOCK] Started camera capture session: {capture_id}")
                    return self
                
                def log_capture_data(self, capture_id, capture_data, data_type="frame"):
                    print(f"[MOCK] Camera capture data for {capture_id}: {data_type}")
                    print(f"[MOCK] Data: {capture_data}")
                
                def log_camera_error(self, session_id, error, context="", error_data=None):
                    print(f"[MOCK] Camera error in {session_id} ({context}): {error}")
                
                def end_capture_session(self, capture_id):
                    print(f"[MOCK] Ended camera capture session: {capture_id}")
                
                def get_performance_summary(self):
                    return {
                        "device_name": self.device_name,
                        "total_captures": 0,
                        "total_frames": 0,
                        "errors_count": 0
                    }
                
                def info(self, message):
                    print(f"[MOCK] Camera INFO: {message}")
                
                def warning(self, message):
                    print(f"[MOCK] Camera WARNING: {message}")
                
                def error(self, message):
                    print(f"[MOCK] Camera ERROR: {message}")
            
            mock_logger = MockCameraLogger()
            _camera_telemetry_logger_instance = mock_logger
            print("⚠️ Using mock camera logger as last resort")
            return mock_logger

def get_camera_telemetry_logger() -> Optional[CameraTelemetryLogger]:
    """Get the global camera telemetry logger instance."""
    return _camera_telemetry_logger_instance

if __name__ == "__main__":
    # Test the camera telemetry logging system
    print("Testing Camera Telemetry Logger...")
    
    # Setup logger
    logger = setup_camera_telemetry_logging("test_device")
    
    # Test capture session
    capture_id = "test_capture_001"
    capture_params = {
        "resolution": "1920x1080",
        "frame_rate": 30.0,
        "exposure_time_ms": 16.67,
        "iso": 100
    }
    
    # Start capture session
    capture_logger = logger.start_capture_session(capture_id, capture_params)
    
    # Simulate capture data
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
    
    # Log capture data
    logger.log_capture_data(capture_id, capture_data, "frame")
    
    # Test streaming session
    stream_id = "test_stream_001"
    stream_params = {
        "resolution": "1280x720",
        "frame_rate": 25.0,
        "bitrate": "2Mbps"
    }
    
    # Start streaming session
    stream_logger = logger.start_streaming_session(stream_id, stream_params)
    
    # Simulate streaming data
    streaming_data = {
        "resolution": "1280x720",
        "frame_rate": 25.0,
        "bitrate": "2Mbps",
        "streaming_time_ms": 40.0,
        "frames_dropped": 0,
        "network_latency_ms": 15.0
    }
    
    # Log streaming data
    logger.log_streaming_data(stream_id, streaming_data, "frame")
    
    # Simulate some errors
    try:
        raise RuntimeError("Simulated camera sensor error")
    except Exception as e:
        logger.log_camera_error(capture_id, e, "sensor_reading", {"sensor_id": "camera_001"})
    
    # End sessions
    logger.end_capture_session(capture_id)
    logger.end_streaming_session(stream_id)
    
    # Show performance summary
    print("\nCamera Performance Summary:")
    perf_summary = logger.get_performance_summary()
    for key, value in perf_summary.items():
        print(f"  {key}: {value}")
