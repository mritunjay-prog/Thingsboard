"""
Ultrasonic Streaming Service

This service handles continuous streaming of ultrasonic telemetry data to ThingsBoard.
It coordinates with the proximity detector to provide real-time distance monitoring.
"""

import threading
import time
import random
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# Add services to path for telemetry saver import
sys.path.append(str(Path(__file__).parent.parent.parent / 'services'))

try:
    from telemetry_saver import save_telemetry
    TELEMETRY_SAVER_AVAILABLE = True
    print("✅ Telemetry saver imported successfully for ultrasonic")
except ImportError as e:
    TELEMETRY_SAVER_AVAILABLE = False
    print(f"⚠️ Telemetry saver not available for ultrasonic: {e}")


class UltrasonicStreamingService:
    """
    Service for streaming ultrasonic telemetry data continuously.
    """
    
    def __init__(self, telemetry_callback: Optional[Callable] = None):
        """
        Initialize the ultrasonic streaming service.
        
        Args:
            telemetry_callback: Function to call with telemetry data for publishing
        """
        self._streaming = False
        self._telemetry_callback = telemetry_callback
        self._streaming_thread = None
        self._lock = threading.RLock()
        self._stream_count = 0
        self._start_time = None
        self._proximity_detector = None
        
        # Streaming configuration
        self._streaming_interval = 2.0  # Default 2 second interval
        
        # Sensor configuration
        self._sensors_config = {
            "sensors_enabled": 4,  # Number of ultrasonic sensors
            "min_range_cm": 5.0,   # Minimum range in cm
            "max_range_cm": 400.0, # Maximum range in cm
            "temperature_compensation": True  # Enable temperature compensation
        }
        
    def set_telemetry_callback(self, callback: Callable):
        """Set or update the telemetry callback function"""
        with self._lock:
            self._telemetry_callback = callback
    
    def set_proximity_detector(self, detector):
        """Set the proximity detector reference"""
        with self._lock:
            self._proximity_detector = detector
    
    def start_streaming(self, streaming_interval: float = 2.0) -> Dict[str, Any]:
        """
        Start streaming ultrasonic telemetry data.
        
        Args:
            streaming_interval: Interval between telemetry transmissions in seconds
            
        Returns:
            Dictionary containing the streaming start result
        """
        with self._lock:
            if self._streaming:
                return {
                    "success": False,
                    "message": "Ultrasonic streaming already active"
                }
            
            self._streaming_interval = streaming_interval
            self._streaming = True
            self._stream_count = 0
            self._start_time = time.time()
            
            # Start streaming thread
            self._streaming_thread = threading.Thread(target=self._streaming_loop, daemon=True)
            self._streaming_thread.start()
            
            print(f"📡 Ultrasonic telemetry streaming started")
            
            return {
                "success": True,
                "message": "Ultrasonic streaming started",
                "streaming_interval": self._streaming_interval
            }
    
    def stop_streaming(self) -> Dict[str, Any]:
        """
        Stop streaming ultrasonic telemetry data.
        
        Returns:
            Dictionary containing the streaming stop result
        """
        with self._lock:
            if not self._streaming:
                return {
                    "success": False,
                    "message": "Ultrasonic streaming not active"
                }
            
            self._streaming = False
            duration = time.time() - self._start_time if self._start_time else 0
            
            print(f"📡 Ultrasonic telemetry streaming stopped")
            
            return {
                "success": True,
                "message": f"Ultrasonic streaming stopped after {self._stream_count} transmissions",
                "transmissions_sent": self._stream_count,
                "duration_seconds": round(duration, 1)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current streaming status.
        
        Returns:
            Dictionary containing streaming status information
        """
        with self._lock:
            duration = time.time() - self._start_time if self._start_time and self._streaming else 0
            
            return {
                "streaming": self._streaming,
                "streaming_interval": self._streaming_interval,
                "transmissions_sent": self._stream_count,
                "duration_seconds": round(duration, 1),
                "callback_available": self._telemetry_callback is not None,
                "sensors_enabled": self._sensors_config["sensors_enabled"],
                "telemetry_saver_available": TELEMETRY_SAVER_AVAILABLE
            }
    
    def _streaming_loop(self):
        """Main streaming loop running in a separate thread."""
        print(f"🔊 Ultrasonic streaming loop started (interval: {self._streaming_interval}s)")
        
        while self._streaming:
            try:
                # Generate and send telemetry data
                telemetry_data = self._generate_ultrasonic_telemetry()
                
                if self._telemetry_callback and telemetry_data:
                    # Send via MQTT callback
                    self._telemetry_callback(telemetry_data)
                    
                    # Save telemetry data to database if telemetry saver is available
                    if TELEMETRY_SAVER_AVAILABLE:
                        try:
                            # Extract the values from telemetry data for database storage
                            telemetry_values = telemetry_data.get('values', {})
                            if telemetry_values:
                                # Save to database with sync_status=0 (successfully sent)
                                db_success = save_telemetry('ultrasonic', telemetry_values, sync_status=0)
                                if db_success:
                                    print(f"💾 Ultrasonic telemetry saved to database (stream #{self._stream_count + 1})")
                                else:
                                    print(f"⚠️ Failed to save ultrasonic telemetry to database")
                        except Exception as db_error:
                            print(f"❌ Database save error: {db_error}")
                    
                    # Save to file
                    try:
                        from .telemetry_file_saver import save_ultrasonic_telemetry_to_file
                        save_ultrasonic_telemetry_to_file(telemetry_data)
                    except Exception as save_error:
                        print(f"⚠️ Failed to save ultrasonic telemetry to file: {save_error}")
                    
                    # Trigger real-time proximity detection
                    if self._proximity_detector:
                        try:
                            self._proximity_detector.process_telemetry_data(telemetry_data)
                        except Exception as prox_error:
                            print(f"⚠️ Proximity detection error: {prox_error}")
                    
                    with self._lock:
                        self._stream_count += 1
                    
                    # Debug output every 10 transmissions
                    if self._stream_count % 10 == 0:
                        print(f"📡 Ultrasonic telemetry sent #{self._stream_count}")
                
                time.sleep(self._streaming_interval)
                
            except Exception as e:
                print(f"❌ Ultrasonic streaming error: {e}")
                time.sleep(1)  # Error recovery delay
        
        print(f"📡 Ultrasonic streaming loop ended")
    
    def _generate_ultrasonic_telemetry(self) -> Dict[str, Any]:
        """
        Generate ultrasonic telemetry data with temperature compensation.
        
        Returns:
            Dictionary containing ultrasonic telemetry data in the specified format
        """
        current_time = int(time.time() * 1000)
        
        # Generate telemetry data structure
        telemetry_data = {
            "ts": current_time,
            "values": {}
        }
        
        # Generate data for each active sensor
        for sensor_id in range(1, self._sensors_config["sensors_enabled"] + 1):
            # Generate realistic distance readings within configured range
            min_range = self._sensors_config["min_range_cm"]
            max_range = self._sensors_config["max_range_cm"]
            distance = round(random.uniform(min_range, max_range), 1)
            
            # Calculate confidence based on distance and environmental factors
            # Closer objects generally have higher confidence
            if distance < 50:
                confidence = round(random.uniform(0.95, 0.99), 2)
            elif distance < 150:
                confidence = round(random.uniform(0.90, 0.97), 2)
            elif distance < 300:
                confidence = round(random.uniform(0.85, 0.94), 2)
            else:
                confidence = round(random.uniform(0.80, 0.91), 2)
            
            # Temperature compensation status
            temp_compensated = self._sensors_config["temperature_compensation"]
            
            # Add sensor data to telemetry values
            telemetry_data["values"].update({
                f"ultrasonic.sensor_{sensor_id}.distance_cm": distance,
                f"ultrasonic.sensor_{sensor_id}.confidence": confidence,
                f"ultrasonic.sensor_{sensor_id}.temperature_compensated": temp_compensated
            })
        
        return telemetry_data
    
    def update_sensor_config(self, config: Dict[str, Any]):
        """
        Update sensor configuration parameters.
        
        Args:
            config: Dictionary containing sensor configuration updates
        """
        with self._lock:
            if "sensors_enabled" in config:
                sensors_enabled = int(config["sensors_enabled"])
                if 1 <= sensors_enabled <= 4:
                    self._sensors_config["sensors_enabled"] = sensors_enabled
            
            if "max_range_cm" in config:
                max_range = float(config["max_range_cm"])
                if 10 <= max_range <= 500:
                    self._sensors_config["max_range_cm"] = max_range
            
            if "min_range_cm" in config:
                min_range = float(config["min_range_cm"])
                if 1 <= min_range <= 50:
                    self._sensors_config["min_range_cm"] = min_range
            
            if "temperature_compensation" in config:
                self._sensors_config["temperature_compensation"] = bool(config["temperature_compensation"])
            
            if "noise_filtering" in config:
                self._sensors_config["noise_filtering"] = bool(config["noise_filtering"])
            
            print(f"🔧 Ultrasonic streaming config updated: {config}")
    
    def get_current_telemetry(self) -> Optional[Dict[str, Any]]:
        """
        Get current telemetry data without streaming.
        
        Returns:
            Dictionary containing current ultrasonic telemetry data
        """
        return self._generate_ultrasonic_telemetry()
