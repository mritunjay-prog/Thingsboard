"""
Logger Factory for Production-Grade Logging

Centralized logging factory with device-specific loggers, rotation,
structured logging, and performance monitoring.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Optional, Any
import json
import time
from datetime import datetime
import threading
from .config_manager import ConfigManager


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def __init__(self, device_id: str = "unknown"):
        super().__init__()
        self.device_id = device_id
    
    def format(self, record):
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "device_id": self.device_id,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_entry["extra"] = record.extra_data
        
        return json.dumps(log_entry)


class PerformanceLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._timers = {}
        self._lock = threading.Lock()
    
    def start_timer(self, operation: str) -> None:
        """Start timing an operation."""
        with self._lock:
            self._timers[operation] = time.time()
    
    def end_timer(self, operation: str, extra_data: Optional[Dict] = None) -> float:
        """End timing and log the duration."""
        with self._lock:
            if operation not in self._timers:
                self.logger.warning(f"Timer for operation '{operation}' was not started")
                return 0.0
            
            duration = time.time() - self._timers[operation]
            del self._timers[operation]
        
        log_data = {
            "operation": operation,
            "duration_seconds": round(duration, 3),
            "performance_metric": True
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        # Log performance data
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"Operation '{operation}' completed in {duration:.3f}s",
            args=(),
            exc_info=None
        )
        record.extra_data = log_data
        self.logger.handle(record)
        
        return duration


class LoggerFactory:
    """
    Production-grade logger factory with device-specific logging,
    rotation, structured logging, and performance monitoring.
    """
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logging_config = config_manager.get_logging_config()
        self.system_config = config_manager.get_system_config()
        self._loggers = {}
        self._lock = threading.Lock()
        
        # Create log directory - use data/logs as default
        log_directory = getattr(self.logging_config, 'log_directory', 'data/logs')
        self.log_dir = Path(log_directory)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup root logger
        self._setup_root_logger()
    
    def _setup_root_logger(self) -> None:
        """Setup the root logger configuration."""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.logging_config.level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(self.logging_config.format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str, sensor_type: Optional[str] = None) -> logging.Logger:
        """
        Get or create a logger with optional sensor-specific configuration.
        
        Args:
            name: Logger name
            sensor_type: Optional sensor type for specialized logging
            
        Returns:
            Configured logger instance
        """
        with self._lock:
            logger_key = f"{name}_{sensor_type}" if sensor_type else name
            
            if logger_key not in self._loggers:
                logger = logging.getLogger(logger_key)
                logger.setLevel(getattr(logging, self.logging_config.level.upper()))
                
                # Clear existing handlers to avoid duplicates
                logger.handlers.clear()
                logger.propagate = False
                
                # Add file handler with rotation
                self._add_file_handler(logger, name, sensor_type)
                
                # Add console handler for important messages
                self._add_console_handler(logger)
                
                self._loggers[logger_key] = logger
            
            return self._loggers[logger_key]
    
    def _add_file_handler(self, logger: logging.Logger, name: str, sensor_type: Optional[str]) -> None:
        """Add rotating file handler to logger."""
        # Determine log file name
        if sensor_type:
            log_filename = f"{self.system_config.device_id}_{sensor_type}_{name}.log"
        else:
            log_filename = f"{self.system_config.device_id}_{name}.log"
        
        log_path = self.log_dir / log_filename
        
        # Parse max file size
        max_bytes = self._parse_file_size(self.logging_config.max_file_size)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=self.logging_config.backup_count
        )
        
        # Use structured formatter for file logs
        if self.system_config.environment == "production":
            formatter = StructuredFormatter(self.system_config.device_id)
        else:
            formatter = logging.Formatter(
                f"%(asctime)s - {self.system_config.device_id} - %(name)s - %(levelname)s - %(message)s"
            )
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    def _add_console_handler(self, logger: logging.Logger) -> None:
        """Add console handler for important messages."""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        
        formatter = logging.Formatter(
            f"%(asctime)s - {self.system_config.device_id} - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
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
            return int(size_str)  # Assume bytes
    
    def get_sensor_logger(self, sensor_name: str) -> logging.Logger:
        """Get a sensor-specific logger."""
        return self.get_logger("sensor", sensor_name)
    
    def get_performance_logger(self, name: str) -> PerformanceLogger:
        """Get a performance logger for timing operations."""
        base_logger = self.get_logger(f"performance_{name}")
        return PerformanceLogger(base_logger)
    
    def get_audit_logger(self) -> logging.Logger:
        """Get audit logger for security and compliance events."""
        audit_logger = self.get_logger("audit")
        audit_logger.setLevel(logging.INFO)  # Audit logs should capture all info
        return audit_logger
    
    def log_system_event(self, event_type: str, message: str, extra_data: Optional[Dict] = None) -> None:
        """Log system-wide events with structured data."""
        system_logger = self.get_logger("system")
        
        log_data = {
            "event_type": event_type,
            "system_event": True,
            "device_id": self.system_config.device_id
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        # Create log record with extra data
        record = logging.LogRecord(
            name=system_logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.extra_data = log_data
        system_logger.handle(record)
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> None:
        """Clean up log files older than specified days."""
        import time
        
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        cleaned_count = 0
        
        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Failed to delete old log {log_file}: {e}")
        
        if cleaned_count > 0:
            self.log_system_event(
                "log_cleanup",
                f"Cleaned up {cleaned_count} old log files",
                {"files_cleaned": cleaned_count, "days_to_keep": days_to_keep}
            )
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get statistics about current logging."""
        stats = {
            "log_directory": str(self.log_dir),
            "active_loggers": len(self._loggers),
            "log_files": [],
            "total_log_size_mb": 0
        }
        
        total_size = 0
        for log_file in self.log_dir.glob("*.log*"):
            file_size = log_file.stat().st_size
            total_size += file_size
            
            stats["log_files"].append({
                "name": log_file.name,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            })
        
        stats["total_log_size_mb"] = round(total_size / (1024 * 1024), 2)
        return stats