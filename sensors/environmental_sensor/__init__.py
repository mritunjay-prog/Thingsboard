"""
Environmental Sensor Module
Provides comprehensive environmental monitoring including environment conditions,
air quality measurements, and light level monitoring.
"""

from .environment_conditions import EnvironmentConditionsService
from .air_quality_monitor import AirQualityMonitorService  
from .light_level_monitor import LightLevelMonitorService
from .environmental_manager import (
    EnvironmentalManager,
    get_environmental_manager,
    timed_environmental_capture,
    estimate_environmental_capture_session
)

# Global service instances
_environment_conditions_service = None
_air_quality_monitor_service = None
_light_level_monitor_service = None

def get_environment_conditions_service():
    """Get the global environment conditions service instance"""
    global _environment_conditions_service
    if _environment_conditions_service is None:
        _environment_conditions_service = EnvironmentConditionsService()
    return _environment_conditions_service

def get_air_quality_monitor_service():
    """Get the global air quality monitor service instance"""
    global _air_quality_monitor_service
    if _air_quality_monitor_service is None:
        _air_quality_monitor_service = AirQualityMonitorService()
    return _air_quality_monitor_service

def get_light_level_monitor_service():
    """Get the global light level monitor service instance"""
    global _light_level_monitor_service
    if _light_level_monitor_service is None:
        _light_level_monitor_service = LightLevelMonitorService()
    return _light_level_monitor_service

# Export key functions
__all__ = [
    'get_environment_conditions_service',
    'get_air_quality_monitor_service', 
    'get_light_level_monitor_service',
    'EnvironmentConditionsService',
    'AirQualityMonitorService',
    'LightLevelMonitorService',
    'EnvironmentalManager',
    'get_environmental_manager',
    'timed_environmental_capture',
    'estimate_environmental_capture_session'
]
