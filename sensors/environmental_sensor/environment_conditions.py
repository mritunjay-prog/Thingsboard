#!/usr/bin/env python3

import time
import math
import random
import threading
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add services to path for telemetry saver import
sys.path.append(str(Path(__file__).parent.parent.parent / 'services'))

try:
    from telemetry_saver import save_telemetry
    TELEMETRY_SAVER_AVAILABLE = True
    print("✅ Telemetry saver imported successfully for environment conditions")
except ImportError as e:
    TELEMETRY_SAVER_AVAILABLE = False
    print(f"⚠️ Telemetry saver not available for environment conditions: {e}")


class EnvironmentConditionsService:
    """
    Environment Conditions Service for monitoring temperature, humidity, pressure,
    dew point, heat index, and pressure altitude.
    """
    
    def __init__(self, data_dir: str = "data/telemetry"):
        """
        Initialize the environment conditions service
        
        Args:
            data_dir: Directory to store telemetry data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Sensor configuration and state
        self.is_monitoring = False
        self.monitoring_thread = None
        self.monitoring_lock = threading.Lock()
        
        # Configuration defaults
        self.config = {
            "sample_interval_seconds": 30,
            "temperature_range_c": (-10, 50),
            "humidity_range_percent": (20, 90),
            "pressure_range_hpa": (980, 1050),
            "sea_level_pressure_hpa": 1013.25,
            "enable_data_saving": True
        }
        
        # Current readings (for simulation)
        self.current_readings = {
            "temperature_c": 22.5,
            "humidity_percent": 65.0,
            "pressure_hpa": 1013.25
        }
        
        print("🌡️ Environment Conditions Service initialized")
    
    def get_telemetry_data(self) -> Dict[str, Any]:
        """
        Get current environment conditions telemetry data
        
        Returns:
            Dictionary containing current environment telemetry in ThingsBoard format
        """
        try:
            # Get current sensor readings (simulated)
            readings = self._read_environment_sensors()
            
            # Calculate derived values
            dew_point = self._calculate_dew_point(readings["temperature_c"], readings["humidity_percent"])
            heat_index = self._calculate_heat_index(readings["temperature_c"], readings["humidity_percent"])
            pressure_altitude = self._calculate_pressure_altitude(readings["pressure_hpa"])
            
            # Build telemetry data in ThingsBoard format
            telemetry_data = {
                "ts": int(time.time() * 1000),
                "values": {
                    "environment.temperature_c": round(readings["temperature_c"], 1),
                    "environment.humidity_percent": round(readings["humidity_percent"], 1),
                    "environment.pressure_hpa": round(readings["pressure_hpa"], 2),
                    "environment.pressure_altitude_m": round(pressure_altitude, 1),
                    "environment.dew_point_c": round(dew_point, 1),
                    "environment.heat_index_c": round(heat_index, 1)
                }
            }
            
            return telemetry_data
            
        except Exception as e:
            print(f"❌ Error getting environment telemetry data: {e}")
            return {}
    
    def _read_environment_sensors(self) -> Dict[str, float]:
        """
        Read current environment sensor values
        
        In production, this would interface with actual sensors like:
        - BME280/BME680 (temperature, humidity, pressure)
        - DHT22 (temperature, humidity)
        - BMP180/BMP280 (pressure, temperature)
        - SHT30 (temperature, humidity)
        
        Returns:
            Dictionary containing current sensor readings
        """
        try:
            # Simulate realistic sensor readings with gradual changes
            temp_change = random.uniform(-0.5, 0.5)
            humidity_change = random.uniform(-2.0, 2.0)
            pressure_change = random.uniform(-1.0, 1.0)
            
            # Apply changes with bounds checking
            self.current_readings["temperature_c"] = max(
                self.config["temperature_range_c"][0],
                min(self.config["temperature_range_c"][1],
                    self.current_readings["temperature_c"] + temp_change)
            )
            
            self.current_readings["humidity_percent"] = max(
                self.config["humidity_range_percent"][0],
                min(self.config["humidity_range_percent"][1],
                    self.current_readings["humidity_percent"] + humidity_change)
            )
            
            self.current_readings["pressure_hpa"] = max(
                self.config["pressure_range_hpa"][0],
                min(self.config["pressure_range_hpa"][1],
                    self.current_readings["pressure_hpa"] + pressure_change)
            )
            
            return self.current_readings.copy()
            
        except Exception as e:
            print(f"❌ Error reading environment sensors: {e}")
            # Return default safe values
            return {
                "temperature_c": 22.0,
                "humidity_percent": 50.0,
                "pressure_hpa": 1013.25
            }
    
    def _calculate_dew_point(self, temperature_c: float, humidity_percent: float) -> float:
        """
        Calculate dew point using Magnus formula
        
        Args:
            temperature_c: Temperature in Celsius
            humidity_percent: Relative humidity percentage
            
        Returns:
            Dew point in Celsius
        """
        try:
            # Magnus formula constants
            a = 17.27
            b = 237.7
            
            # Calculate alpha
            alpha = ((a * temperature_c) / (b + temperature_c)) + math.log(humidity_percent / 100.0)
            
            # Calculate dew point
            dew_point = (b * alpha) / (a - alpha)
            
            return dew_point
            
        except Exception as e:
            print(f"❌ Error calculating dew point: {e}")
            return temperature_c - 5.0  # Fallback approximation
    
    def _calculate_heat_index(self, temperature_c: float, humidity_percent: float) -> float:
        """
        Calculate heat index (apparent temperature)
        
        Args:
            temperature_c: Temperature in Celsius
            humidity_percent: Relative humidity percentage
            
        Returns:
            Heat index in Celsius
        """
        try:
            # Convert to Fahrenheit for calculation
            temp_f = (temperature_c * 9/5) + 32
            
            # If temperature is below 80°F (26.7°C), heat index equals temperature
            if temp_f < 80:
                return temperature_c
            
            # Heat index formula coefficients
            c1 = -42.379
            c2 = 2.04901523
            c3 = 10.14333127
            c4 = -0.22475541
            c5 = -0.00683783
            c6 = -0.05481717
            c7 = 0.00122874
            c8 = 0.00085282
            c9 = -0.00000199
            
            # Calculate heat index in Fahrenheit
            hi_f = (c1 + (c2 * temp_f) + (c3 * humidity_percent) + 
                   (c4 * temp_f * humidity_percent) + (c5 * temp_f * temp_f) + 
                   (c6 * humidity_percent * humidity_percent) + 
                   (c7 * temp_f * temp_f * humidity_percent) + 
                   (c8 * temp_f * humidity_percent * humidity_percent) + 
                   (c9 * temp_f * temp_f * humidity_percent * humidity_percent))
            
            # Convert back to Celsius
            heat_index_c = (hi_f - 32) * 5/9
            
            return heat_index_c
            
        except Exception as e:
            print(f"❌ Error calculating heat index: {e}")
            return temperature_c + 1.0  # Fallback approximation
    
    def _calculate_pressure_altitude(self, pressure_hpa: float) -> float:
        """
        Calculate pressure altitude from barometric pressure
        
        Args:
            pressure_hpa: Barometric pressure in hPa
            
        Returns:
            Pressure altitude in meters
        """
        try:
            # Standard atmosphere formula
            sea_level_pressure = self.config["sea_level_pressure_hpa"]
            
            # Pressure altitude formula
            altitude_m = 44330 * (1 - pow(pressure_hpa / sea_level_pressure, 0.1903))
            
            return altitude_m
            
        except Exception as e:
            print(f"❌ Error calculating pressure altitude: {e}")
            return 0.0  # Fallback to sea level
    
    def save_telemetry_to_file(self, telemetry_data: Dict[str, Any]) -> bool:
        """
        Save environment telemetry data to file (append to single file)
        
        Args:
            telemetry_data: Telemetry data to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if not self.config.get("enable_data_saving", True):
                return True
            
            # Use fixed filename for all environment telemetry data
            filename = "environment_conditions_telemetry.json"
            file_path = self.data_dir / filename
            
            # Load existing data or create new list
            import json
            telemetry_list = []
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        telemetry_list = json.load(f)
                        if not isinstance(telemetry_list, list):
                            telemetry_list = []
                except (json.JSONDecodeError, ValueError):
                    telemetry_list = []
            
            # Append new telemetry data
            telemetry_list.append(telemetry_data)
            
            # Save updated data to file
            with open(file_path, 'w') as f:
                json.dump(telemetry_list, f, indent=2)
            
            print(f"💾 Environment telemetry saved: {filename} (total: {len(telemetry_list)} entries)")
            return True
            
        except Exception as e:
            print(f"❌ Error saving environment telemetry: {e}")
            return False
    
    def start_monitoring(self, interval_seconds: int = None) -> Dict[str, Any]:
        """
        Start continuous environment monitoring
        
        Args:
            interval_seconds: Monitoring interval (uses config default if None)
            
        Returns:
            Status dictionary
        """
        with self.monitoring_lock:
            if self.is_monitoring:
                return {
                    "success": False,
                    "message": "Environment monitoring is already running"
                }
            
            # Update interval if provided
            if interval_seconds:
                self.config["sample_interval_seconds"] = interval_seconds
            
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            print(f"🚀 Environment monitoring started (interval: {self.config['sample_interval_seconds']}s)")
            
            return {
                "success": True,
                "message": "Environment monitoring started",
                "interval_seconds": self.config["sample_interval_seconds"]
            }
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """
        Stop continuous environment monitoring
        
        Returns:
            Status dictionary
        """
        with self.monitoring_lock:
            if not self.is_monitoring:
                return {
                    "success": False,
                    "message": "Environment monitoring is not running"
                }
            
            self.is_monitoring = False
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            print("🛑 Environment monitoring stopped")
            
            return {
                "success": True,
                "message": "Environment monitoring stopped"
            }
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.is_monitoring:
            try:
                # Get telemetry data
                telemetry_data = self.get_telemetry_data()
                
                if telemetry_data:
                    # Save to file if enabled
                    self.save_telemetry_to_file(telemetry_data)
                    
                    # Save to database if available
                    if TELEMETRY_SAVER_AVAILABLE:
                        try:
                            # Extract the values from telemetry data for database storage
                            telemetry_values = telemetry_data.get('values', {})
                            if telemetry_values:
                                # Save to database with sync_status=0 (successfully sent)
                                db_success = save_telemetry('environmental_environment', telemetry_values, sync_status=0)
                                if db_success:
                                    print(f"💾 Environment conditions telemetry saved to database")
                                else:
                                    print(f"⚠️ Failed to save environment conditions telemetry to database")
                        except Exception as db_error:
                            print(f"❌ Database save error: {db_error}")
                    
                    # Print current readings
                    values = telemetry_data.get("values", {})
                    temp = values.get("environment.temperature_c", 0)
                    humidity = values.get("environment.humidity_percent", 0)
                    pressure = values.get("environment.pressure_hpa", 0)
                    dew_point = values.get("environment.dew_point_c", 0)
                    
                    print(f"🌡️ Environment: {temp}°C, {humidity}%RH, {pressure}hPa, DP:{dew_point}°C")
                
                # Wait for next sample
                time.sleep(self.config["sample_interval_seconds"])
                
            except Exception as e:
                print(f"❌ Error in environment monitoring loop: {e}")
                time.sleep(5)  # Brief pause on error
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current service status
        
        Returns:
            Dictionary containing service status information
        """
        with self.monitoring_lock:
            return {
                "service": "environment_conditions",
                "status": "monitoring" if self.is_monitoring else "idle",
                "data_directory": str(self.data_dir),
                "sample_interval_seconds": self.config["sample_interval_seconds"],
                "temperature_range_c": self.config["temperature_range_c"],
                "humidity_range_percent": self.config["humidity_range_percent"],
                "pressure_range_hpa": self.config["pressure_range_hpa"],
                "current_readings": self.current_readings.copy(),
                "data_saving_enabled": self.config.get("enable_data_saving", True),
                "telemetry_saver_available": TELEMETRY_SAVER_AVAILABLE
            }
    
    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update service configuration
        
        Args:
            new_config: Dictionary containing configuration updates
            
        Returns:
            Updated configuration
        """
        try:
            self.config.update(new_config)
            print(f"✅ Environment conditions config updated: {new_config}")
            return self.config.copy()
            
        except Exception as e:
            print(f"❌ Error updating environment config: {e}")
            return self.config.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get environment conditions summary
        
        Returns:
            Summary of current environment conditions
        """
        try:
            telemetry_data = self.get_telemetry_data()
            values = telemetry_data.get("values", {})
            
            # Categorize conditions
            temp = values.get("environment.temperature_c", 0)
            humidity = values.get("environment.humidity_percent", 0)
            pressure = values.get("environment.pressure_hpa", 0)
            
            temp_category = self._categorize_temperature(temp)
            humidity_category = self._categorize_humidity(humidity)
            pressure_category = self._categorize_pressure(pressure)
            
            return {
                "timestamp": telemetry_data.get("ts", int(time.time() * 1000)),
                "current_conditions": values,
                "categories": {
                    "temperature": temp_category,
                    "humidity": humidity_category,
                    "pressure": pressure_category
                },
                "comfort_index": self._calculate_comfort_index(temp, humidity),
                "monitoring_active": self.is_monitoring
            }
            
        except Exception as e:
            print(f"❌ Error getting environment summary: {e}")
            return {}
    
    def _categorize_temperature(self, temp_c: float) -> str:
        """Categorize temperature reading"""
        if temp_c < 10:
            return "cold"
        elif temp_c < 20:
            return "cool"
        elif temp_c < 25:
            return "comfortable"
        elif temp_c < 30:
            return "warm"
        else:
            return "hot"
    
    def _categorize_humidity(self, humidity_percent: float) -> str:
        """Categorize humidity reading"""
        if humidity_percent < 30:
            return "dry"
        elif humidity_percent < 60:
            return "comfortable"
        elif humidity_percent < 80:
            return "humid"
        else:
            return "very_humid"
    
    def _categorize_pressure(self, pressure_hpa: float) -> str:
        """Categorize pressure reading"""
        if pressure_hpa < 1000:
            return "low"
        elif pressure_hpa < 1020:
            return "normal"
        else:
            return "high"
    
    def _calculate_comfort_index(self, temp_c: float, humidity_percent: float) -> str:
        """Calculate overall comfort index"""
        temp_score = 0
        humidity_score = 0
        
        # Temperature scoring (optimal: 20-24°C)
        if 20 <= temp_c <= 24:
            temp_score = 2
        elif 18 <= temp_c <= 26:
            temp_score = 1
        else:
            temp_score = 0
        
        # Humidity scoring (optimal: 40-60%)
        if 40 <= humidity_percent <= 60:
            humidity_score = 2
        elif 30 <= humidity_percent <= 70:
            humidity_score = 1
        else:
            humidity_score = 0
        
        total_score = temp_score + humidity_score
        
        if total_score >= 3:
            return "excellent"
        elif total_score >= 2:
            return "good"
        elif total_score >= 1:
            return "fair"
        else:
            return "poor"
