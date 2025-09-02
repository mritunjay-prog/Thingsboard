"""
Ultrasonic Control Service

This module manages the operational state and configuration of ultrasonic sensors
for distance measurement and obstacle detection.
"""

import threading
import time
from typing import Dict, Any, Optional


class UltrasonicControlService:
    """
    Controls ultrasonic sensor operations including sensor activation,
    configuration management, and operational state tracking.
    """
    
    def __init__(self):
        """Initialize the ultrasonic control service."""
        self._lock = threading.RLock()
        self._active = False
        self._config = {
            "sensors_enabled": 4,
            "sample_rate_hz": 10.0,
            "max_range_cm": 400,
            "min_range_cm": 5,
            "temperature_compensation": True,
            "noise_filtering": True
        }
        self._start_time = None
        self._status = "initialized"
        
    def start(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start ultrasonic sensor operations.
        
        Args:
            config: Optional configuration parameters
            
        Returns:
            Dictionary containing the start result
        """
        with self._lock:
            try:
                if self._active:
                    return {
                        "success": False,
                        "active": True,
                        "message": "Ultrasonic sensors already active",
                        "config": self._config.copy()
                    }
                
                # Apply new configuration if provided
                if config:
                    self._apply_config(config)
                
                self._active = True
                self._start_time = time.time()
                self._status = "operational"
                
                print(f"🔊 Ultrasonic Control Service started")
                print(f"   - Sensors enabled: {self._config['sensors_enabled']}")
                print(f"   - Sample rate: {self._config['sample_rate_hz']} Hz")
                print(f"   - Range: {self._config['min_range_cm']}-{self._config['max_range_cm']} cm")
                print(f"   - Temperature compensation: {self._config['temperature_compensation']}")
                
                return {
                    "success": True,
                    "active": True,
                    "message": "Ultrasonic sensors started successfully",
                    "config": self._config.copy(),
                    "start_time": self._start_time
                }
                
            except Exception as e:
                print(f"❌ Failed to start ultrasonic sensors: {e}")
                self._status = "error"
                return {
                    "success": False,
                    "active": False,
                    "message": f"Failed to start ultrasonic sensors: {str(e)}",
                    "error": str(e)
                }
    
    def stop(self) -> Dict[str, Any]:
        """
        Stop ultrasonic sensor operations.
        
        Returns:
            Dictionary containing the stop result
        """
        with self._lock:
            try:
                if not self._active:
                    return {
                        "success": False,
                        "active": False,
                        "message": "Ultrasonic sensors not active"
                    }
                
                uptime = time.time() - self._start_time if self._start_time else 0
                
                self._active = False
                self._status = "stopped"
                
                print(f"🔇 Ultrasonic Control Service stopped")
                print(f"   - Uptime: {uptime:.1f} seconds")
                
                return {
                    "success": True,
                    "active": False,
                    "message": "Ultrasonic sensors stopped successfully",
                    "uptime_seconds": round(uptime, 1)
                }
                
            except Exception as e:
                print(f"❌ Failed to stop ultrasonic sensors: {e}")
                return {
                    "success": False,
                    "active": self._active,
                    "message": f"Failed to stop ultrasonic sensors: {str(e)}",
                    "error": str(e)
                }
    
    def reset(self) -> Dict[str, Any]:
        """
        Reset ultrasonic sensor system to default configuration.
        
        Returns:
            Dictionary containing the reset result
        """
        with self._lock:
            try:
                was_active = self._active
                
                # Stop if active
                if self._active:
                    self.stop()
                
                # Reset to default configuration
                self._config = {
                    "sensors_enabled": 4,
                    "sample_rate_hz": 10.0,
                    "max_range_cm": 400,
                    "min_range_cm": 5,
                    "temperature_compensation": True,
                    "noise_filtering": True
                }
                self._status = "reset"
                
                print(f"🔄 Ultrasonic Control Service reset to defaults")
                
                result = {
                    "success": True,
                    "active": False,
                    "message": "Ultrasonic sensors reset to default configuration",
                    "config": self._config.copy(),
                    "was_active": was_active
                }
                
                return result
                
            except Exception as e:
                print(f"❌ Failed to reset ultrasonic sensors: {e}")
                return {
                    "success": False,
                    "active": self._active,
                    "message": f"Failed to reset ultrasonic sensors: {str(e)}",
                    "error": str(e)
                }
    
    def current_state(self) -> Dict[str, Any]:
        """
        Get the current operational state and configuration.
        
        Returns:
            Dictionary containing current state information
        """
        with self._lock:
            uptime = time.time() - self._start_time if self._start_time and self._active else 0
            
            return {
                "active": self._active,
                "status": self._status,
                "config": self._config.copy(),
                "uptime_seconds": round(uptime, 1) if self._active else 0,
                "start_time": self._start_time,
                "sensors_operational": self._config["sensors_enabled"] if self._active else 0
            }
    
    def apply_config(self, **kwargs) -> Dict[str, Any]:
        """
        Apply configuration parameters.
        
        Args:
            **kwargs: Configuration parameters to apply
            
        Returns:
            Dictionary containing applied configuration
        """
        with self._lock:
            return self._apply_config(kwargs)
    
    def _apply_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to apply configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Applied configuration
        """
        if "sensors_enabled" in config:
            sensors_enabled = int(config["sensors_enabled"])
            if 1 <= sensors_enabled <= 4:
                self._config["sensors_enabled"] = sensors_enabled
            else:
                raise ValueError(f"sensors_enabled must be between 1 and 4, got {sensors_enabled}")
        
        if "sample_rate_hz" in config:
            sample_rate = float(config["sample_rate_hz"])
            if 0.1 <= sample_rate <= 100.0:
                self._config["sample_rate_hz"] = sample_rate
            else:
                raise ValueError(f"sample_rate_hz must be between 0.1 and 100.0, got {sample_rate}")
        
        if "max_range_cm" in config:
            max_range = float(config["max_range_cm"])
            if 10 <= max_range <= 500:
                self._config["max_range_cm"] = max_range
            else:
                raise ValueError(f"max_range_cm must be between 10 and 500, got {max_range}")
        
        if "min_range_cm" in config:
            min_range = float(config["min_range_cm"])
            if 1 <= min_range <= 50:
                self._config["min_range_cm"] = min_range
            else:
                raise ValueError(f"min_range_cm must be between 1 and 50, got {min_range}")
        
        if "temperature_compensation" in config:
            self._config["temperature_compensation"] = bool(config["temperature_compensation"])
        
        if "noise_filtering" in config:
            self._config["noise_filtering"] = bool(config["noise_filtering"])
        
        # Validate min < max range
        if self._config["min_range_cm"] >= self._config["max_range_cm"]:
            raise ValueError("min_range_cm must be less than max_range_cm")
        
        print(f"🔧 Ultrasonic configuration updated: {config}")
        
        return self._config.copy()
    
    def get_effective_generation_params(self) -> Dict[str, Any]:
        """
        Get the effective parameters for telemetry data generation.
        
        Returns:
            Dictionary containing effective generation parameters
        """
        with self._lock:
            return {
                "active": self._active,
                "sensors_enabled": self._config["sensors_enabled"],
                "sample_rate_hz": self._config["sample_rate_hz"],
                "max_range_cm": self._config["max_range_cm"],
                "min_range_cm": self._config["min_range_cm"],
                "temperature_compensation": self._config["temperature_compensation"],
                "noise_filtering": self._config["noise_filtering"]
            }

    def timed_ultrasonic_capture(
        self,
        sample_rate_hz: float,
        capture_duration_seconds: int,
        save_location: str,
        device_id: str = None,
        stop_event: threading.Event = None,
        capture_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Perform timed ultrasonic data capture for a specified duration.
        
        This method captures ultrasonic telemetry data at the specified sample rate
        for the given duration and saves it to JSON files.
        
        Args:
            sample_rate_hz (float): Sample rate in Hz (how frequently to capture data)
            capture_duration_seconds (int): Total duration to capture data (in seconds)
            save_location (str): Directory path where telemetry JSON files should be saved
            device_id (str, optional): Device identifier for file naming
            stop_event (threading.Event, optional): Event to signal early termination
            capture_params (dict, optional): Additional ultrasonic capture parameters
            
        Returns:
            dict: Results containing captured ultrasonic data information
                {
                    "success": bool,
                    "samples_captured": int,
                    "telemetry_files": List[str],
                    "capture_duration_actual": float,
                    "total_distance_readings": int,
                    "avg_distance_cm": float,
                    "sample_rate_actual": float,
                    "error": str (if success=False)
                }
        """
        
        print(f"🔊 Starting timed ultrasonic capture session")
        print(f"   Sample rate: {sample_rate_hz}Hz")
        print(f"   Duration: {capture_duration_seconds}s")
        print(f"   Save location: {save_location}")
        
        # Validate sample rate
        if not (0.1 <= sample_rate_hz <= 100.0):
            return {
                "success": False,
                "error": f"Invalid sample rate: {sample_rate_hz}Hz. Must be between 0.1 and 100.0 Hz",
                "samples_captured": 0,
                "telemetry_files": [],
                "capture_duration_actual": 0.0,
                "total_distance_readings": 0,
                "avg_distance_cm": 0.0,
                "sample_rate_actual": 0.0
            }
        
        # Initialize results
        results = {
            "success": False,
            "samples_captured": 0,
            "telemetry_files": [],
            "capture_duration_actual": 0.0,
            "total_distance_readings": 0,
            "avg_distance_cm": 0.0,
            "sample_rate_actual": 0.0,
            "error": None
        }
        
        try:
            # Setup save directory
            from pathlib import Path
            save_dir = Path(save_location)
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # Default capture parameters
            default_params = {
                "sensors_enabled": 4,
                "sample_rate_hz": sample_rate_hz,
                "max_range_cm": 400,
                "min_range_cm": 5,
                "temperature_compensation": True,
                "noise_filtering": True
            }
            
            # Merge with user-provided parameters
            if capture_params:
                default_params.update(capture_params)
            
            # Store original state to restore later
            original_state = self.current_state()
            was_originally_active = original_state["active"]
            
            # Configure ultrasonic with capture parameters
            if capture_params or sample_rate_hz != self._config.get("sample_rate_hz", 10.0):
                print(f"🔧 Applying ultrasonic configuration: sample_rate_hz={sample_rate_hz}")
                try:
                    self.apply_config(**default_params)
                except Exception as cfg_err:
                    print(f"⚠️ Configuration warning: {cfg_err}")
            
            # Start ultrasonic if not already active
            if not was_originally_active:
                start_result = self.start(default_params)
                if not start_result.get("active", False):
                    return {
                        "success": False,
                        "error": "Failed to start ultrasonic sensors for capture session",
                        "samples_captured": 0,
                        "telemetry_files": [],
                        "capture_duration_actual": 0.0,
                        "total_distance_readings": 0,
                        "avg_distance_cm": 0.0,
                        "sample_rate_actual": 0.0
                    }
                print(f"✅ Ultrasonic sensors started for capture session")
            else:
                print(f"🔊 Using already active ultrasonic service")
            
            # Calculate timing
            sample_interval = 1.0 / sample_rate_hz
            expected_samples = int(capture_duration_seconds * sample_rate_hz)
            
            print(f"📊 Capture plan:")
            print(f"   Sample rate: {sample_rate_hz}Hz")
            print(f"   Sample interval: {sample_interval:.3f}s")
            print(f"   Expected samples: {expected_samples}")
            print(f"   Sensors enabled: {self._config['sensors_enabled']}")
            
            # Track timing and data
            start_time = time.time()
            captured_files = []
            total_distances = []
            
            # Import telemetry functions
            from .telemetry_file_saver import save_ultrasonic_telemetry_to_file
            from . import get_ultrasonic_telemetry_data
            
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
                    # Get ultrasonic telemetry data
                    ultrasonic_data = get_ultrasonic_telemetry_data()
                    
                    if ultrasonic_data and "values" in ultrasonic_data:
                        sample_count += 1
                        
                        # Save telemetry data to JSON file
                        timestamp = int(time.time() * 1000)
                        telemetry_filename = f"ultrasonic_telemetry_{timestamp}.json"
                        telemetry_path = save_dir / telemetry_filename
                        
                        # Save with timestamp wrapper
                        telemetry_entry = {
                            "timestamp": time.time(),
                            "readable_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "device_id": device_id,
                            "sample_number": sample_count,
                            "sample_rate_hz": sample_rate_hz,
                            "data": ultrasonic_data
                        }
                        
                        with open(telemetry_path, 'w') as f:
                            import json
                            json.dump(telemetry_entry, f, indent=2)
                        
                        captured_files.append(str(telemetry_path))
                        results["samples_captured"] += 1
                        
                        # Extract distance readings for statistics
                        values = ultrasonic_data.get("values", {})
                        for sensor_id in range(1, self._config["sensors_enabled"] + 1):
                            distance = values.get(f"ultrasonic.sensor_{sensor_id}.distance_cm", 0)
                            if distance > 0:
                                total_distances.append(distance)
                        
                        if sample_count % 10 == 0:
                            sensor_distances = [values.get(f"ultrasonic.sensor_{i}.distance_cm", 0) 
                                             for i in range(1, self._config["sensors_enabled"] + 1)]
                            print(f"🔊 Ultrasonic: {sample_count} samples captured, distances: {sensor_distances}")
                    
                except Exception as sample_error:
                    print(f"❌ Ultrasonic sample error: {sample_error}")
                
                # Wait for next sample
                time.sleep(sample_interval)
            
            # Calculate final results
            end_time = time.time()
            results["capture_duration_actual"] = end_time - start_time
            results["telemetry_files"] = captured_files
            results["total_distance_readings"] = len(total_distances)
            results["avg_distance_cm"] = round(sum(total_distances) / len(total_distances), 1) if total_distances else 0.0
            results["sample_rate_actual"] = round(sample_count / results["capture_duration_actual"], 2) if results["capture_duration_actual"] > 0 else 0.0
            results["success"] = True
            
            print(f"✅ Timed ultrasonic capture completed:")
            print(f"   Total samples: {results['samples_captured']}")
            print(f"   Telemetry files: {len(captured_files)}")
            print(f"   Distance readings: {results['total_distance_readings']}")
            print(f"   Average distance: {results['avg_distance_cm']}cm")
            print(f"   Actual sample rate: {results['sample_rate_actual']}Hz")
            print(f"   Actual duration: {results['capture_duration_actual']:.2f}s")
            print(f"   Files saved to: {save_dir}")
            
            # Restore original ultrasonic state if we started it
            if not was_originally_active and self._active:
                print(f"🔄 Stopping ultrasonic sensors (was not originally active)")
                self.stop()
            
        except Exception as e:
            error_msg = f"Timed ultrasonic capture failed: {str(e)}"
            print(f"❌ {error_msg}")
            results["error"] = error_msg
            results["capture_duration_actual"] = time.time() - start_time if 'start_time' in locals() else 0
        
        return results

    def estimate_ultrasonic_capture_session(
        self,
        sample_rate_hz: float,
        capture_duration_seconds: int
    ) -> Dict[str, Any]:
        """
        Estimate the results of a timed ultrasonic capture session without actually capturing.
        
        Args:
            sample_rate_hz (float): Sample rate in Hz
            capture_duration_seconds (int): Total duration to capture data
            
        Returns:
            dict: Estimated capture session results
        """
        
        if not (0.1 <= sample_rate_hz <= 100.0):
            return {
                "error": f"Invalid sample rate: {sample_rate_hz}Hz. Must be between 0.1 and 100.0 Hz"
            }
        
        estimated_samples = int(capture_duration_seconds * sample_rate_hz)
        sensors_enabled = self._config.get("sensors_enabled", 4)
        estimated_distance_readings = estimated_samples * sensors_enabled
        
        # Estimate file sizes (approximate)
        telemetry_size_per_file = 1024  # ~1KB per ultrasonic telemetry JSON
        estimated_total_size_mb = (estimated_samples * telemetry_size_per_file) / (1024 * 1024)
        
        return {
            "estimated_samples": estimated_samples,
            "estimated_distance_readings": estimated_distance_readings,
            "sensors_enabled": sensors_enabled,
            "sample_rate_hz": sample_rate_hz,
            "sample_interval_seconds": 1.0 / sample_rate_hz,
            "estimated_telemetry_files": estimated_samples,
            "estimated_telemetry_size_mb": round(estimated_total_size_mb, 3),
            "capture_efficiency": 100.0  # Ultrasonic captures continuously
        }
