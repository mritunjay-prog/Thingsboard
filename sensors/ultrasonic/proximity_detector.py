"""
Ultrasonic-based Proximity Alert Detector

This module provides proximity alert functionality based on ultrasonic sensor data.
It analyzes sensor distance readings to determine if objects are approaching within threshold distances.

NOTE: Proximity alert telemetry database saving is currently disabled.
Only general ultrasonic telemetry data is being saved to the database.
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
    print("✅ Telemetry saver imported successfully for ultrasonic proximity detector")
except ImportError as e:
    TELEMETRY_SAVER_AVAILABLE = False
    print(f"⚠️ Telemetry saver not available for ultrasonic proximity detector: {e}")


class ProximityDetector:
    """
    Detects proximity alerts based on ultrasonic sensor distance analysis.
    """
    
    def __init__(self, telemetry_callback: Optional[Callable] = None):
        """
        Initialize the proximity detector.
        
        Args:
            telemetry_callback: Function to call with proximity alert telemetry data
        """
        self._detecting = False
        self._telemetry_callback = telemetry_callback
        self._detection_thread = None
        self._lock = threading.RLock()
        self._detection_count = 0
        self._start_time = None
        
        # Detection parameters - configurable thresholds per sensor
        self._detection_interval = 0.5  # Check every 500ms for proximity alerts
        self._sensor_thresholds = {
            1: 50,  # cm - sensor 1 threshold
            2: 50,  # cm - sensor 2 threshold  
            3: 50,  # cm - sensor 3 threshold
            4: 50   # cm - sensor 4 threshold
        }
        self._confidence_threshold = 0.8  # Minimum confidence for valid reading
        self._alert_duration_tracking = {}  # Track alert durations per sensor
        self._real_time_mode = True  # Enable real-time detection
        
    def set_telemetry_callback(self, callback: Callable):
        """Set or update the telemetry callback function"""
        with self._lock:
            self._telemetry_callback = callback
    
    def start_detection(self) -> Dict[str, Any]:
        """
        Start proximity detection.
        
        Returns:
            Dictionary containing the start result
        """
        with self._lock:
            if self._detecting:
                return {
                    "success": False,
                    "message": "Proximity detection already active"
                }
            
            self._detecting = True
            self._detection_count = 0
            self._start_time = time.time()
            self._alert_duration_tracking = {}
            
            # Start detection thread
            self._detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self._detection_thread.start()
            
            print(f"🚨 Proximity detection started")
            print(f"   - Detection interval: {self._detection_interval}s")
            print(f"   - Sensor thresholds: {self._sensor_thresholds}")
            print(f"   - Confidence threshold: {self._confidence_threshold}")
            
            return {
                "success": True,
                "message": "Proximity detection started successfully",
                "detection_interval": self._detection_interval,
                "sensor_thresholds": self._sensor_thresholds.copy(),
                "confidence_threshold": self._confidence_threshold
            }
    
    def stop_detection(self) -> Dict[str, Any]:
        """
        Stop proximity detection.
        
        Returns:
            Dictionary containing the stop result
        """
        with self._lock:
            if not self._detecting:
                return {
                    "success": False,
                    "message": "Proximity detection not active"
                }
            
            self._detecting = False
            duration = time.time() - self._start_time if self._start_time else 0
            
            print(f"🚨 Proximity detection stopped")
            print(f"   - Total alerts: {self._detection_count}")
            print(f"   - Duration: {duration:.1f}s")
            
            return {
                "success": True,
                "message": f"Proximity detection stopped after {self._detection_count} alerts",
                "alerts_detected": self._detection_count,
                "duration_seconds": round(duration, 1)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current detection status.
        
        Returns:
            Dictionary containing status information
        """
        with self._lock:
            duration = time.time() - self._start_time if self._start_time and self._detecting else 0
            
            return {
                "detecting": self._detecting,
                "alerts_detected": self._detection_count,
                "duration_seconds": round(duration, 1),
                "callback_available": self._telemetry_callback is not None,
                "detection_interval": self._detection_interval,
                "sensor_thresholds": self._sensor_thresholds.copy(),
                "confidence_threshold": self._confidence_threshold,
                "real_time_mode": self._real_time_mode,
                "telemetry_saver_available": TELEMETRY_SAVER_AVAILABLE,
                "proximity_telemetry_saving": False  # Currently disabled
            }
    
    def process_telemetry_data(self, telemetry_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process telemetry data immediately for real-time proximity detection.
        This method can be called directly when new telemetry data is available.
        
        Args:
            telemetry_data: Ultrasonic telemetry data to analyze
            
        Returns:
            Proximity alert result or None if detection is not active
        """
        if not self._detecting:
            return None
            
        try:
            if telemetry_data and 'values' in telemetry_data:
                # Analyze each sensor for proximity alerts
                proximity_alerts = []
                
                for sensor_id in range(1, 5):
                    distance_key = f"ultrasonic.sensor_{sensor_id}.distance_cm"
                    confidence_key = f"ultrasonic.sensor_{sensor_id}.confidence"
                    
                    distance = telemetry_data['values'].get(distance_key, 999)
                    confidence = telemetry_data['values'].get(confidence_key, 0)
                    
                    # Check if this sensor has a proximity alert
                    alert_data = self._analyze_proximity(sensor_id, distance, confidence)
                    if alert_data:
                        proximity_alerts.append(alert_data)
                
                # If we have proximity alerts, generate telemetry data
                if proximity_alerts:
                    # For simplicity, we'll send the alert for the closest object
                    closest_alert = min(proximity_alerts, key=lambda x: x["distance_cm"])
                    
                    # Create proximity alert result
                    proximity_result = {
                        "ts": telemetry_data.get('ts', int(time.time() * 1000)),
                        "values": {
                            "ultrasonic.proximity_alert.sensor_id": closest_alert["sensor_id"],
                            "ultrasonic.proximity_alert.distance_cm": closest_alert["distance_cm"],
                            "ultrasonic.proximity_alert.threshold_cm": closest_alert["threshold_cm"],
                            "ultrasonic.proximity_alert.duration_ms": closest_alert["duration_ms"],
                            "ultrasonic.proximity_alert.object_approaching": closest_alert["object_approaching"]
                        }
                    }
                    
                    # Update internal state
                    with self._lock:
                        self._detection_count += 1
                    
                    # Send via callback if available - ONLY when proximity is detected
                    if self._telemetry_callback:
                        self._telemetry_callback(proximity_result)
                        
                        # Save proximity alert telemetry data to database if telemetry saver is available
                        # COMMENTED OUT: Only saving general ultrasonic telemetry for now
                        # if TELEMETRY_SAVER_AVAILABLE:
                        #     try:
                        #         # Extract the values from proximity result for database storage
                        #         proximity_values = proximity_result.get('values', {})
                        #         if proximity_values:
                        #             # Save to database with sync_status=0 (successfully sent)
                        #             db_success = save_telemetry('ultrasonic_proximity', proximity_values, sync_status=0)
                        #             if db_success:
                        #                 print(f"💾 Ultrasonic proximity telemetry saved to database (alert #{self._detection_count})")
                        #             else:
                        #                 print(f"⚠️ Failed to save ultrasonic proximity telemetry to database")
                        #     except Exception as db_error:
                        #         print(f"❌ Database save error: {db_error}")
                        
                        sensor_id = closest_alert["sensor_id"]
                        distance = closest_alert["distance_cm"]
                        threshold = closest_alert["threshold_cm"]
                        print(f"🚨 PROXIMITY ALERT: Sensor {sensor_id} detected object at {distance}cm (threshold: {threshold}cm) - telemetry published!")
                    
                    return proximity_result
                
        except Exception as e:
            print(f"❌ Proximity detection error: {e}")
            
        return None
    
    def update_sensor_threshold(self, sensor_id: int, threshold_cm: float) -> bool:
        """
        Update proximity threshold for a specific sensor.
        
        Args:
            sensor_id: Sensor ID (1-4)
            threshold_cm: New threshold distance in centimeters
            
        Returns:
            True if threshold was updated, False otherwise
        """
        with self._lock:
            if 1 <= sensor_id <= 4 and 5 <= threshold_cm <= 200:
                self._sensor_thresholds[sensor_id] = threshold_cm
                print(f"🔧 Sensor {sensor_id} proximity threshold updated to {threshold_cm}cm")
                return True
            return False
    
    def update_confidence_threshold(self, confidence: float) -> bool:
        """
        Update minimum confidence threshold for valid readings.
        
        Args:
            confidence: New confidence threshold (0.0 to 1.0)
            
        Returns:
            True if threshold was updated, False otherwise
        """
        with self._lock:
            if 0.0 <= confidence <= 1.0:
                self._confidence_threshold = confidence
                print(f"🔧 Confidence threshold updated to {confidence}")
                return True
            return False
    
    def _detection_loop(self):
        """Main detection loop running in a separate thread."""
        print(f"🚨 Proximity detection loop started")
        
        while self._detecting:
            try:
                # Import here to avoid circular imports
                from . import get_ultrasonic_telemetry_data
                
                # Get current ultrasonic telemetry data
                telemetry_data = get_ultrasonic_telemetry_data()
                
                if telemetry_data:
                    # Process the telemetry data for proximity detection
                    self.process_telemetry_data(telemetry_data)
                
                time.sleep(self._detection_interval)
                
            except Exception as e:
                print(f"❌ Proximity detection loop error: {e}")
                time.sleep(1)  # Error recovery delay
        
        print(f"🚨 Proximity detection loop ended")
    
    def _analyze_proximity(self, sensor_id: int, distance: float, confidence: float) -> Optional[Dict[str, Any]]:
        """
        Analyze sensor data for proximity alerts.
        
        Args:
            sensor_id: ID of the sensor (1-4)
            distance: Distance reading in cm
            confidence: Confidence level of the reading (0.0-1.0)
            
        Returns:
            Alert data dictionary if proximity detected, None otherwise
        """
        # Check if we have a valid reading
        if confidence < self._confidence_threshold:
            return None
        
        threshold = self._sensor_thresholds.get(sensor_id, 50)
        
        # Check if object is within proximity threshold
        if distance <= threshold:
            # Track alert duration for this sensor
            current_time = time.time()
            sensor_key = f"sensor_{sensor_id}"
            
            if sensor_key not in self._alert_duration_tracking:
                # First time detecting proximity for this sensor
                self._alert_duration_tracking[sensor_key] = current_time
                duration_ms = 0
            else:
                # Calculate how long this proximity alert has been active
                start_time = self._alert_duration_tracking[sensor_key]
                duration_ms = int((current_time - start_time) * 1000)
            
            # Determine if object is approaching (for demo, we'll simulate this)
            # In real implementation, this would compare with previous readings
            object_approaching = random.choice([True, False])  # Simulate approach detection
            
            return {
                "sensor_id": sensor_id,
                "distance_cm": distance,
                "threshold_cm": threshold,
                "duration_ms": duration_ms,
                "object_approaching": object_approaching,
                "confidence": confidence
            }
        else:
            # Object moved away, clear duration tracking for this sensor
            sensor_key = f"sensor_{sensor_id}"
            if sensor_key in self._alert_duration_tracking:
                del self._alert_duration_tracking[sensor_key]
        
        return None


# Global instance
_proximity_detector = None

def get_proximity_detector(telemetry_callback=None):
    """Get the global proximity detector instance"""
    global _proximity_detector
    if _proximity_detector is None:
        _proximity_detector = ProximityDetector(telemetry_callback)
    return _proximity_detector
