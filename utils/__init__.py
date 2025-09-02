"""
IoT Sensor Management Utilities - Production Grade Package

This package provides comprehensive utilities for managing IoT sensors and devices
with enterprise-level features including logging, monitoring, and reporting.
"""

__version__ = "1.0.0"
__author__ = "IoT Development Team"

# Import all utility classes for easy access
from .sensor_manager import SensorManager
from .diagnostics_utils import DiagnosticsUtils
from .config_manager import ConfigManager
from .logger_factory import LoggerFactory
from .unified_logger import UnifiedLogger, setup_unified_logger, get_unified_logger

# Export main classes
__all__ = [
    'SensorManager',
    'DiagnosticsUtils',
    'ConfigManager',
    'LoggerFactory',
    'UnifiedLogger',
    'setup_unified_logger',
    'get_unified_logger'
]

# Package-level configuration
DEFAULT_CONFIG = {
    'logging': {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'max_file_size': '10MB',
        'backup_count': 5
    },
    'sensors': {
        'timeout_seconds': 30,
        'retry_attempts': 3,
        'health_check_interval': 300
    },
    'network': {
        'connection_timeout': 10,
        'read_timeout': 30,
        'max_retries': 3
    }
}

def get_version():
    """Get package version."""
    return __version__

def initialize_package(config_path=None):
    """Initialize the package with configuration."""
    config_manager = ConfigManager(config_path)
    logger_factory = LoggerFactory(config_manager)
    
    return {
        'config_manager': config_manager,
        'logger_factory': logger_factory,
        'version': __version__
    }