#!/usr/bin/env python3

"""
Environmental Manager Service

This module provides unified timed capture functionality for all environmental sensors:
- Environment conditions (temperature, humidity, pressure)
- Air quality monitoring (PM2.5, CO2, VOC, AQI)
- Light level monitoring (ambient light, UV index)
"""

import time
import threading
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from .environment_conditions import EnvironmentConditionsService
from .air_quality_monitor import AirQualityMonitorService
from .light_level_monitor import LightLevelMonitorService


class EnvironmentalManager:
    """
    Manager class that orchestrates timed capture across all environmental sensors.
    """
    
    def __init__(self):
        """Initialize the environmental manager with all sensor services."""
        self.environment_service = EnvironmentConditionsService()
        self.air_quality_service = AirQualityMonitorService()
        self.light_level_service = LightLevelMonitorService()
        
        print("🌍 Environmental Manager initialized with all sensor services")
    
    def timed_environmental_capture(
        self,
        capture_duration_seconds: int,
        sample_rate_hz: float,
        save_location: str,
        device_id: str = None,
        stop_event: threading.Event = None,
        capture_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Perform timed environmental data capture for all sensors.
        
        This method captures data from environment conditions, air quality, and light level
        sensors at the specified sample rate for the given duration and saves separate 
        JSON files for each sensor type.
        
        Args:
            capture_duration_seconds (int): Total duration to capture data (in seconds)
            sample_rate_hz (float): Sample rate in Hz (how frequently to capture data)
            save_location (str): Directory path where telemetry JSON files should be saved
            device_id (str, optional): Device identifier for file naming
            stop_event (threading.Event, optional): Event to signal early termination
            capture_params (dict, optional): Additional environmental capture parameters
            
        Returns:
            dict: Results containing captured environmental data information
                {
                    "success": bool,
                    "samples_captured": int,
                    "environment_files": List[str],
                    "air_quality_files": List[str],
                    "light_level_files": List[str],
                    "total_files": List[str],
                    "capture_duration_actual": float,
                    "sample_rate_actual": float,
                    "sensor_statistics": Dict[str, Any],
                    "error": str (if success=False)
                }
        """
        
        print(f"🌍 Starting timed environmental capture session")
        print(f"   Sample rate: {sample_rate_hz}Hz")
        print(f"   Duration: {capture_duration_seconds}s")
        print(f"   Save location: {save_location}")
        
        # Validate sample rate
        if not (0.1 <= sample_rate_hz <= 60.0):  # Environmental sensors typically slower
            return {
                "success": False,
                "error": f"Invalid sample rate: {sample_rate_hz}Hz. Must be between 0.1 and 60.0 Hz",
                "samples_captured": 0,
                "environment_files": [],
                "air_quality_files": [],
                "light_level_files": [],
                "total_files": [],
                "capture_duration_actual": 0.0,
                "sample_rate_actual": 0.0,
                "sensor_statistics": {}
            }
        
        # Initialize results
        results = {
            "success": False,
            "samples_captured": 0,
            "environment_files": [],
            "air_quality_files": [],
            "light_level_files": [],
            "total_files": [],
            "capture_duration_actual": 0.0,
            "sample_rate_actual": 0.0,
            "sensor_statistics": {},
            "error": None
        }
        
        try:
            # Setup save directory
            save_dir = Path(save_location)
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # Default capture parameters
            default_params = {
                "environment": {
                    "sample_interval_seconds": 1.0 / sample_rate_hz,
                    "enable_data_saving": True
                },
                "air_quality": {
                    "sample_interval_seconds": 1.0 / sample_rate_hz,
                    "enable_data_saving": True
                },
                "light_level": {
                    "sample_interval_seconds": 1.0 / sample_rate_hz,
                    "enable_data_saving": True
                }
            }
            
            # Merge with user-provided parameters
            if capture_params:
                for sensor_type in default_params:
                    if sensor_type in capture_params:
                        default_params[sensor_type].update(capture_params[sensor_type])
            
            # Store original states to restore later
            env_was_monitoring = self.environment_service.is_monitoring
            air_was_monitoring = self.air_quality_service.is_monitoring
            light_was_monitoring = self.light_level_service.is_monitoring
            
            # Start monitoring services if not already active
            services_started = []
            
            if not env_was_monitoring:
                env_result = self.environment_service.start_monitoring(
                    interval_seconds=int(default_params["environment"]["sample_interval_seconds"])
                )
                if env_result.get("success", False):
                    services_started.append("environment")
                    print(f"✅ Environment conditions monitoring started")
                else:
                    print(f"⚠️ Failed to start environment monitoring: {env_result.get('message', 'Unknown error')}")
            
            if not air_was_monitoring:
                air_result = self.air_quality_service.start_monitoring(
                    interval_seconds=int(default_params["air_quality"]["sample_interval_seconds"])
                )
                if air_result.get("success", False):
                    services_started.append("air_quality")
                    print(f"✅ Air quality monitoring started")
                else:
                    print(f"⚠️ Failed to start air quality monitoring: {air_result.get('message', 'Unknown error')}")
            
            if not light_was_monitoring:
                light_result = self.light_level_service.start_monitoring(
                    interval_seconds=int(default_params["light_level"]["sample_interval_seconds"])
                )
                if light_result.get("success", False):
                    services_started.append("light_level")
                    print(f"✅ Light level monitoring started")
                else:
                    print(f"⚠️ Failed to start light level monitoring: {light_result.get('message', 'Unknown error')}")
            
            # Calculate timing
            sample_interval = 1.0 / sample_rate_hz
            expected_samples = int(capture_duration_seconds * sample_rate_hz)
            
            print(f"📊 Capture plan:")
            print(f"   Sample rate: {sample_rate_hz}Hz")
            print(f"   Sample interval: {sample_interval:.3f}s")
            print(f"   Expected samples: {expected_samples}")
            print(f"   Active services: {len(services_started) + (3 - len(services_started))} total")
            
            # Track timing and data
            start_time = time.time()
            environment_files = []
            air_quality_files = []
            light_level_files = []
            
            # Statistics tracking
            sensor_stats = {
                "environment": {"samples": 0, "avg_temp": 0, "avg_humidity": 0},
                "air_quality": {"samples": 0, "avg_aqi": 0, "avg_pm25": 0},
                "light_level": {"samples": 0, "avg_lux": 0, "avg_uv": 0}
            }
            
            sample_count = 0
            while True:
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Check if we should stop
                if elapsed_time >= capture_duration_seconds:
                    print(f"⏰ Capture duration reached: {elapsed_time:.2f}s")
                    break
                    
                if stop_event and stop_event.is_set():
                    print(f"🛑 Stop event triggered at {elapsed_time:.2f}s")
                    break
                
                try:
                    sample_count += 1
                    timestamp = int(time.time() * 1000)
                    
                    # Capture environment conditions data
                    try:
                        env_data = self.environment_service.get_telemetry_data()
                        if env_data and "values" in env_data:
                            env_filename = f"environment_telemetry_{timestamp}.json"
                            env_path = save_dir / env_filename
                            
                            env_entry = {
                                "timestamp": time.time(),
                                "readable_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "device_id": device_id,
                                "sample_number": sample_count,
                                "sample_rate_hz": sample_rate_hz,
                                "sensor_type": "environment_conditions",
                                "data": env_data
                            }
                            
                            with open(env_path, 'w') as f:
                                json.dump(env_entry, f, indent=2)
                            
                            environment_files.append(str(env_path))
                            
                            # Update statistics
                            values = env_data.get("values", {})
                            temp = values.get("environment.temperature_c", 0)
                            humidity = values.get("environment.humidity_percent", 0)
                            sensor_stats["environment"]["samples"] += 1
                            sensor_stats["environment"]["avg_temp"] = (
                                (sensor_stats["environment"]["avg_temp"] * (sensor_stats["environment"]["samples"] - 1) + temp) /
                                sensor_stats["environment"]["samples"]
                            )
                            sensor_stats["environment"]["avg_humidity"] = (
                                (sensor_stats["environment"]["avg_humidity"] * (sensor_stats["environment"]["samples"] - 1) + humidity) /
                                sensor_stats["environment"]["samples"]
                            )
                            
                    except Exception as env_error:
                        print(f"❌ Environment capture error: {env_error}")
                    
                    # Capture air quality data
                    try:
                        air_data = self.air_quality_service.get_telemetry_data()
                        if air_data and "values" in air_data:
                            air_filename = f"air_quality_telemetry_{timestamp}.json"
                            air_path = save_dir / air_filename
                            
                            air_entry = {
                                "timestamp": time.time(),
                                "readable_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "device_id": device_id,
                                "sample_number": sample_count,
                                "sample_rate_hz": sample_rate_hz,
                                "sensor_type": "air_quality",
                                "data": air_data
                            }
                            
                            with open(air_path, 'w') as f:
                                json.dump(air_entry, f, indent=2)
                            
                            air_quality_files.append(str(air_path))
                            
                            # Update statistics
                            values = air_data.get("values", {})
                            aqi = values.get("air_quality.aqi", 0)
                            pm25 = values.get("air_quality.pm2_5_ugm3", 0)
                            sensor_stats["air_quality"]["samples"] += 1
                            sensor_stats["air_quality"]["avg_aqi"] = (
                                (sensor_stats["air_quality"]["avg_aqi"] * (sensor_stats["air_quality"]["samples"] - 1) + aqi) /
                                sensor_stats["air_quality"]["samples"]
                            )
                            sensor_stats["air_quality"]["avg_pm25"] = (
                                (sensor_stats["air_quality"]["avg_pm25"] * (sensor_stats["air_quality"]["samples"] - 1) + pm25) /
                                sensor_stats["air_quality"]["samples"]
                            )
                            
                    except Exception as air_error:
                        print(f"❌ Air quality capture error: {air_error}")
                    
                    # Capture light level data
                    try:
                        light_data = self.light_level_service.get_telemetry_data()
                        if light_data and "values" in light_data:
                            light_filename = f"light_level_telemetry_{timestamp}.json"
                            light_path = save_dir / light_filename
                            
                            light_entry = {
                                "timestamp": time.time(),
                                "readable_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "device_id": device_id,
                                "sample_number": sample_count,
                                "sample_rate_hz": sample_rate_hz,
                                "sensor_type": "light_level",
                                "data": light_data
                            }
                            
                            with open(light_path, 'w') as f:
                                json.dump(light_entry, f, indent=2)
                            
                            light_level_files.append(str(light_path))
                            
                            # Update statistics
                            values = light_data.get("values", {})
                            lux = values.get("light.ambient_lux", 0)
                            uv = values.get("light.uv_index", 0)
                            sensor_stats["light_level"]["samples"] += 1
                            sensor_stats["light_level"]["avg_lux"] = (
                                (sensor_stats["light_level"]["avg_lux"] * (sensor_stats["light_level"]["samples"] - 1) + lux) /
                                sensor_stats["light_level"]["samples"]
                            )
                            sensor_stats["light_level"]["avg_uv"] = (
                                (sensor_stats["light_level"]["avg_uv"] * (sensor_stats["light_level"]["samples"] - 1) + uv) /
                                sensor_stats["light_level"]["samples"]
                            )
                            
                    except Exception as light_error:
                        print(f"❌ Light level capture error: {light_error}")
                    
                    # Progress logging
                    if sample_count % 10 == 0:
                        print(f"🌍 Environmental: {sample_count} samples captured")
                        print(f"   Files: Env({len(environment_files)}) Air({len(air_quality_files)}) Light({len(light_level_files)})")
                    
                except Exception as sample_error:
                    print(f"❌ Environmental sample error: {sample_error}")
                
                # Wait for next sample
                time.sleep(sample_interval)
            
            # Calculate final results
            end_time = time.time()
            results["capture_duration_actual"] = end_time - start_time
            results["samples_captured"] = sample_count
            results["environment_files"] = environment_files
            results["air_quality_files"] = air_quality_files
            results["light_level_files"] = light_level_files
            results["total_files"] = environment_files + air_quality_files + light_level_files
            results["sample_rate_actual"] = round(sample_count / results["capture_duration_actual"], 2) if results["capture_duration_actual"] > 0 else 0.0
            results["sensor_statistics"] = {
                "environment": {
                    "samples": sensor_stats["environment"]["samples"],
                    "avg_temperature_c": round(sensor_stats["environment"]["avg_temp"], 1),
                    "avg_humidity_percent": round(sensor_stats["environment"]["avg_humidity"], 1)
                },
                "air_quality": {
                    "samples": sensor_stats["air_quality"]["samples"],
                    "avg_aqi": round(sensor_stats["air_quality"]["avg_aqi"], 1),
                    "avg_pm25_ugm3": round(sensor_stats["air_quality"]["avg_pm25"], 1)
                },
                "light_level": {
                    "samples": sensor_stats["light_level"]["samples"],
                    "avg_ambient_lux": round(sensor_stats["light_level"]["avg_lux"], 1),
                    "avg_uv_index": round(sensor_stats["light_level"]["avg_uv"], 1)
                }
            }
            results["success"] = True
            
            print(f"✅ Timed environmental capture completed:")
            print(f"   Total samples: {results['samples_captured']}")
            print(f"   Environment files: {len(environment_files)}")
            print(f"   Air quality files: {len(air_quality_files)}")
            print(f"   Light level files: {len(light_level_files)}")
            print(f"   Total files: {len(results['total_files'])}")
            print(f"   Actual sample rate: {results['sample_rate_actual']}Hz")
            print(f"   Actual duration: {results['capture_duration_actual']:.2f}s")
            print(f"   Files saved to: {save_dir}")
            
            # Restore original monitoring states
            if "environment" in services_started and not env_was_monitoring:
                self.environment_service.stop_monitoring()
                print(f"🔄 Stopped environment monitoring (was not originally active)")
            
            if "air_quality" in services_started and not air_was_monitoring:
                self.air_quality_service.stop_monitoring()
                print(f"🔄 Stopped air quality monitoring (was not originally active)")
            
            if "light_level" in services_started and not light_was_monitoring:
                self.light_level_service.stop_monitoring()
                print(f"🔄 Stopped light level monitoring (was not originally active)")
            
        except Exception as e:
            error_msg = f"Timed environmental capture failed: {str(e)}"
            print(f"❌ {error_msg}")
            results["error"] = error_msg
            results["capture_duration_actual"] = time.time() - start_time if 'start_time' in locals() else 0
        
        return results

    def estimate_environmental_capture_session(
        self,
        capture_duration_seconds: int,
        sample_rate_hz: float
    ) -> Dict[str, Any]:
        """
        Estimate the results of a timed environmental capture session without actually capturing.
        
        Args:
            capture_duration_seconds (int): Total duration to capture data
            sample_rate_hz (float): Sample rate in Hz
            
        Returns:
            dict: Estimated capture session results
        """
        
        if not (0.1 <= sample_rate_hz <= 60.0):
            return {
                "error": f"Invalid sample rate: {sample_rate_hz}Hz. Must be between 0.1 and 60.0 Hz"
            }
        
        estimated_samples = int(capture_duration_seconds * sample_rate_hz)
        
        # Estimate file sizes (approximate)
        env_size_per_file = 1024  # ~1KB per environment JSON
        air_size_per_file = 1024  # ~1KB per air quality JSON
        light_size_per_file = 1024  # ~1KB per light level JSON
        
        total_files = estimated_samples * 3  # 3 sensor types
        estimated_total_size_mb = (total_files * 1024) / (1024 * 1024)
        
        return {
            "estimated_samples_per_sensor": estimated_samples,
            "estimated_total_samples": estimated_samples * 3,
            "estimated_environment_files": estimated_samples,
            "estimated_air_quality_files": estimated_samples,
            "estimated_light_level_files": estimated_samples,
            "estimated_total_files": total_files,
            "sample_rate_hz": sample_rate_hz,
            "sample_interval_seconds": 1.0 / sample_rate_hz,
            "estimated_total_size_mb": round(estimated_total_size_mb, 3),
            "sensors_involved": ["environment_conditions", "air_quality", "light_level"],
            "capture_efficiency": 100.0  # Environmental sensors capture continuously
        }


# Global instance
_environmental_manager = None

def get_environmental_manager():
    """Get the global environmental manager instance"""
    global _environmental_manager
    if _environmental_manager is None:
        _environmental_manager = EnvironmentalManager()
    return _environmental_manager

def timed_environmental_capture(
    capture_duration_seconds: int,
    sample_rate_hz: float,
    save_location: str,
    device_id: str = None,
    stop_event: threading.Event = None,
    capture_params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Convenience function for timed environmental capture.
    
    Args:
        capture_duration_seconds (int): Total duration to capture data
        sample_rate_hz (float): Sample rate in Hz  
        save_location (str): Location where JSON files will be saved
        device_id (str, optional): Device identifier
        stop_event (threading.Event, optional): Stop event
        capture_params (dict, optional): Additional capture parameters
        
    Returns:
        dict: Capture results
    """
    manager = get_environmental_manager()
    return manager.timed_environmental_capture(
        capture_duration_seconds=capture_duration_seconds,
        sample_rate_hz=sample_rate_hz,
        save_location=save_location,
        device_id=device_id,
        stop_event=stop_event,
        capture_params=capture_params
    )

def estimate_environmental_capture_session(
    capture_duration_seconds: int,
    sample_rate_hz: float
) -> Dict[str, Any]:
    """
    Convenience function for estimating environmental capture session.
    
    Args:
        capture_duration_seconds (int): Total duration to capture data
        sample_rate_hz (float): Sample rate in Hz
        
    Returns:
        dict: Estimated session results
    """
    manager = get_environmental_manager()
    return manager.estimate_environmental_capture_session(
        capture_duration_seconds=capture_duration_seconds,
        sample_rate_hz=sample_rate_hz
    )

