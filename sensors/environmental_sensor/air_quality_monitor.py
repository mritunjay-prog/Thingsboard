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
    print("✅ Telemetry saver imported successfully for air quality monitor")
except ImportError as e:
    TELEMETRY_SAVER_AVAILABLE = False
    print(f"⚠️ Telemetry saver not available for air quality monitor: {e}")


class AirQualityMonitorService:
    """
    Air Quality Monitor Service for monitoring PM2.5, CO2, VOC, and calculating AQI.
    """
    
    def __init__(self, data_dir: str = "data/telemetry"):
        """
        Initialize the air quality monitor service
        
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
            "sample_interval_seconds": 60,
            "pm2_5_range_ugm3": (0, 500),
            "pm10_range_ugm3": (0, 1000),
            "co2_range_ppm": (300, 2000),
            "voc_range_index": (0, 1000),
            "enable_data_saving": True
        }
        
        # Current readings (for simulation)
        self.current_readings = {
            "pm2_5_ugm3": 15.0,
            "pm10_ugm3": 25.0,
            "co2_ppm": 450.0,
            "voc_index": 125.0
        }
        
        # AQI breakpoints (US EPA standard)
        self.aqi_breakpoints = {
            "pm2_5": [
                (0, 12.0, 0, 50),      # Good
                (12.1, 35.4, 51, 100), # Moderate
                (35.5, 55.4, 101, 150), # Unhealthy for Sensitive Groups
                (55.5, 150.4, 151, 200), # Unhealthy
                (150.5, 250.4, 201, 300), # Very Unhealthy
                (250.5, 500, 301, 500)   # Hazardous
            ],
            "pm10": [
                (0, 54, 0, 50),
                (55, 154, 51, 100),
                (155, 254, 101, 150),
                (255, 354, 151, 200),
                (355, 424, 201, 300),
                (425, 604, 301, 500)
            ]
        }
        
        self.aqi_categories = {
            (0, 50): "good",
            (51, 100): "moderate", 
            (101, 150): "unhealthy_for_sensitive",
            (151, 200): "unhealthy",
            (201, 300): "very_unhealthy",
            (301, 500): "hazardous"
        }
        
        print("🌬️ Air Quality Monitor Service initialized")
    
    def get_telemetry_data(self) -> Dict[str, Any]:
        """
        Get current air quality telemetry data
        
        Returns:
            Dictionary containing current air quality telemetry in ThingsBoard format
        """
        try:
            # Get current sensor readings (simulated)
            readings = self._read_air_quality_sensors()
            
            # Calculate AQI
            aqi_value, aqi_category = self._calculate_aqi(readings)
            
            # Build telemetry data in ThingsBoard format
            telemetry_data = {
                "ts": int(time.time() * 1000),
                "values": {
                    "air_quality.pm2_5_ugm3": round(readings["pm2_5_ugm3"], 1),
                    "air_quality.pm10_ugm3": round(readings["pm10_ugm3"], 1),
                    "air_quality.co2_ppm": int(readings["co2_ppm"]),
                    "air_quality.voc_index": int(readings["voc_index"]),
                    "air_quality.aqi": int(aqi_value),
                    "air_quality.aqi_category": aqi_category
                }
            }
            
            return telemetry_data
            
        except Exception as e:
            print(f"❌ Error getting air quality telemetry data: {e}")
            return {}
    
    def _read_air_quality_sensors(self) -> Dict[str, float]:
        """
        Read current air quality sensor values
        
        In production, this would interface with actual sensors like:
        - PMS5003/PMS7003 (PM2.5, PM10)
        - SCD30/SCD40 (CO2, temperature, humidity)
        - SGP30/SGP40 (VOC, NOx)
        - CCS811 (CO2, VOC)
        - MQ series (various gases)
        
        Returns:
            Dictionary containing current sensor readings
        """
        try:
            # Simulate realistic sensor readings with gradual changes
            pm2_5_change = random.uniform(-2.0, 2.0)
            pm10_change = random.uniform(-3.0, 3.0)
            co2_change = random.uniform(-10, 10)
            voc_change = random.uniform(-5, 5)
            
            # Apply changes with bounds checking
            self.current_readings["pm2_5_ugm3"] = max(
                self.config["pm2_5_range_ugm3"][0],
                min(self.config["pm2_5_range_ugm3"][1],
                    self.current_readings["pm2_5_ugm3"] + pm2_5_change)
            )
            
            self.current_readings["pm10_ugm3"] = max(
                self.config["pm10_range_ugm3"][0],
                min(self.config["pm10_range_ugm3"][1],
                    self.current_readings["pm10_ugm3"] + pm10_change)
            )
            
            self.current_readings["co2_ppm"] = max(
                self.config["co2_range_ppm"][0],
                min(self.config["co2_range_ppm"][1],
                    self.current_readings["co2_ppm"] + co2_change)
            )
            
            self.current_readings["voc_index"] = max(
                self.config["voc_range_index"][0],
                min(self.config["voc_range_index"][1],
                    self.current_readings["voc_index"] + voc_change)
            )
            
            return self.current_readings.copy()
            
        except Exception as e:
            print(f"❌ Error reading air quality sensors: {e}")
            # Return default safe values
            return {
                "pm2_5_ugm3": 10.0,
                "pm10_ugm3": 15.0,
                "co2_ppm": 400,
                "voc_index": 100
            }
    
    def _calculate_aqi(self, readings: Dict[str, float]) -> tuple:
        """
        Calculate Air Quality Index (AQI) using US EPA standard
        
        Args:
            readings: Dictionary containing sensor readings
            
        Returns:
            Tuple of (aqi_value, aqi_category)
        """
        try:
            pm2_5 = readings["pm2_5_ugm3"]
            pm10 = readings["pm10_ugm3"]
            
            # Calculate AQI for PM2.5
            pm2_5_aqi = self._calculate_pollutant_aqi(pm2_5, self.aqi_breakpoints["pm2_5"])
            
            # Calculate AQI for PM10
            pm10_aqi = self._calculate_pollutant_aqi(pm10, self.aqi_breakpoints["pm10"])
            
            # Take the maximum (worst) AQI
            overall_aqi = max(pm2_5_aqi, pm10_aqi)
            
            # Determine category
            aqi_category = self._get_aqi_category(overall_aqi)
            
            return overall_aqi, aqi_category
            
        except Exception as e:
            print(f"❌ Error calculating AQI: {e}")
            return 50, "good"  # Fallback to good air quality
    
    def _calculate_pollutant_aqi(self, concentration: float, breakpoints: list) -> int:
        """
        Calculate AQI for a specific pollutant using linear interpolation
        
        Args:
            concentration: Pollutant concentration
            breakpoints: List of breakpoint tuples (C_lo, C_hi, I_lo, I_hi)
            
        Returns:
            AQI value for the pollutant
        """
        try:
            for c_lo, c_hi, i_lo, i_hi in breakpoints:
                if c_lo <= concentration <= c_hi:
                    # Linear interpolation formula
                    aqi = ((i_hi - i_lo) / (c_hi - c_lo)) * (concentration - c_lo) + i_lo
                    return int(round(aqi))
            
            # If concentration exceeds all breakpoints, use hazardous level
            return 500
            
        except Exception as e:
            print(f"❌ Error calculating pollutant AQI: {e}")
            return 50
    
    def _get_aqi_category(self, aqi_value: int) -> str:
        """
        Get AQI category based on AQI value
        
        Args:
            aqi_value: AQI value
            
        Returns:
            AQI category string
        """
        for (min_val, max_val), category in self.aqi_categories.items():
            if min_val <= aqi_value <= max_val:
                return category
        
        return "hazardous"  # Fallback for extreme values
    
    def save_telemetry_to_file(self, telemetry_data: Dict[str, Any]) -> bool:
        """
        Save air quality telemetry data to file (append to single file)
        
        Args:
            telemetry_data: Telemetry data to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if not self.config.get("enable_data_saving", True):
                return True
            
            # Use fixed filename for all air quality telemetry data
            filename = "air_quality_telemetry.json"
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
            
            print(f"💾 Air quality telemetry saved: {filename} (total: {len(telemetry_list)} entries)")
            return True
            
        except Exception as e:
            print(f"❌ Error saving air quality telemetry: {e}")
            return False
    
    def start_monitoring(self, interval_seconds: int = None) -> Dict[str, Any]:
        """
        Start continuous air quality monitoring
        
        Args:
            interval_seconds: Monitoring interval (uses config default if None)
            
        Returns:
            Status dictionary
        """
        with self.monitoring_lock:
            if self.is_monitoring:
                return {
                    "success": False,
                    "message": "Air quality monitoring is already running"
                }
            
            # Update interval if provided
            if interval_seconds:
                self.config["sample_interval_seconds"] = interval_seconds
            
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            print(f"🚀 Air quality monitoring started (interval: {self.config['sample_interval_seconds']}s)")
            
            return {
                "success": True,
                "message": "Air quality monitoring started",
                "interval_seconds": self.config["sample_interval_seconds"]
            }
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """
        Stop continuous air quality monitoring
        
        Returns:
            Status dictionary
        """
        with self.monitoring_lock:
            if not self.is_monitoring:
                return {
                    "success": False,
                    "message": "Air quality monitoring is not running"
                }
            
            self.is_monitoring = False
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            print("🛑 Air quality monitoring stopped")
            
            return {
                "success": True,
                "message": "Air quality monitoring stopped"
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
                                db_success = save_telemetry('environmental_air_quality', telemetry_values, sync_status=0)
                                if db_success:
                                    print(f"💾 Air quality telemetry saved to database")
                                else:
                                    print(f"⚠️ Failed to save air quality telemetry to database")
                        except Exception as db_error:
                            print(f"❌ Database save error: {db_error}")
                    
                    # Print current readings
                    values = telemetry_data.get("values", {})
                    pm2_5 = values.get("air_quality.pm2_5_ugm3", 0)
                    pm10 = values.get("air_quality.pm10_ugm3", 0)
                    co2 = values.get("air_quality.co2_ppm", 0)
                    aqi = values.get("air_quality.aqi", 0)
                    category = values.get("air_quality.aqi_category", "unknown")
                    
                    print(f"🌬️ Air Quality: PM2.5:{pm2_5}μg/m³, PM10:{pm10}μg/m³, CO2:{co2}ppm, AQI:{aqi}({category})")
                
                # Wait for next sample
                time.sleep(self.config["sample_interval_seconds"])
                
            except Exception as e:
                print(f"❌ Error in air quality monitoring loop: {e}")
                time.sleep(5)  # Brief pause on error
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current service status
        
        Returns:
            Dictionary containing service status information
        """
        with self.monitoring_lock:
            return {
                "service": "air_quality_monitor",
                "status": "monitoring" if self.is_monitoring else "idle",
                "data_directory": str(self.data_dir),
                "sample_interval_seconds": self.config["sample_interval_seconds"],
                "pm2_5_range_ugm3": self.config["pm2_5_range_ugm3"],
                "pm10_range_ugm3": self.config["pm10_range_ugm3"],
                "co2_range_ppm": self.config["co2_range_ppm"],
                "voc_range_index": self.config["voc_range_index"],
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
            print(f"✅ Air quality monitor config updated: {new_config}")
            return self.config.copy()
            
        except Exception as e:
            print(f"❌ Error updating air quality config: {e}")
            return self.config.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get air quality summary with health recommendations
        
        Returns:
            Summary of current air quality conditions
        """
        try:
            telemetry_data = self.get_telemetry_data()
            values = telemetry_data.get("values", {})
            
            aqi = values.get("air_quality.aqi", 0)
            category = values.get("air_quality.aqi_category", "unknown")
            
            # Generate health recommendations based on AQI
            recommendations = self._get_health_recommendations(aqi, category)
            
            # Assess individual pollutants
            pollutant_status = self._assess_pollutants(values)
            
            return {
                "timestamp": telemetry_data.get("ts", int(time.time() * 1000)),
                "current_measurements": values,
                "overall_aqi": {
                    "value": aqi,
                    "category": category,
                    "color_code": self._get_aqi_color(aqi)
                },
                "pollutant_status": pollutant_status,
                "health_recommendations": recommendations,
                "monitoring_active": self.is_monitoring
            }
            
        except Exception as e:
            print(f"❌ Error getting air quality summary: {e}")
            return {}
    
    def _get_health_recommendations(self, aqi: int, category: str) -> Dict[str, Any]:
        """Generate health recommendations based on AQI"""
        recommendations = {
            "good": {
                "general": "Air quality is satisfactory. Enjoy outdoor activities.",
                "sensitive": "No precautions needed.",
                "activity_level": "normal"
            },
            "moderate": {
                "general": "Air quality is acceptable for most people.",
                "sensitive": "Sensitive individuals may experience minor symptoms.",
                "activity_level": "normal"
            },
            "unhealthy_for_sensitive": {
                "general": "Most people can continue normal activities.",
                "sensitive": "Sensitive groups should limit prolonged outdoor activities.",
                "activity_level": "reduced_for_sensitive"
            },
            "unhealthy": {
                "general": "Everyone should limit prolonged outdoor activities.",
                "sensitive": "Sensitive groups should avoid outdoor activities.",
                "activity_level": "limited"
            },
            "very_unhealthy": {
                "general": "Everyone should avoid outdoor activities.",
                "sensitive": "Sensitive groups should remain indoors.",
                "activity_level": "indoor_only"
            },
            "hazardous": {
                "general": "Everyone should remain indoors and avoid outdoor activities.",
                "sensitive": "Emergency conditions for sensitive groups.",
                "activity_level": "emergency"
            }
        }
        
        return recommendations.get(category, recommendations["good"])
    
    def _assess_pollutants(self, values: Dict[str, Any]) -> Dict[str, str]:
        """Assess individual pollutant levels"""
        pm2_5 = values.get("air_quality.pm2_5_ugm3", 0)
        pm10 = values.get("air_quality.pm10_ugm3", 0)
        co2 = values.get("air_quality.co2_ppm", 0)
        voc = values.get("air_quality.voc_index", 0)
        
        status = {}
        
        # PM2.5 assessment
        if pm2_5 <= 12:
            status["pm2_5"] = "good"
        elif pm2_5 <= 35:
            status["pm2_5"] = "moderate"
        elif pm2_5 <= 55:
            status["pm2_5"] = "unhealthy_for_sensitive"
        else:
            status["pm2_5"] = "unhealthy"
        
        # PM10 assessment
        if pm10 <= 54:
            status["pm10"] = "good"
        elif pm10 <= 154:
            status["pm10"] = "moderate"
        else:
            status["pm10"] = "unhealthy"
        
        # CO2 assessment
        if co2 <= 1000:
            status["co2"] = "good"
        elif co2 <= 2000:
            status["co2"] = "moderate"
        else:
            status["co2"] = "poor"
        
        # VOC assessment
        if voc <= 150:
            status["voc"] = "good"
        elif voc <= 250:
            status["voc"] = "moderate"
        else:
            status["voc"] = "poor"
        
        return status
    
    def _get_aqi_color(self, aqi: int) -> str:
        """Get color code for AQI value"""
        if aqi <= 50:
            return "green"
        elif aqi <= 100:
            return "yellow"
        elif aqi <= 150:
            return "orange"
        elif aqi <= 200:
            return "red"
        elif aqi <= 300:
            return "purple"
        else:
            return "maroon"
