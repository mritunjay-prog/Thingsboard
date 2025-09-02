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
    print("✅ Telemetry saver imported successfully for light level monitor")
except ImportError as e:
    TELEMETRY_SAVER_AVAILABLE = False
    print(f"⚠️ Telemetry saver not available for light level monitor: {e}")


class LightLevelMonitorService:
    """
    Light Level Monitor Service for monitoring ambient light, UV index, and day/night state.
    """
    
    def __init__(self, data_dir: str = "data/telemetry"):
        """
        Initialize the light level monitor service
        
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
            "ambient_light_range_lux": (0, 100000),
            "uv_index_range": (0, 11),
            "ir_level_range": (0.0, 1.0),
            "color_temp_range_k": (2000, 8000),
            "day_night_threshold_lux": 200,
            "enable_data_saving": True
        }
        
        # Current readings (for simulation)
        self.current_readings = {
            "ambient_lux": 850.0,
            "uv_index": 3.2,
            "ir_level": 0.15,
            "color_temperature_k": 5600
        }
        
        print("💡 Light Level Monitor Service initialized")
    
    def get_telemetry_data(self) -> Dict[str, Any]:
        """
        Get current light level telemetry data
        
        Returns:
            Dictionary containing current light level telemetry in ThingsBoard format
        """
        try:
            # Get current sensor readings (simulated)
            readings = self._read_light_sensors()
            
            # Determine day/night state
            day_night_state = self._determine_day_night_state(readings["ambient_lux"])
            
            # Build telemetry data in ThingsBoard format
            telemetry_data = {
                "ts": int(time.time() * 1000),
                "values": {
                    "light.ambient_lux": int(readings["ambient_lux"]),
                    "light.uv_index": readings["uv_index"],
                    "light.ir_level": round(readings["ir_level"], 2),
                    "light.color_temperature_k": int(readings["color_temperature_k"]),
                    "light.day_night_state": day_night_state
                }
            }
            
            return telemetry_data
            
        except Exception as e:
            print(f"❌ Error getting light level telemetry data: {e}")
            return {}
    
    def _read_light_sensors(self) -> Dict[str, float]:
        """
        Read current light sensor values
        
        In production, this would interface with actual sensors like:
        - TSL2561/TSL2591 (ambient light, IR)
        - BH1750 (ambient light)
        - VEML6070/VEML6075 (UV index)
        - TCS34725 (color temperature, RGB)
        - APDS9960 (ambient light, gesture)
        - AS7341 (spectral sensing)
        
        Returns:
            Dictionary containing current sensor readings
        """
        try:
            # Simulate time-based lighting changes (day/night cycle)
            current_hour = datetime.now().hour
            
            # Base light level based on time of day
            if 6 <= current_hour <= 18:  # Daytime
                base_lux = random.uniform(10000, 80000)
                base_uv = random.uniform(2, 10)
                base_temp = random.uniform(5000, 6500)
            elif 19 <= current_hour <= 22:  # Evening
                base_lux = random.uniform(100, 5000)
                base_uv = random.uniform(0, 2)
                base_temp = random.uniform(2700, 4000)
            else:  # Night
                base_lux = random.uniform(0, 500)
                base_uv = 0
                base_temp = random.uniform(2000, 3000)
            
            # Apply small random variations
            lux_change = random.uniform(-0.1, 0.1) * base_lux
            uv_change = random.uniform(-0.5, 0.5)
            ir_change = random.uniform(-0.02, 0.02)
            temp_change = random.uniform(-100, 100)
            
            # Update readings with bounds checking
            self.current_readings["ambient_lux"] = max(
                self.config["ambient_light_range_lux"][0],
                min(self.config["ambient_light_range_lux"][1],
                    base_lux + lux_change)
            )
            
            self.current_readings["uv_index"] = max(
                self.config["uv_index_range"][0],
                min(self.config["uv_index_range"][1],
                    base_uv + uv_change)
            )
            
            self.current_readings["ir_level"] = max(
                self.config["ir_level_range"][0],
                min(self.config["ir_level_range"][1],
                    self.current_readings["ir_level"] + ir_change)
            )
            
            self.current_readings["color_temperature_k"] = max(
                self.config["color_temp_range_k"][0],
                min(self.config["color_temp_range_k"][1],
                    base_temp + temp_change)
            )
            
            return self.current_readings.copy()
            
        except Exception as e:
            print(f"❌ Error reading light sensors: {e}")
            # Return default safe values
            return {
                "ambient_lux": 1000,
                "uv_index": 3,
                "ir_level": 0.1,
                "color_temperature_k": 5000
            }
    
    def _determine_day_night_state(self, ambient_lux: float) -> str:
        """
        Determine day/night state based on ambient light level
        
        Args:
            ambient_lux: Ambient light level in lux
            
        Returns:
            Day/night state string
        """
        try:
            threshold = self.config["day_night_threshold_lux"]
            
            if ambient_lux >= threshold * 50:  # Very bright (>10,000 lux)
                return "day"
            elif ambient_lux >= threshold * 5:   # Bright (>1,000 lux)
                return "day"
            elif ambient_lux >= threshold:       # Moderate light (>200 lux)
                return "twilight"
            elif ambient_lux >= 10:              # Low light
                return "dusk"
            else:                                 # Very low light
                return "night"
                
        except Exception as e:
            print(f"❌ Error determining day/night state: {e}")
            return "unknown"
    
    def save_telemetry_to_file(self, telemetry_data: Dict[str, Any]) -> bool:
        """
        Save light level telemetry data to file (append to single file)
        
        Args:
            telemetry_data: Telemetry data to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if not self.config.get("enable_data_saving", True):
                return True
            
            # Use fixed filename for all light level telemetry data
            filename = "light_level_telemetry.json"
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
            
            print(f"💾 Light level telemetry saved: {filename} (total: {len(telemetry_list)} entries)")
            return True
            
        except Exception as e:
            print(f"❌ Error saving light level telemetry: {e}")
            return False
    
    def start_monitoring(self, interval_seconds: int = None) -> Dict[str, Any]:
        """
        Start continuous light level monitoring
        
        Args:
            interval_seconds: Monitoring interval (uses config default if None)
            
        Returns:
            Status dictionary
        """
        with self.monitoring_lock:
            if self.is_monitoring:
                return {
                    "success": False,
                    "message": "Light level monitoring is already running"
                }
            
            # Update interval if provided
            if interval_seconds:
                self.config["sample_interval_seconds"] = interval_seconds
            
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            print(f"🚀 Light level monitoring started (interval: {self.config['sample_interval_seconds']}s)")
            
            return {
                "success": True,
                "message": "Light level monitoring started",
                "interval_seconds": self.config["sample_interval_seconds"]
            }
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """
        Stop continuous light level monitoring
        
        Returns:
            Status dictionary
        """
        with self.monitoring_lock:
            if not self.is_monitoring:
                return {
                    "success": False,
                    "message": "Light level monitoring is not running"
                }
            
            self.is_monitoring = False
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            print("🛑 Light level monitoring stopped")
            
            return {
                "success": True,
                "message": "Light level monitoring stopped"
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
                                db_success = save_telemetry('environmental_light_level', telemetry_values, sync_status=0)
                                if db_success:
                                    print(f"💾 Light level telemetry saved to database")
                                else:
                                    print(f"⚠️ Failed to save light level telemetry to database")
                        except Exception as db_error:
                            print(f"❌ Database save error: {db_error}")
                    
                    # Print current readings
                    values = telemetry_data.get("values", {})
                    lux = values.get("light.ambient_lux", 0)
                    uv = values.get("light.uv_index", 0)
                    temp_k = values.get("light.color_temperature_k", 0)
                    state = values.get("light.day_night_state", "unknown")
                    
                    print(f"💡 Light: {lux}lux, UV:{uv}, {temp_k}K, {state}")
                
                # Wait for next sample
                time.sleep(self.config["sample_interval_seconds"])
                
            except Exception as e:
                print(f"❌ Error in light level monitoring loop: {e}")
                time.sleep(5)  # Brief pause on error
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current service status
        
        Returns:
            Dictionary containing service status information
        """
        with self.monitoring_lock:
            return {
                "service": "light_level_monitor",
                "status": "monitoring" if self.is_monitoring else "idle",
                "data_directory": str(self.data_dir),
                "sample_interval_seconds": self.config["sample_interval_seconds"],
                "ambient_light_range_lux": self.config["ambient_light_range_lux"],
                "uv_index_range": self.config["uv_index_range"],
                "ir_level_range": self.config["ir_level_range"],
                "color_temp_range_k": self.config["color_temp_range_k"],
                "day_night_threshold_lux": self.config["day_night_threshold_lux"],
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
            print(f"✅ Light level monitor config updated: {new_config}")
            return self.config.copy()
            
        except Exception as e:
            print(f"❌ Error updating light level config: {e}")
            return self.config.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get light level summary with analysis
        
        Returns:
            Summary of current light level conditions
        """
        try:
            telemetry_data = self.get_telemetry_data()
            values = telemetry_data.get("values", {})
            
            # Analyze light conditions
            analysis = self._analyze_light_conditions(values)
            
            # Get lighting recommendations
            recommendations = self._get_lighting_recommendations(values)
            
            return {
                "timestamp": telemetry_data.get("ts", int(time.time() * 1000)),
                "current_measurements": values,
                "light_analysis": analysis,
                "lighting_recommendations": recommendations,
                "monitoring_active": self.is_monitoring
            }
            
        except Exception as e:
            print(f"❌ Error getting light level summary: {e}")
            return {}
    
    def _analyze_light_conditions(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current light conditions"""
        lux = values.get("light.ambient_lux", 0)
        uv_index = values.get("light.uv_index", 0)
        color_temp = values.get("light.color_temperature_k", 0)
        day_night = values.get("light.day_night_state", "unknown")
        
        analysis = {}
        
        # Light intensity analysis
        if lux < 10:
            analysis["intensity"] = "very_low"
            analysis["intensity_description"] = "Darkness or very dim light"
        elif lux < 200:
            analysis["intensity"] = "low"
            analysis["intensity_description"] = "Indoor lighting or dusk"
        elif lux < 1000:
            analysis["intensity"] = "moderate"
            analysis["intensity_description"] = "Typical indoor office lighting"
        elif lux < 10000:
            analysis["intensity"] = "bright"
            analysis["intensity_description"] = "Bright indoor or overcast outdoor"
        elif lux < 50000:
            analysis["intensity"] = "very_bright"
            analysis["intensity_description"] = "Direct sunlight or very bright outdoor"
        else:
            analysis["intensity"] = "extreme"
            analysis["intensity_description"] = "Direct sunlight, very bright conditions"
        
        # UV index analysis
        if uv_index <= 2:
            analysis["uv_risk"] = "low"
        elif uv_index <= 5:
            analysis["uv_risk"] = "moderate"
        elif uv_index <= 7:
            analysis["uv_risk"] = "high"
        elif uv_index <= 10:
            analysis["uv_risk"] = "very_high"
        else:
            analysis["uv_risk"] = "extreme"
        
        # Color temperature analysis
        analysis["color_temp_category"] = self._categorize_color_temperature(color_temp)
        
        # Day/night state
        analysis["day_night_state"] = day_night
        
        return analysis
    
    def _categorize_color_temperature(self, temp_k: int) -> str:
        """Categorize color temperature"""
        if temp_k < 2700:
            return "very_warm"
        elif temp_k < 3500:
            return "warm"
        elif temp_k < 4500:
            return "neutral"
        elif temp_k < 6000:
            return "cool"
        else:
            return "very_cool"
    
    def _get_lighting_recommendations(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Get lighting recommendations based on current conditions"""
        lux = values.get("light.ambient_lux", 0)
        uv_index = values.get("light.uv_index", 0)
        day_night = values.get("light.day_night_state", "unknown")
        
        recommendations = {}
        
        # General lighting recommendations
        if lux < 200:
            recommendations["general"] = "Consider additional lighting for tasks"
        elif lux > 50000:
            recommendations["general"] = "Very bright conditions, consider shade"
        else:
            recommendations["general"] = "Good lighting conditions"
        
        # UV protection recommendations
        if uv_index <= 2:
            recommendations["uv_protection"] = "No protection needed"
        elif uv_index <= 5:
            recommendations["uv_protection"] = "Wear sunglasses on bright days"
        elif uv_index <= 7:
            recommendations["uv_protection"] = "Wear sunglasses and sunscreen"
        elif uv_index <= 10:
            recommendations["uv_protection"] = "Avoid prolonged sun exposure"
        else:
            recommendations["uv_protection"] = "Seek shade, wear protective clothing"
        
        # Activity recommendations
        if day_night == "day":
            recommendations["activities"] = "Good for outdoor activities"
        elif day_night == "twilight":
            recommendations["activities"] = "Consider lighting for outdoor activities"
        else:
            recommendations["activities"] = "Use artificial lighting for activities"
        
        # Photography recommendations
        if lux > 10000 and uv_index > 3:
            recommendations["photography"] = "Excellent natural lighting for photography"
        elif lux > 1000:
            recommendations["photography"] = "Good lighting, may need flash indoors"
        else:
            recommendations["photography"] = "Low light, flash or artificial lighting recommended"
        
        return recommendations
    
    def get_color_temperature_preset(self, preset_name: str) -> Optional[int]:
        """
        Get color temperature value for a preset
        
        Args:
            preset_name: Name of the color temperature preset
            
        Returns:
            Color temperature in Kelvin, or None if preset not found
        """
        return self.color_temp_presets.get(preset_name.lower())
    
    def list_color_temperature_presets(self) -> Dict[str, int]:
        """
        List all available color temperature presets
        
        Returns:
            Dictionary of preset names and their color temperatures
        """
        return self.color_temp_presets.copy()
    
    def calculate_circadian_lighting(self, time_of_day: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calculate recommended circadian lighting parameters
        
        Args:
            time_of_day: Specific time to calculate for (uses current time if None)
            
        Returns:
            Dictionary containing recommended lighting parameters
        """
        try:
            if time_of_day is None:
                time_of_day = datetime.now()
            
            hour = time_of_day.hour
            minute = time_of_day.minute
            time_decimal = hour + minute / 60.0
            
            # Circadian lighting curve (simplified)
            if 6 <= time_decimal <= 9:  # Morning
                brightness = 0.6 + (time_decimal - 6) * 0.1
                color_temp = 3000 + (time_decimal - 6) * 500
            elif 9 < time_decimal <= 12:  # Mid-morning
                brightness = 0.9
                color_temp = 4500 + (time_decimal - 9) * 200
            elif 12 < time_decimal <= 15:  # Afternoon
                brightness = 1.0
                color_temp = 5500
            elif 15 < time_decimal <= 18:  # Late afternoon
                brightness = 0.8
                color_temp = 5000 - (time_decimal - 15) * 200
            elif 18 < time_decimal <= 21:  # Evening
                brightness = 0.6 - (time_decimal - 18) * 0.1
                color_temp = 4000 - (time_decimal - 18) * 400
            else:  # Night
                brightness = 0.1
                color_temp = 2200
            
            return {
                "time": time_of_day.strftime("%H:%M"),
                "recommended_brightness": round(brightness, 2),
                "recommended_color_temp_k": int(color_temp),
                "circadian_phase": self._get_circadian_phase(time_decimal)
            }
            
        except Exception as e:
            print(f"❌ Error calculating circadian lighting: {e}")
            return {
                "time": "unknown",
                "recommended_brightness": 0.5,
                "recommended_color_temp_k": 4000,
                "circadian_phase": "unknown"
            }
    
    def _get_circadian_phase(self, time_decimal: float) -> str:
        """Get circadian phase for given time"""
        if 6 <= time_decimal <= 10:
            return "morning_activation"
        elif 10 < time_decimal <= 14:
            return "peak_alertness"
        elif 14 < time_decimal <= 18:
            return "afternoon_plateau"
        elif 18 < time_decimal <= 22:
            return "evening_wind_down"
        else:
            return "night_rest"
