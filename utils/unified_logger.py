"""
Unified Production-Grade Logging System

This module consolidates all logging functionality from enhanced_device_logger.py,
streaming_logger.py, device_logger.py, and logger_factory.py into a single,
comprehensive logging solution with all features.
"""

import logging
import logging.handlers
import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import queue
import atexit

from .config_manager import ConfigManager


@dataclass
class LogEntry:
    """Structured log entry for enhanced logging."""
    timestamp: str
    level: str
    logger_name: str
    device_id: str
    sensor_name: Optional[str]
    message: str
    module: str
    function: str
    line: int
    extra_data: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    stream_id: Optional[str] = None
    performance_data: Optional[Dict[str, Any]] = None


class AsyncLogHandler(logging.Handler):
    """Asynchronous log handler for high-performance logging."""
    
    def __init__(self, target_handler: logging.Handler, queue_size: int = 1000):
        super().__init__()
        self.target_handler = target_handler
        self.log_queue = queue.Queue(maxsize=queue_size)
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.shutdown_event = threading.Event()
        self.worker_thread.start()
        
        # Register cleanup on exit
        atexit.register(self.close)
    
    def emit(self, record):
        """Add log record to queue for async processing."""
        try:
            self.log_queue.put_nowait(record)
        except queue.Full:
            # Drop oldest record if queue is full
            try:
                self.log_queue.get_nowait()
                self.log_queue.put_nowait(record)
            except queue.Empty:
                pass
    
    def _worker(self):
        """Worker thread to process log records."""
        while not self.shutdown_event.is_set():
            try:
                record = self.log_queue.get(timeout=1.0)
                self.target_handler.emit(record)
                self.log_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Async log handler error: {e}")
    
    def close(self):
        """Close the async handler and wait for queue to empty."""
        self.shutdown_event.set()
        
        # Process remaining items
        while not self.log_queue.empty():
            try:
                record = self.log_queue.get_nowait()
                self.target_handler.emit(record)
            except queue.Empty:
                break
        
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
        
        self.target_handler.close()
        super().close()


class StructuredJSONFormatter(logging.Formatter):
    """Enhanced JSON formatter with all structured data support."""
    
    def __init__(self, device_id: str = "unknown"):
        super().__init__()
        self.device_id = device_id
    
    def format(self, record):
        """Format log record as comprehensive structured JSON."""
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created).isoformat(),
            level=record.levelname,
            logger_name=record.name,
            device_id=self.device_id,
            sensor_name=getattr(record, 'sensor_name', None),
            message=record.getMessage(),
            module=record.module,
            function=record.funcName,
            line=record.lineno,
            extra_data=getattr(record, 'extra_data', None),
            session_id=getattr(record, 'session_id', None),
            stream_id=getattr(record, 'stream_id', None),
            performance_data=getattr(record, 'performance_data', None)
        )
        
        # Add exception info if present
        if record.exc_info:
            log_entry.extra_data = log_entry.extra_data or {}
            log_entry.extra_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(asdict(log_entry), default=str)


class PerformanceTracker:
    """Enhanced performance tracking with detailed metrics."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._timers = {}
        self._metrics = {}
        self._lock = threading.Lock()
    
    def start_timer(self, operation: str, context: Optional[Dict] = None) -> str:
        """Start timing an operation with optional context."""
        timer_id = f"{operation}_{int(time.time() * 1000000)}"
        
        with self._lock:
            self._timers[timer_id] = {
                "operation": operation,
                "start_time": time.time(),
                "context": context or {}
            }
        
        return timer_id
    
    def end_timer(self, timer_id: str, extra_data: Optional[Dict] = None) -> float:
        """End timing and log performance data."""
        with self._lock:
            if timer_id not in self._timers:
                self.logger.warning(f"Timer {timer_id} was not found")
                return 0.0
            
            timer_data = self._timers[timer_id]
            duration = time.time() - timer_data["start_time"]
            del self._timers[timer_id]
        
        # Update metrics
        operation = timer_data["operation"]
        if operation not in self._metrics:
            self._metrics[operation] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0,
                "avg_time": 0.0
            }
        
        metrics = self._metrics[operation]
        metrics["count"] += 1
        metrics["total_time"] += duration
        metrics["min_time"] = min(metrics["min_time"], duration)
        metrics["max_time"] = max(metrics["max_time"], duration)
        metrics["avg_time"] = metrics["total_time"] / metrics["count"]
        
        # Log performance data
        performance_data = {
            "operation": operation,
            "duration_seconds": round(duration, 3),
            "metrics": metrics.copy(),
            "context": timer_data["context"]
        }
        
        if extra_data:
            performance_data.update(extra_data)
        
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"Operation '{operation}' completed in {duration:.3f}s",
            args=(),
            exc_info=None
        )
        record.performance_data = performance_data
        self.logger.handle(record)
        
        return duration
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            return self._metrics.copy()


class SessionManager:
    """Manage logging sessions for sensors and streams."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.active_sessions = {}
        self.session_history = []
        self._lock = threading.Lock()
    
    def start_session(self, session_type: str, session_id: str, 
                     metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Start a new logging session."""
        session_data = {
            "session_id": session_id,
            "session_type": session_type,
            "start_time": time.time(),
            "start_timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "log_count": 0,
            "error_count": 0,
            "warning_count": 0
        }
        
        with self._lock:
            self.active_sessions[session_id] = session_data
        
        self.logger.info(f"Started {session_type} session: {session_id}", extra={
            "session_id": session_id,
            "session_type": session_type,
            "metadata": metadata
        })
        
        return session_data
    
    def end_session(self, session_id: str, final_data: Optional[Dict] = None) -> Dict[str, Any]:
        """End a logging session."""
        with self._lock:
            if session_id not in self.active_sessions:
                self.logger.warning(f"Session {session_id} not found")
                return {}
            
            session_data = self.active_sessions[session_id]
            session_data["end_time"] = time.time()
            session_data["end_timestamp"] = datetime.now().isoformat()
            session_data["duration_seconds"] = session_data["end_time"] - session_data["start_time"]
            
            if final_data:
                session_data["final_data"] = final_data
            
            # Move to history
            self.session_history.append(session_data.copy())
            del self.active_sessions[session_id]
        
        self.logger.info(f"Ended session: {session_id}", extra={
            "session_id": session_id,
            "duration_seconds": session_data["duration_seconds"],
            "final_data": final_data
        })
        
        return session_data
    
    def log_to_session(self, session_id: str, level: str, message: str, 
                      extra_data: Optional[Dict] = None) -> None:
        """Log a message to a specific session."""
        with self._lock:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session["log_count"] += 1
                
                if level == "ERROR":
                    session["error_count"] += 1
                elif level == "WARNING":
                    session["warning_count"] += 1
        
        # Create log record with session context
        record = logging.LogRecord(
            name=self.logger.name,
            level=getattr(logging, level),
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.session_id = session_id
        record.extra_data = extra_data
        
        self.logger.handle(record)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        with self._lock:
            return {
                "active_sessions": len(self.active_sessions),
                "total_sessions": len(self.session_history),
                "session_details": {
                    "active": list(self.active_sessions.keys()),
                    "recent_completed": [
                        s["session_id"] for s in self.session_history[-10:]
                    ]
                }
            }


class UnifiedLogger:
    """
    Unified production-grade logger combining all logging functionality
    from enhanced_device_logger, streaming_logger, device_logger, and logger_factory.
    """
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logging_config = config_manager.get_logging_config()
        self.system_config = config_manager.get_system_config()
        
        # Core components
        self._loggers = {}
        self._performance_trackers = {}
        self._session_managers = {}
        self._lock = threading.Lock()
        
        # Create log directory
        self.log_dir = Path(self.logging_config.log_directory)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize main logger
        self.main_logger = self._create_main_logger()
        
        # Setup root logger
        self._setup_root_logger()
        
        # Cleanup thread
        self._start_cleanup_thread()
    
    def _create_main_logger(self) -> logging.Logger:
        """Create the main system logger."""
        logger = logging.getLogger(f"unified_{self.system_config.device_id}")
        logger.setLevel(getattr(logging, self.logging_config.level.upper()))
        logger.handlers.clear()
        logger.propagate = False
        
        # Add file handler
        log_file = self.log_dir / f"{self.system_config.device_id}_main.log"
        file_handler = self._create_rotating_handler(log_file)
        file_handler.setFormatter(StructuredJSONFormatter(self.system_config.device_id))
        
        # Use async handler for performance
        async_handler = AsyncLogHandler(file_handler)
        logger.addHandler(async_handler)
        
        # Add console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter(
            f"%(asctime)s - {self.system_config.device_id} - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _create_rotating_handler(self, log_file: Path) -> logging.handlers.RotatingFileHandler:
        """Create a rotating file handler."""
        max_bytes = self._parse_file_size(self.logging_config.max_file_size)
        
        return logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=self.logging_config.backup_count
        )
    
    def _parse_file_size(self, size_str: str) -> int:
        """Parse file size string to bytes."""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def _setup_root_logger(self) -> None:
        """Setup root logger configuration."""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.logging_config.level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(self.logging_config.format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str, sensor_type: Optional[str] = None) -> logging.Logger:
        """Get or create a logger with optional sensor-specific configuration."""
        with self._lock:
            logger_key = f"{name}_{sensor_type}" if sensor_type else name
            
            if logger_key not in self._loggers:
                logger = logging.getLogger(f"{self.system_config.device_id}_{logger_key}")
                logger.setLevel(getattr(logging, self.logging_config.level.upper()))
                logger.handlers.clear()
                logger.propagate = False
                
                # Create log file
                if sensor_type:
                    log_filename = f"{self.system_config.device_id}_{sensor_type}_{name}.log"
                else:
                    log_filename = f"{self.system_config.device_id}_{name}.log"
                
                log_file = self.log_dir / log_filename
                file_handler = self._create_rotating_handler(log_file)
                
                # Use structured formatter for production
                if self.system_config.environment == "production":
                    formatter = StructuredJSONFormatter(self.system_config.device_id)
                else:
                    formatter = logging.Formatter(
                        f"%(asctime)s - {self.system_config.device_id} - %(name)s - %(levelname)s - %(message)s"
                    )
                
                file_handler.setFormatter(formatter)
                
                # Use async handler for performance
                async_handler = AsyncLogHandler(file_handler)
                logger.addHandler(async_handler)
                
                # Add console handler for warnings and errors
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.WARNING)
                console_formatter = logging.Formatter(
                    f"%(asctime)s - {self.system_config.device_id} - %(levelname)s - %(message)s"
                )
                console_handler.setFormatter(console_formatter)
                logger.addHandler(console_handler)
                
                self._loggers[logger_key] = logger
            
            return self._loggers[logger_key]
    
    def get_sensor_logger(self, sensor_name: str) -> logging.Logger:
        """Get a sensor-specific logger."""
        return self.get_logger("sensor", sensor_name)
    
    def get_performance_tracker(self, name: str) -> PerformanceTracker:
        """Get a performance tracker for timing operations."""
        if name not in self._performance_trackers:
            base_logger = self.get_logger(f"performance_{name}")
            self._performance_trackers[name] = PerformanceTracker(base_logger)
        
        return self._performance_trackers[name]
    
    def get_session_manager(self, name: str) -> SessionManager:
        """Get a session manager for managing logging sessions."""
        if name not in self._session_managers:
            base_logger = self.get_logger(f"session_{name}")
            self._session_managers[name] = SessionManager(base_logger)
        
        return self._session_managers[name]
    
    def get_audit_logger(self) -> logging.Logger:
        """Get audit logger for security and compliance events."""
        audit_logger = self.get_logger("audit")
        audit_logger.setLevel(logging.INFO)
        return audit_logger
    
    def log_system_event(self, event_type: str, message: str, 
                        extra_data: Optional[Dict] = None) -> None:
        """Log system-wide events with structured data."""
        log_data = {
            "event_type": event_type,
            "system_event": True,
            "device_id": self.system_config.device_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        record = logging.LogRecord(
            name=self.main_logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.extra_data = log_data
        self.main_logger.handle(record)
    
    def log_sensor_data(self, sensor_name: str, level: str, message: str, 
                       data: Optional[Dict] = None) -> None:
        """Log sensor-specific data with structured format."""
        sensor_logger = self.get_sensor_logger(sensor_name)
        
        log_data = {
            "sensor_name": sensor_name,
            "sensor_data": True,
            "timestamp": datetime.now().isoformat()
        }
        
        if data:
            log_data.update(data)
        
        record = logging.LogRecord(
            name=sensor_logger.name,
            level=getattr(logging, level.upper()),
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.sensor_name = sensor_name
        record.extra_data = log_data
        sensor_logger.handle(record)
    
    def log_sensor_error(self, sensor_name: str, error: Exception, 
                        context: str = "") -> None:
        """Log sensor errors with full context."""
        sensor_logger = self.get_sensor_logger(sensor_name)
        
        error_data = {
            "sensor_name": sensor_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
        record = logging.LogRecord(
            name=sensor_logger.name,
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg=f"Sensor error in {context}: {str(error)}",
            args=(),
            exc_info=(type(error), error, error.__traceback__)
        )
        record.sensor_name = sensor_name
        record.extra_data = error_data
        sensor_logger.handle(record)
    
    def start_sensor_session(self, sensor_name: str, session_params: Dict[str, Any]) -> str:
        """Start a sensor logging session."""
        session_manager = self.get_session_manager(sensor_name)
        session_id = f"{sensor_name}_{int(time.time() * 1000)}"
        
        session_manager.start_session("sensor", session_id, session_params)
        return session_id
    
    def end_sensor_session(self, sensor_name: str, session_id: str, 
                          final_data: Optional[Dict] = None) -> None:
        """End a sensor logging session."""
        if sensor_name in self._session_managers:
            session_manager = self._session_managers[sensor_name]
            session_manager.end_session(session_id, final_data)
    
    def start_stream_session(self, stream_id: str, stream_params: Dict[str, Any]) -> logging.Logger:
        """Start a streaming session with dedicated logger."""
        session_manager = self.get_session_manager("streaming")
        session_manager.start_session("stream", stream_id, stream_params)
        
        # Create dedicated stream logger
        stream_logger = self.get_logger(f"stream_{stream_id}")
        return stream_logger
    
    def log_stream_data(self, stream_id: str, level: str, message: str, 
                       data: Optional[Dict] = None) -> None:
        """Log streaming-specific data."""
        stream_logger = self.get_logger(f"stream_{stream_id}")
        
        log_data = {
            "stream_id": stream_id,
            "stream_data": True,
            "timestamp": datetime.now().isoformat()
        }
        
        if data:
            log_data.update(data)
        
        record = logging.LogRecord(
            name=stream_logger.name,
            level=getattr(logging, level.upper()),
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.stream_id = stream_id
        record.extra_data = log_data
        stream_logger.handle(record)
    
    def get_completed_log_files(self) -> List[Dict[str, Any]]:
        """Get list of completed log files with metadata."""
        completed_logs = []
        
        for log_file in self.log_dir.glob("*.log"):
            if "_active.log" in log_file.name:
                continue
            
            try:
                stat = log_file.stat()
                completed_logs.append({
                    'file_path': str(log_file),
                    'file_name': log_file.name,
                    'file_size_bytes': stat.st_size,
                    'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'device_id': self.system_config.device_id
                })
            except (OSError, ValueError):
                continue
        
        return sorted(completed_logs, key=lambda x: x['modified_time'], reverse=True)
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> None:
        """Clean up log files older than specified days."""
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        cleaned_count = 0
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    cleaned_count += 1
            except Exception as e:
                self.main_logger.warning(f"Failed to delete old log {log_file}: {e}")
        
        if cleaned_count > 0:
            self.log_system_event(
                "log_cleanup",
                f"Cleaned up {cleaned_count} old log files",
                {"files_cleaned": cleaned_count, "days_to_keep": days_to_keep}
            )
    
    def _start_cleanup_thread(self) -> None:
        """Start background thread for periodic cleanup."""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(24 * 60 * 60)  # Run daily
                    self.cleanup_old_logs()
                except Exception as e:
                    self.main_logger.error(f"Cleanup thread error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get comprehensive logging statistics."""
        stats = {
            "log_directory": str(self.log_dir),
            "active_loggers": len(self._loggers),
            "performance_trackers": len(self._performance_trackers),
            "session_managers": len(self._session_managers),
            "log_files": [],
            "total_log_size_mb": 0,
            "session_stats": {}
        }
        
        # File statistics
        total_size = 0
        for log_file in self.log_dir.glob("*.log*"):
            try:
                file_size = log_file.stat().st_size
                total_size += file_size
                
                stats["log_files"].append({
                    "name": log_file.name,
                    "size_mb": round(file_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                })
            except OSError:
                continue
        
        stats["total_log_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        # Session statistics
        for name, session_manager in self._session_managers.items():
            stats["session_stats"][name] = session_manager.get_session_stats()
        
        # Performance statistics
        performance_stats = {}
        for name, tracker in self._performance_trackers.items():
            performance_stats[name] = tracker.get_metrics()
        stats["performance_stats"] = performance_stats
        
        return stats
    
    def shutdown(self) -> None:
        """Graceful shutdown of the logging system."""
        self.log_system_event("logger_shutdown", "Unified logger shutting down")
        
        # Close all handlers
        for logger in self._loggers.values():
            for handler in logger.handlers:
                handler.close()
        
        # Close main logger handlers
        for handler in self.main_logger.handlers:
            handler.close()


# Global instance management
_unified_logger_instance = None


def setup_unified_logger(config_manager: ConfigManager) -> UnifiedLogger:
    """Setup the global unified logger instance."""
    global _unified_logger_instance
    _unified_logger_instance = UnifiedLogger(config_manager)
    return _unified_logger_instance


def get_unified_logger() -> Optional[UnifiedLogger]:
    """Get the global unified logger instance."""
    return _unified_logger_instance


# Convenience functions for backward compatibility
def get_device_logger(sensor_name: str) -> Optional[logging.Logger]:
    """Get device logger for backward compatibility."""
    if _unified_logger_instance:
        return _unified_logger_instance.get_sensor_logger(sensor_name)
    return None


def get_enhanced_device_logger() -> Optional[UnifiedLogger]:
    """Get enhanced device logger for backward compatibility."""
    return _unified_logger_instance


def get_streaming_logger() -> Optional[UnifiedLogger]:
    """Get streaming logger for backward compatibility."""
    return _unified_logger_instance


def get_logger(name: str) -> Optional[logging.Logger]:
    """Get logger using the unified logging system."""
    unified_logger = get_unified_logger()
    if unified_logger:
        return unified_logger.get_logger(name)
    return None