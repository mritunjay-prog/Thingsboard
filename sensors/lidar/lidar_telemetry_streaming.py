"""
LiDAR Telemetry Streaming Service

This service handles continuous streaming of LiDAR telemetry data to ThingsBoard.
It coordinates with the data collector to get telemetry data and publishes it
via the provided callback function.
"""

import threading
import time
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# Add services to path for telemetry saver import
sys.path.append(str(Path(__file__).parent.parent.parent / 'services'))

try:
    from telemetry_saver import save_telemetry
    TELEMETRY_SAVER_AVAILABLE = True
    print("✅ Telemetry saver imported successfully for LiDAR")
except ImportError as e:
    TELEMETRY_SAVER_AVAILABLE = False
    print(f"⚠️ Telemetry saver not available for LiDAR: {e}")


class LidarTelemetryStreamingService:
    """
    Service for streaming LiDAR telemetry data continuously.
    """
    
    def __init__(self, telemetry_callback: Optional[Callable] = None):
        """
        Initialize the LiDAR telemetry streaming service.
        
        Args:
            telemetry_callback: Function to call with telemetry data for publishing
        """
        self._streaming = False
        self._telemetry_callback = telemetry_callback
        self._streaming_thread = None
        self._lock = threading.RLock()
        self._data_collector = None
        self._stream_count = 0
        self._start_time = None
        
        # Streaming configuration
        self._streaming_interval = 1.0  # Default 1 second interval
        
    def set_data_collector(self, collector):
        """Set the data collector reference"""
        with self._lock:
            self._data_collector = collector
    
    def set_telemetry_callback(self, callback: Callable):
        """Set or update the telemetry callback function"""
        with self._lock:
            self._telemetry_callback = callback
    
    def start_streaming(self, streaming_interval: float = 1.0) -> Dict[str, Any]:
        """
        Start streaming LiDAR telemetry data.
        
        Args:
            streaming_interval: Interval between telemetry transmissions in seconds
            
        Returns:
            Dictionary containing the streaming start result
        """
        with self._lock:
            try:
                if self._streaming:
                    return {
                        "success": False,
                        "message": "LiDAR telemetry streaming already active",
                        "streaming": True
                    }
                
                if not self._telemetry_callback:
                    return {
                        "success": False,
                        "message": "No telemetry callback function provided",
                        "streaming": False
                    }
                
                self._streaming_interval = streaming_interval
                self._streaming = True
                self._stream_count = 0
                self._start_time = time.time()
                
                # Start streaming thread
                self._streaming_thread = threading.Thread(target=self._streaming_loop, daemon=True)
                self._streaming_thread.start()
                
                print(f"📡 LiDAR telemetry streaming started (interval: {streaming_interval}s)")
                
                return {
                    "success": True,
                    "message": f"LiDAR telemetry streaming started with {streaming_interval}s interval",
                    "streaming": True,
                    "interval_seconds": streaming_interval
                }
                
            except Exception as e:
                print(f"❌ Failed to start LiDAR telemetry streaming: {e}")
                return {
                    "success": False,
                    "message": f"Failed to start streaming: {str(e)}",
                    "streaming": False
                }
    
    def stop_streaming(self) -> Dict[str, Any]:
        """
        Stop streaming LiDAR telemetry data.
        
        Returns:
            Dictionary containing the streaming stop result
        """
        with self._lock:
            try:
                if not self._streaming:
                    return {
                        "success": False,
                        "message": "LiDAR telemetry streaming not active",
                        "streaming": False
                    }
                
                self._streaming = False
                
                # Wait for streaming thread to finish (with timeout)
                if self._streaming_thread and self._streaming_thread.is_alive():
                    print("⏳ Waiting for LiDAR streaming thread to stop...")
                    # Don't join to avoid blocking RPC response
                
                duration = time.time() - self._start_time if self._start_time else 0
                
                print(f"📡 LiDAR telemetry streaming stopped")
                print(f"📊 Streaming stats: {self._stream_count} transmissions in {duration:.1f}s")
                
                return {
                    "success": True,
                    "message": f"LiDAR telemetry streaming stopped after {self._stream_count} transmissions",
                    "streaming": False,
                    "total_transmissions": self._stream_count,
                    "duration_seconds": round(duration, 1)
                }
                
            except Exception as e:
                print(f"❌ Failed to stop LiDAR telemetry streaming: {e}")
                return {
                    "success": False,
                    "message": f"Failed to stop streaming: {str(e)}",
                    "streaming": True
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
                "interval_seconds": self._streaming_interval,
                "total_transmissions": self._stream_count,
                "duration_seconds": round(duration, 1),
                "avg_transmission_rate": round(self._stream_count / duration, 2) if duration > 0 else 0,
                "callback_available": self._telemetry_callback is not None,
                "collector_available": self._data_collector is not None,
                "telemetry_saver_available": TELEMETRY_SAVER_AVAILABLE
            }
    
    def _streaming_loop(self):
        """Main streaming loop running in a separate thread."""
        print(f"📡 LiDAR telemetry streaming loop started")
        
        while self._streaming:
            try:
                # Get current telemetry data from collector
                if self._data_collector:
                    telemetry_data = self._data_collector.get_current_telemetry()
                    
                    if telemetry_data and self._telemetry_callback:
                        # Publish telemetry data via callback
                        self._telemetry_callback(telemetry_data)
                        
                        # Save telemetry data to database if telemetry saver is available
                        if TELEMETRY_SAVER_AVAILABLE:
                            try:
                                # Extract the values from telemetry data for database storage
                                telemetry_values = telemetry_data.get('values', {})
                                if telemetry_values:
                                    # Save to database with sync_status=0 (successfully sent)
                                    db_success = save_telemetry('lidar', telemetry_values, sync_status=0)
                                    if db_success:
                                        print(f"💾 LiDAR telemetry saved to database (stream #{self._stream_count + 1})")
                                    else:
                                        print(f"⚠️ Failed to save LiDAR telemetry to database")
                            except Exception as db_error:
                                print(f"❌ Database save error: {db_error}")
                        
                        with self._lock:
                            self._stream_count += 1
                        
                        # Debug output (reduce frequency to avoid spam)
                        if self._stream_count % 10 == 0:
                            print(f"📡 LiDAR telemetry stream #{self._stream_count}: {telemetry_data['values'].get('lidar.point_count', 0)} points")
                    else:
                        if not telemetry_data:
                            print(f"⚠️ No LiDAR telemetry data available")
                        if not self._telemetry_callback:
                            print(f"⚠️ No telemetry callback function available")
                else:
                    print(f"⚠️ No LiDAR data collector available")
                
                time.sleep(self._streaming_interval)
                
            except Exception as e:
                print(f"❌ LiDAR streaming error: {e}")
                time.sleep(1)  # Error recovery delay
        
        print(f"📡 LiDAR telemetry streaming loop ended")
    
    def update_streaming_interval(self, interval: float) -> bool:
        """
        Update the streaming interval while streaming is active.
        
        Args:
            interval: New streaming interval in seconds
            
        Returns:
            True if interval was updated successfully
        """
        with self._lock:
            if 0.1 <= interval <= 60.0:
                self._streaming_interval = interval
                print(f"🔧 LiDAR streaming interval updated to {interval}s")
                return True
            else:
                print(f"❌ Invalid streaming interval: {interval}s (must be 0.1-60.0)")
                return False

