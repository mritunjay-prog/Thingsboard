import logging
import time
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime
import socket
import atexit
import json
import threading
from dataclasses import dataclass, asdict

@dataclass
class LidarTelemetryData:
    """Structured data class for LiDAR telemetry information."""
    timestamp: float
    scan_id: str
    points_count: int
    scan_duration_ms: float
    occupancy_detected: bool
    range_min: float
    range_max: float
    resolution_deg: float
    scan_rate_hz: float
    sensor_status: str
    data_format: str
    compression_ratio: Optional[float] = None
    quality_score: Optional[float] = None

class LidarTelemetryLogger:
    """Specialized logger for LiDAR telemetry operations with detailed data logging."""
    
    def __init__(self, device_name: Optional[str] = None, log_base_dir: str = "data/logs/lidar"):
        self.device_name = device_name or self._get_device_name()
        self.log_base_dir = Path(log_base_dir)
        
        # Create specialized log directories
        self.log_base_dir.mkdir(parents=True, exist_ok=True)
        (self.log_base_dir / "telemetry").mkdir(exist_ok=True)
        (self.log_base_dir / "scans").mkdir(exist_ok=True)
        (self.log_base_dir / "errors").mkdir(exist_ok=True)
        (self.log_base_dir / "performance").mkdir(exist_ok=True)
        
        # Store active scanning sessions
        self._active_scans: Dict[str, Dict] = {}
        self._scan_loggers: Dict[str, logging.Logger] = {}
        self._scan_handlers: Dict[str, logging.FileHandler] = {}
        
        # Thread lock for concurrent operations
        self._lock = threading.Lock()
        
        # Performance tracking
        self._performance_stats = {
            'total_scans': 0,
            'total_points': 0,
            'total_scan_time_ms': 0,
            'errors_count': 0,
            'start_time': time.time()
        }
        
        # Register cleanup on exit
        atexit.register(self._cleanup_all_scans)
        
        # Setup main LiDAR logger
        self.main_logger = self._create_main_logger()
        self.main_logger.info(f"LiDAR Telemetry Logger initialized for device: {self.device_name}")
        
        print(f"🔍 LiDAR Telemetry Logger initialized for device: {self.device_name}")
    
    def _get_device_name(self) -> str:
        """Get device name from hostname."""
        try:
            return socket.gethostname().replace('.', '_').replace('-', '_')
        except Exception:
            return "unknown_device"
    
    def _create_main_logger(self) -> logging.Logger:
        """Create main LiDAR logger."""
        log_file = self.log_base_dir / "lidar_main.log"
        
        logger = logging.getLogger(f"{self.device_name}_lidar_main")
        logger.setLevel(logging.DEBUG)
        
        if logger.handlers:
            logger.handlers.clear()
        
        # Create file handler
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | LIDAR[MAIN] | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def start_scan_session(self, scan_id: str, scan_params: Dict) -> logging.Logger:
        """Start a new LiDAR scan session with dedicated logger."""
        with self._lock:
            if scan_id in self._active_scans:
                return self._scan_loggers[scan_id]
            
            start_epoch = int(time.time())
            
            # Create session info
            self._active_scans[scan_id] = {
                'scan_id': scan_id,
                'start_time': start_epoch,
                'end_time': None,
                'log_file': None,
                'scan_params': scan_params,
                'status': 'active',
                'points_collected': 0,
                'scan_duration_ms': 0
            }
            
            # Create log file for this scan
            log_file = self.log_base_dir / "scans" / f"scan_{scan_id}_{start_epoch}_active.log"
            self._active_scans[scan_id]['log_file'] = log_file
            
            # Create dedicated logger for this scan
            logger_name = f"{self.device_name}_lidar_scan_{scan_id}_{start_epoch}"
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
            
            if logger.handlers:
                logger.handlers.clear()
            
            # Create file handler
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # Create specialized formatter for LiDAR scans
            formatter = logging.Formatter(
                '%(asctime)s | LIDAR[SCAN:%(scan_id)s] | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Custom filter to add scan_id
            class ScanFilter(logging.Filter):
                def __init__(self, scan_id):
                    super().__init__()
                    self.scan_id = scan_id
                
                def filter(self, record):
                    record.scan_id = self.scan_id
                    return True
            
            file_handler.addFilter(ScanFilter(scan_id))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            self._scan_loggers[scan_id] = logger
            self._scan_handlers[scan_id] = file_handler
            
            # Log scan session start
            logger.info(f"LiDAR scan session started", extra={
                'scan_params': scan_params,
                'session_start': start_epoch
            })
            
            self.main_logger.info(f"New LiDAR scan session started: {scan_id}")
            return logger
    
    def log_telemetry_data(self, scan_id: str, telemetry_data: Dict, data_type: str = "scan"):
        """Log LiDAR telemetry data with detailed information."""
        if scan_id not in self._active_scans:
            self.main_logger.warning(f"Attempted to log telemetry for unknown scan: {scan_id}")
            return
        
        scan_logger = self._scan_loggers[scan_id]
        scan_session = self._active_scans[scan_id]
        
        # Update session statistics
        if data_type == "scan":
            scan_session['points_collected'] = telemetry_data.get('points_count', 0)
            scan_session['scan_duration_ms'] = telemetry_data.get('scan_time_ms', 0)
            
            # Update global performance stats
            with self._lock:
                self._performance_stats['total_scans'] += 1
                self._performance_stats['total_points'] += telemetry_data.get('points_count', 0)
                self._performance_stats['total_scan_time_ms'] += telemetry_data.get('scan_time_ms', 0)
        
        # Create detailed log message
        log_message = f"LiDAR {data_type} data captured"
        
        # Log with structured data
        scan_logger.info(log_message, extra={
            'data_type': data_type,
            'telemetry_data': telemetry_data,
            'session_stats': {
                'points_collected': scan_session['points_collected'],
                'scan_duration_ms': scan_session['scan_duration_ms'],
                'session_duration': int(time.time()) - scan_session['start_time']
            }
        })
        
        # Also log to main logger for overview
        self.main_logger.info(f"Telemetry data logged for scan {scan_id}: {data_type}", extra={
            'scan_id': scan_id,
            'data_type': data_type,
            'points_count': telemetry_data.get('points_count', 0),
            'scan_time_ms': telemetry_data.get('scan_time_ms', 0)
        })
    
    def log_scan_summary(self, scan_id: str, summary_data: Dict):
        """Log LiDAR scan summary with performance metrics."""
        if scan_id not in self._active_scans:
            self.main_logger.warning(f"Attempted to log summary for unknown scan: {scan_id}")
            return
        
        scan_logger = self._scan_loggers[scan_id]
        scan_session = self._active_scans[scan_id]
        
        # Calculate scan performance metrics
        scan_duration = time.time() - scan_session['start_time']
        points_per_second = scan_session['points_collected'] / (scan_duration / 1000) if scan_duration > 0 else 0
        
        # Create performance summary
        performance_summary = {
            'scan_id': scan_id,
            'total_points': scan_session['points_collected'],
            'scan_duration_seconds': scan_duration,
            'points_per_second': round(points_per_second, 2),
            'efficiency_score': round((scan_session['points_collected'] / max(scan_duration, 1)) * 100, 2),
            'summary_data': summary_data
        }
        
        # Log performance summary
        scan_logger.info("LiDAR scan performance summary", extra=performance_summary)
        
        # Log to performance log file
        self._log_performance_data(performance_summary)
        
        # Update main logger
        self.main_logger.info(f"Scan {scan_id} completed - Performance summary logged", extra={
            'scan_id': scan_id,
            'points_collected': scan_session['points_collected'],
            'duration_seconds': round(scan_duration, 2),
            'efficiency_score': performance_summary['efficiency_score']
        })
    
    def log_lidar_error(self, scan_id: str, error: Exception, context: str = "", error_data: Dict = None):
        """Log LiDAR-specific errors with context."""
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': time.time(),
            'scan_id': scan_id
        }
        
        if error_data:
            error_info['error_data'] = error_data
        
        # Log to scan logger if available
        if scan_id in self._scan_loggers:
            scan_logger = self._scan_loggers[scan_id]
            scan_logger.error(f"LiDAR error in {context}: {error}", extra=error_info)
        
        # Log to main logger
        self.main_logger.error(f"LiDAR error in scan {scan_id}: {error}", extra=error_info)
        
        # Log to dedicated error log file
        self._log_error_data(error_info)
        
        # Update error count
        with self._lock:
            self._performance_stats['errors_count'] += 1
    
    def _log_performance_data(self, performance_data: Dict):
        """Log performance data to dedicated performance log."""
        performance_log_file = self.log_base_dir / "performance" / "lidar_performance.log"
        
        # Create performance logger
        perf_logger = logging.getLogger(f"{self.device_name}_lidar_performance")
        perf_logger.setLevel(logging.INFO)
        
        if perf_logger.handlers:
            perf_logger.handlers.clear()
        
        # Create file handler
        file_handler = logging.FileHandler(performance_log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | LIDAR[PERF] | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        perf_logger.addHandler(file_handler)
        
        # Log performance data
        perf_logger.info("Performance data", extra=performance_data)
        
        # Clean up handler
        perf_logger.removeHandler(file_handler)
        file_handler.close()
    
    def _log_error_data(self, error_data: Dict):
        """Log error data to dedicated error log."""
        error_log_file = self.log_base_dir / "errors" / "lidar_errors.log"
        
        # Create error logger
        error_logger = logging.getLogger(f"{self.device_name}_lidar_errors")
        error_logger.setLevel(logging.ERROR)
        
        if error_logger.handlers:
            error_logger.handlers.clear()
        
        # Create file handler
        file_handler = logging.FileHandler(error_log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.ERROR)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | LIDAR[ERROR] | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        error_logger.addHandler(file_handler)
        
        # Log error data
        error_logger.error("Error occurred", extra=error_data)
        
        # Clean up handler
        error_logger.removeHandler(file_handler)
        file_handler.close()
    
    def end_scan_session(self, scan_id: str):
        """End LiDAR scan session and finalize logging."""
        if scan_id not in self._active_scans:
            return
        
        with self._lock:
            scan_session = self._active_scans[scan_id]
            end_epoch = int(time.time())
            scan_session['end_time'] = end_epoch
            
            # Close the current handler
            if scan_id in self._scan_handlers:
                handler = self._scan_handlers[scan_id]
                logger = self._scan_loggers[scan_id]
                
                # Log session end
                logger.info(f"LiDAR scan session ended for {scan_id}", extra={
                    'session_duration': end_epoch - scan_session['start_time'],
                    'total_points': scan_session['points_collected'],
                    'final_scan_time_ms': scan_session['scan_duration_ms']
                })
                
                # Remove handler and close it
                logger.removeHandler(handler)
                handler.close()
                
                # Rename log file to final format
                old_file = scan_session['log_file']
                new_file = self.log_base_dir / "scans" / f"scan_{scan_id}_{scan_session['start_time']}_{end_epoch}.log"
                
                try:
                    if old_file.exists():
                        old_file.rename(new_file)
                        print(f"✅ LiDAR scan log renamed: {new_file.name}")
                except Exception as e:
                    print(f"❌ Failed to rename LiDAR scan log for {scan_id}: {e}")
                
                # Clean up references
                del self._scan_handlers[scan_id]
                del self._scan_loggers[scan_id]
            
            # Log to main logger
            self.main_logger.info(f"LiDAR scan session {scan_id} ended", extra={
                'scan_id': scan_id,
                'duration_seconds': end_epoch - scan_session['start_time'],
                'points_collected': scan_session['points_collected']
            })
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive LiDAR performance summary."""
        uptime = time.time() - self._performance_stats['start_time']
        
        return {
            'device_name': self.device_name,
            'uptime_seconds': round(uptime, 2),
            'total_scans': self._performance_stats['total_scans'],
            'total_points': self._performance_stats['total_points'],
            'total_scan_time_ms': self._performance_stats['total_scan_time_ms'],
            'errors_count': self._performance_stats['errors_count'],
            'average_points_per_scan': round(self._performance_stats['total_points'] / max(self._performance_stats['total_scans'], 1), 2),
            'average_scan_time_ms': round(self._performance_stats['total_scan_time_ms'] / max(self._performance_stats['total_scans'], 1), 2),
            'active_scans': len([s for s in self._active_scans.values() if s['end_time'] is None]),
            'summary_generated_at': datetime.now().isoformat()
        }
    
    def _cleanup_all_scans(self):
        """Cleanup function called on exit."""
        active_scans = list(self._active_scans.keys())
        for scan_id in active_scans:
            if self._active_scans[scan_id]['end_time'] is None:
                self.end_scan_session(scan_id)

# Global instance
_lidar_telemetry_logger_instance: Optional[LidarTelemetryLogger] = None

def setup_lidar_telemetry_logging(device_name: Optional[str] = None, log_base_dir: str = "data/logs/lidar") -> LidarTelemetryLogger:
    """Setup LiDAR telemetry logging system."""
    global _lidar_telemetry_logger_instance
    
    try:
        print(f"🔧 Setting up LiDAR telemetry logging for device: {device_name}")
        print(f"📁 Log base directory: {log_base_dir}")
        
        _lidar_telemetry_logger_instance = LidarTelemetryLogger(device_name, log_base_dir)
        
        if _lidar_telemetry_logger_instance is None:
            raise RuntimeError("LidarTelemetryLogger constructor returned None")
        
        print(f"✅ LiDAR telemetry logging setup completed successfully")
        return _lidar_telemetry_logger_instance
        
    except Exception as e:
        print(f"❌ Failed to setup LiDAR telemetry logging: {e}")
        print(f"   Device name: {device_name}")
        print(f"   Log base directory: {log_base_dir}")
        import traceback
        traceback.print_exc()
        
        # Return a minimal logger to prevent None errors
        try:
            print("🔄 Attempting to create fallback LiDAR logger...")
            fallback_logger = LidarTelemetryLogger("fallback_device", "data/logs/lidar/fallback")
            _lidar_telemetry_logger_instance = fallback_logger
            print("✅ Fallback LiDAR logger created successfully")
            return fallback_logger
        except Exception as fallback_error:
            print(f"❌ Failed to create fallback LiDAR logger: {fallback_error}")
            # Create a minimal mock logger to prevent crashes
            class MockLidarLogger:
                def __init__(self):
                    self.device_name = device_name or "unknown_device"
                
                def start_scan_session(self, scan_id, scan_params):
                    print(f"[MOCK] Started LiDAR scan session: {scan_id}")
                    return self
                
                def log_telemetry_data(self, scan_id, telemetry_data, data_type="scan"):
                    print(f"[MOCK] LiDAR telemetry data for {scan_id}: {data_type}")
                    print(f"[MOCK] Data: {telemetry_data}")
                
                def log_scan_summary(self, scan_id, summary_data):
                    print(f"[MOCK] LiDAR scan summary for {scan_id}: {summary_data}")
                
                def log_lidar_error(self, scan_id, error, context="", error_data=None):
                    print(f"[MOCK] LiDAR error in {scan_id} ({context}): {error}")
                
                def end_scan_session(self, scan_id):
                    print(f"[MOCK] Ended LiDAR scan session: {scan_id}")
                
                def get_performance_summary(self):
                    return {
                        "device_name": self.device_name,
                        "total_scans": 0,
                        "total_points": 0,
                        "errors_count": 0
                    }
                
                def info(self, message):
                    print(f"[MOCK] LiDAR INFO: {message}")
                
                def warning(self, message):
                    print(f"[MOCK] LiDAR WARNING: {message}")
                
                def error(self, message):
                    print(f"[MOCK] LiDAR ERROR: {message}")
            
            mock_logger = MockLidarLogger()
            _lidar_telemetry_logger_instance = mock_logger
            print("⚠️ Using mock LiDAR logger as last resort")
            return mock_logger

def get_lidar_telemetry_logger() -> Optional[LidarTelemetryLogger]:
    """Get the global LiDAR telemetry logger instance."""
    return _lidar_telemetry_logger_instance

if __name__ == "__main__":
    # Test the LiDAR telemetry logging system
    print("Testing LiDAR Telemetry Logger...")
    
    # Setup logger
    logger = setup_lidar_telemetry_logging("test_device")
    
    # Test scan session
    scan_id = "test_scan_001"
    scan_params = {
        "resolution": 0.1,
        "scan_rate_hz": 10.0,
        "range_filter": {"min": 0.1, "max": 100.0}
    }
    
    # Start scan session
    scan_logger = logger.start_scan_session(scan_id, scan_params)
    
    # Simulate telemetry data
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
    
    # Log telemetry data
    logger.log_telemetry_data(scan_id, telemetry_data, "scan")
    
    # Simulate some errors
    try:
        raise ValueError("Simulated LiDAR sensor error")
    except Exception as e:
        logger.log_lidar_error(scan_id, e, "sensor_reading", {"sensor_id": "lidar_001"})
    
    # Log scan summary
    summary_data = {
        "quality_score": 0.95,
        "compression_ratio": 0.8,
        "scan_completion": 100.0
    }
    logger.log_scan_summary(scan_id, summary_data)
    
    # End scan session
    logger.end_scan_session(scan_id)
    
    # Show performance summary
    print("\nLiDAR Performance Summary:")
    perf_summary = logger.get_performance_summary()
    for key, value in perf_summary.items():
        print(f"  {key}: {value}")


