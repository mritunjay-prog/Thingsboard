import logging
import time
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import socket
import atexit
import json

class EnhancedDeviceLogger:
    """Enhanced device-specific logger with sensor session tracking and epoch-based naming."""
    
    def __init__(self, device_name: Optional[str] = None, log_base_dir: str = "data/logs"):
        print(f"🔧 Initializing EnhancedDeviceLogger...")
        print(f"   Device name: {device_name}")
        print(f"   Log base dir: {log_base_dir}")
        
        # Fallback to old location if new location doesn't exist and old one does
        if not Path(log_base_dir).exists() and Path("device_logs").exists():
            log_base_dir = "device_logs"
            print(f"   Using fallback log directory: {log_base_dir}")
        
        self.device_name = device_name or self._get_device_name()
        print(f"   Final device name: {self.device_name}")
        
        self.log_base_dir = Path(log_base_dir)
        self.session_start_time = int(time.time())
        
        print(f"   Creating log directory: {self.log_base_dir}")
        # Create base log directory
        try:
            self.log_base_dir.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ Log directory created/verified")
        except Exception as e:
            print(f"   ❌ Failed to create log directory: {e}")
            raise
        
        # Store loggers and their session info
        self._loggers: Dict[str, logging.Logger] = {}
        self._sensor_sessions: Dict[str, Dict] = {}
        self._sensor_handlers: Dict[str, logging.FileHandler] = {}
        
        print(f"   Registering cleanup handler...")
        # Register cleanup on exit
        atexit.register(self._cleanup_all_sessions)
        
        print(f"   Creating main logger...")
        # Setup main device logger
        try:
            self.main_logger = self._create_sensor_logger("main")
            print(f"   ✅ Main logger created successfully")
            self.main_logger.info(f"Enhanced device logger initialized for {self.device_name}")
            print(f"   ✅ Enhanced device logger initialization completed")
        except Exception as e:
            print(f"   ❌ Failed to create main logger: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _get_device_name(self) -> str:
        """Get device name from hostname."""
        try:
            return socket.gethostname().replace('.', '_').replace('-', '_')
        except Exception:
            return "unknown_device"
    
    def _create_sensor_logger(self, sensor_name: str) -> logging.Logger:
        """Create or get logger for a specific sensor with epoch-based naming."""
        print(f"   🔧 Creating sensor logger for: {sensor_name}")
        
        if sensor_name in self._loggers:
            print(f"   ✅ Returning existing logger for: {sensor_name}")
            return self._loggers[sensor_name]
        
        # Record session start time for this sensor
        start_epoch = int(time.time())
        print(f"   📅 Session start epoch: {start_epoch}")
        
        self._sensor_sessions[sensor_name] = {
            'start_time': start_epoch,
            'end_time': None,
            'log_file': None
        }
        
        # Create temporary log file name (will be renamed when session ends)
        temp_log_file = self.log_base_dir / f"{sensor_name}_{start_epoch}_active.log"
        self._sensor_sessions[sensor_name]['log_file'] = temp_log_file
        print(f"   📄 Log file path: {temp_log_file}")
        
        # Create logger
        logger_name = f"{self.device_name}_{sensor_name}_{start_epoch}"
        print(f"   🏷️ Logger name: {logger_name}")
        
        try:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
            print(f"   ✅ Logger object created")
            
            # Prevent duplicate handlers
            if logger.handlers:
                logger.handlers.clear()
                print(f"   🧹 Cleared existing handlers")
            
            # Create file handler
            print(f"   📝 Creating file handler...")
            file_handler = logging.FileHandler(temp_log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            print(f"   ✅ File handler created")
            
            # Create formatter
            print(f"   🎨 Creating formatter...")
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            print(f"   ✅ Formatter applied")
            
            logger.addHandler(file_handler)
            self._loggers[sensor_name] = logger
            self._sensor_handlers[sensor_name] = file_handler
            print(f"   ✅ Handler added to logger")
            
            logger.info(f"Sensor logging session started for {sensor_name}")
            print(f"   ✅ Initial log message written")
            
            return logger
            
        except Exception as e:
            print(f"   ❌ Error creating sensor logger: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_sensor_logger(self, sensor_name: str) -> logging.Logger:
        """Get logger for a specific sensor."""
        return self._create_sensor_logger(sensor_name)
    
    def get_main_logger(self) -> logging.Logger:
        """Get main device logger."""
        return self.main_logger
    
    def log_sensor_data(self, sensor_name: str, level: str, message: str, data: Optional[Dict] = None):
        """Log sensor data with optional structured data."""
        logger = self.get_sensor_logger(sensor_name)
        
        if data:
            message = f"{message} | Data: {json.dumps(data, default=str)}"
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, message)
    
    def log_sensor_error(self, sensor_name: str, error: Exception, context: str = ""):
        """Log sensor error with context."""
        logger = self.get_sensor_logger(sensor_name)
        error_msg = f"ERROR in {context}: {type(error).__name__}: {str(error)}"
        logger.error(error_msg)
    
    def log_sensor_status(self, sensor_name: str, status: Dict):
        """Log sensor status information."""
        logger = self.get_sensor_logger(sensor_name)
        status_msg = f"Status update: {json.dumps(status, default=str)}"
        logger.info(status_msg)
    
    def end_sensor_session(self, sensor_name: str):
        """End logging session for a specific sensor and rename log file."""
        if sensor_name not in self._sensor_sessions:
            return
        
        session = self._sensor_sessions[sensor_name]
        end_epoch = int(time.time())
        session['end_time'] = end_epoch
        
        # Close the current handler
        if sensor_name in self._sensor_handlers:
            handler = self._sensor_handlers[sensor_name]
            logger = self._loggers[sensor_name]
            logger.info(f"Sensor logging session ended for {sensor_name}")
            
            # Remove handler and close it
            logger.removeHandler(handler)
            handler.close()
            
            # Rename log file to final format
            old_file = session['log_file']
            new_file = self.log_base_dir / f"{sensor_name}_{session['start_time']}_{end_epoch}.log"
            
            try:
                if old_file.exists():
                    old_file.rename(new_file)
                    print(f"✅ Renamed log file: {new_file.name}")
            except Exception as e:
                print(f"❌ Failed to rename log file for {sensor_name}: {e}")
            
            # Clean up references
            del self._sensor_handlers[sensor_name]
            del self._loggers[sensor_name]
    
    def end_all_sensor_sessions(self):
        """End all active sensor sessions."""
        active_sensors = list(self._sensor_sessions.keys())
        for sensor_name in active_sensors:
            if self._sensor_sessions[sensor_name]['end_time'] is None:
                self.end_sensor_session(sensor_name)
    
    def _cleanup_all_sessions(self):
        """Cleanup function called on exit."""
        self.end_all_sensor_sessions()
    
    def get_active_sessions(self) -> Dict[str, Dict]:
        """Get information about active logging sessions."""
        active_sessions = {}
        for sensor_name, session in self._sensor_sessions.items():
            if session['end_time'] is None:
                active_sessions[sensor_name] = {
                    'sensor': sensor_name,
                    'start_time': session['start_time'],
                    'start_datetime': datetime.fromtimestamp(session['start_time']).isoformat(),
                    'duration_seconds': int(time.time()) - session['start_time'],
                    'log_file': str(session['log_file'])
                }
        return active_sessions
    
    def get_completed_log_files(self) -> List[Dict]:
        """Get list of completed log files with metadata."""
        completed_logs = []
        
        # Look for completed log files (format: sensorname_startepoch_endepoch.log)
        for log_file in self.log_base_dir.glob("*_*_*.log"):
            if "_active.log" in log_file.name:
                continue
                
            parts = log_file.stem.split('_')
            if len(parts) >= 3:
                try:
                    sensor_name = '_'.join(parts[:-2])  # Handle sensor names with underscores
                    start_epoch = int(parts[-2])
                    end_epoch = int(parts[-1])
                    
                    completed_logs.append({
                        'sensor_name': sensor_name,
                        'start_epoch': start_epoch,
                        'end_epoch': end_epoch,
                        'start_datetime': datetime.fromtimestamp(start_epoch).isoformat(),
                        'end_datetime': datetime.fromtimestamp(end_epoch).isoformat(),
                        'duration_seconds': end_epoch - start_epoch,
                        'file_path': str(log_file),
                        'file_size_bytes': log_file.stat().st_size
                    })
                except (ValueError, IndexError):
                    continue
        
        return sorted(completed_logs, key=lambda x: x['start_epoch'], reverse=True)
    
    def get_logging_summary(self) -> Dict:
        """Get comprehensive logging summary."""
        active_sessions = self.get_active_sessions()
        completed_logs = self.get_completed_log_files()
        
        return {
            'device_name': self.device_name,
            'log_directory': str(self.log_base_dir),
            'session_start_time': self.session_start_time,
            'active_sessions': active_sessions,
            'completed_logs': completed_logs,
            'total_active_sessions': len(active_sessions),
            'total_completed_logs': len(completed_logs),
            'summary_generated_at': datetime.now().isoformat()
        }
    
    def cleanup_old_logs(self, days_to_keep: int = 7):
        """Clean up old log files."""
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        removed_count = 0
        
        for log_file in self.log_base_dir.glob("*.log"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    removed_count += 1
            except Exception as e:
                print(f"Failed to remove old log file {log_file}: {e}")
        
        if removed_count > 0:
            self.main_logger.info(f"Cleaned up {removed_count} old log files")

# Global instance
_enhanced_logger_instance: Optional[EnhancedDeviceLogger] = None

def setup_enhanced_device_logging(device_name: Optional[str] = None, log_base_dir: str = "data/logs") -> EnhancedDeviceLogger:
    """Setup enhanced device logging system."""
    global _enhanced_logger_instance
    
    try:
        print(f"🔧 Setting up enhanced device logging for device: {device_name}")
        print(f"📁 Log base directory: {log_base_dir}")
        
        _enhanced_logger_instance = EnhancedDeviceLogger(device_name, log_base_dir)
        
        if _enhanced_logger_instance is None:
            raise RuntimeError("EnhancedDeviceLogger constructor returned None")
        
        print(f"✅ Enhanced device logging setup completed successfully")
        return _enhanced_logger_instance
        
    except Exception as e:
        print(f"❌ Failed to setup enhanced device logging: {e}")
        print(f"   Device name: {device_name}")
        print(f"   Log base directory: {log_base_dir}")
        import traceback
        traceback.print_exc()
        
        # Return a minimal logger to prevent None errors
        try:
            print("🔄 Attempting to create fallback logger...")
            fallback_logger = EnhancedDeviceLogger("fallback_device", "data/logs/fallback")
            _enhanced_logger_instance = fallback_logger
            print("✅ Fallback logger created successfully")
            return fallback_logger
        except Exception as fallback_error:
            print(f"❌ Failed to create fallback logger: {fallback_error}")
            # Create a minimal mock logger to prevent crashes
            class MockLogger:
                def __init__(self):
                    self.device_name = device_name or "unknown_device"
                
                def get_sensor_logger(self, sensor_name):
                    return self
                
                def get_main_logger(self):
                    return self
                
                def log_sensor_data(self, sensor_name, level, message, data=None):
                    print(f"[MOCK] {sensor_name} {level}: {message}")
                    if data:
                        print(f"[MOCK] Data: {data}")
                
                def log_sensor_error(self, sensor_name, error, context=""):
                    print(f"[MOCK] {sensor_name} ERROR in {context}: {error}")
                
                def end_sensor_session(self, sensor_name):
                    print(f"[MOCK] Ended session for {sensor_name}")
                
                def end_all_sensor_sessions(self):
                    print("[MOCK] Ended all sessions")
                
                def info(self, message):
                    print(f"[MOCK] INFO: {message}")
                
                def warning(self, message):
                    print(f"[MOCK] WARNING: {message}")
                
                def error(self, message):
                    print(f"[MOCK] ERROR: {message}")
                
                def debug(self, message):
                    print(f"[MOCK] DEBUG: {message}")
            
            mock_logger = MockLogger()
            _enhanced_logger_instance = mock_logger
            print("⚠️ Using mock logger as last resort")
            return mock_logger

def get_enhanced_device_logger() -> Optional[EnhancedDeviceLogger]:
    """Get the global enhanced device logger instance."""
    return _enhanced_logger_instance

if __name__ == "__main__":
    # Test the enhanced logging system
    print("Testing Enhanced Device Logger...")
    
    # Setup logger
    logger = setup_enhanced_device_logging("test_device")
    
    # Test different sensors
    sensors = ["camera", "lidar", "environment", "system"]
    
    for sensor in sensors:
        sensor_logger = logger.get_sensor_logger(sensor)
        sensor_logger.info(f"Testing {sensor} sensor logging")
        sensor_logger.warning(f"Test warning for {sensor}")
        
        # Log some test data
        logger.log_sensor_data(sensor, "INFO", f"{sensor} data capture", {
            "timestamp": time.time(),
            "status": "active",
            "value": 42
        })
        
        time.sleep(1)  # Small delay between sensors
    
    # Show active sessions
    print("\nActive Sessions:")
    active = logger.get_active_sessions()
    for sensor, info in active.items():
        print(f"  {sensor}: {info['duration_seconds']}s active")
    
    # End some sessions
    print("\nEnding camera and lidar sessions...")
    logger.end_sensor_session("camera")
    logger.end_sensor_session("lidar")
    
    time.sleep(2)
    
    # End remaining sessions
    print("Ending all remaining sessions...")
    logger.end_all_sensor_sessions()
    
    # Show summary
    print("\nLogging Summary:")
    summary = logger.get_logging_summary()
    print(f"Device: {summary['device_name']}")
    print(f"Active sessions: {summary['total_active_sessions']}")
    print(f"Completed logs: {summary['total_completed_logs']}")
    
    for log in summary['completed_logs']:
        print(f"  {log['sensor_name']}: {log['duration_seconds']}s ({log['file_path']})")