"""
LiDAR Data Collector

This module handles LiDAR data collection, telemetry generation, and file saving.
It generates realistic LiDAR telemetry data and saves it to JSON files in the specified format.
"""

import json
import time
import random
import threading
from pathlib import Path
from typing import Dict, Any, Optional


class LidarDataCollector:
    """
    Collects LiDAR data and manages telemetry generation and file saving.
    """
    
    def __init__(self):
        self._collecting = False
        self._parameters = {}
        self._lock = threading.RLock()
        self._collection_thread = None
        self._current_telemetry = None
        self._file_path = None
        self._telemetry_entries = []
        self._start_epoch = None
        self._occupancy_detector = None
        
        # Simulation parameters for realistic data generation
        self._base_point_count = 275000
        self._point_count_variance = 15000
        self._temperature_base = 35.0
        self._temperature_variance = 5.0
        
    def set_occupancy_detector(self, occupancy_detector):
        """Set the occupancy detector reference for real-time processing"""
        with self._lock:
            self._occupancy_detector = occupancy_detector
        
    def start_collection(self, parameters: Dict[str, Any]):
        """
        Start LiDAR data collection with specified parameters.
        
        Args:
            parameters: LiDAR parameters including scan_rate_hz, resolution, range_filter, etc.
        """
        with self._lock:
            if self._collecting:
                print("⚠️ LiDAR data collection already active")
                return
                
            self._parameters = parameters.copy()
            self._collecting = True
            self._start_epoch = int(time.time())
            
            # Create data/temp directory if it doesn't exist
            temp_dir = Path("data/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create file for saving telemetry data
            filename = f"lidar_{self._start_epoch}.json"
            self._file_path = temp_dir / filename
            
            # Initialize file with empty array
            with open(self._file_path, 'w') as f:
                json.dump([], f)
            
            print(f"📁 LiDAR telemetry file created: {filename}")
            
            # Start collection thread
            self._collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
            self._collection_thread.start()
            
            print(f"🔄 LiDAR data collection started")
    
    def stop_collection(self):
        """Stop LiDAR data collection."""
        with self._lock:
            if not self._collecting:
                print("⚠️ LiDAR data collection not active")
                return
                
            self._collecting = False
            
            # Wait for collection thread to finish
            if self._collection_thread and self._collection_thread.is_alive():
                print("⏳ Waiting for LiDAR collection thread to stop...")
                # Don't join with timeout to avoid blocking the RPC response
                
            print(f"🛑 LiDAR data collection stopped")
            print(f"📊 Total telemetry entries: {len(self._telemetry_entries)}")
            if self._file_path:
                print(f"💾 Data saved to: {self._file_path.name}")
    
    def update_parameters(self, parameters: Dict[str, Any]):
        """Update collection parameters while running."""
        with self._lock:
            self._parameters.update(parameters)
            print(f"🔧 LiDAR collection parameters updated: {parameters}")
    
    def get_current_telemetry(self) -> Optional[Dict[str, Any]]:
        """
        Get the current telemetry data in ThingsBoard format.
        
        Returns:
            Dictionary containing current telemetry data or None if not collecting
        """
        with self._lock:
            if not self._collecting or not self._current_telemetry:
                return None
            return self._current_telemetry.copy()
    
    def get_summary_data(self) -> Dict[str, Any]:
        """
        Get summary data for high-frequency mode.
        
        Returns:
            Dictionary containing additional LiDAR metrics
        """
        if not self._collecting:
            return {}
            
        return {
            "lidar.collection.active": True,
            "lidar.collection.duration_sec": int(time.time() - self._start_epoch) if self._start_epoch else 0,
            "lidar.collection.entries_count": len(self._telemetry_entries),
            "lidar.collection.file_size_kb": round(self._file_path.stat().st_size / 1024, 2) if self._file_path and self._file_path.exists() else 0
        }
    
    def _collection_loop(self):
        """Main collection loop running in a separate thread."""
        print(f"🔄 LiDAR collection loop started")
        
        while self._collecting:
            try:
                # Generate telemetry data
                telemetry_data = self._generate_telemetry_data()
                
                with self._lock:
                    self._current_telemetry = telemetry_data
                    self._telemetry_entries.append(telemetry_data)
                
                # Save to file
                self._save_telemetry_to_file(telemetry_data)
                
                # Trigger real-time occupancy detection
                if self._occupancy_detector:
                    try:
                        self._occupancy_detector.process_telemetry_data(telemetry_data)
                    except Exception as occ_error:
                        print(f"⚠️ Occupancy detection error: {occ_error}")
                
                # Calculate sleep interval based on scan rate
                scan_rate = self._parameters.get('scan_rate_hz', 10.0)
                sleep_interval = 1.0 / scan_rate if scan_rate > 0 else 0.1
                
                time.sleep(sleep_interval)
                
            except Exception as e:
                print(f"❌ LiDAR collection error: {e}")
                time.sleep(1)  # Error recovery delay
        
        print(f"🔄 LiDAR collection loop ended")
    
    def _generate_telemetry_data(self) -> Dict[str, Any]:
        """
        Generate realistic LiDAR telemetry data based on current parameters.
        
        Returns:
            Dictionary containing telemetry data in the specified format
        """
        current_time = int(time.time() * 1000)
        
        # Get current parameters
        resolution = self._parameters.get('resolution', 'medium')
        range_filter = self._parameters.get('range_filter', {'min_range_m': 0.5, 'max_range_m': 30.0})
        scan_rate = self._parameters.get('scan_rate_hz', 10.0)
        
        # Generate point count based on resolution
        if resolution == 'high':
            base_points = self._base_point_count + 20000
            variance = self._point_count_variance
        elif resolution == 'low':
            base_points = self._base_point_count - 20000
            variance = self._point_count_variance // 2
        else:  # medium
            base_points = self._base_point_count
            variance = self._point_count_variance
        
        point_count = random.randint(base_points - variance, base_points + variance)
        valid_points = random.randint(int(point_count * 0.92), int(point_count * 0.98))
        
        # Generate range values based on range filter (ensure they stay within limits)
        max_range_variance = min(1.0, range_filter['max_range_m'] * 0.05)  # 5% variance or 1m, whichever is smaller
        min_range_variance = min(0.05, range_filter['min_range_m'] * 0.1)  # 10% variance or 0.05m, whichever is smaller
        
        # Generate values within the configured range limits
        max_range = range_filter['max_range_m'] + random.uniform(-max_range_variance, 0)  # Only go below max limit
        min_range = range_filter['min_range_m'] + random.uniform(0, min_range_variance)  # Only go above min limit
        
        # Ensure ranges don't violate configured limits
        max_range = min(max_range, range_filter['max_range_m'])
        min_range = max(min_range, range_filter['min_range_m'])
        
        # Generate other telemetry values
        avg_reflectivity = round(random.uniform(0.65, 0.85), 2)
        actual_scan_frequency = scan_rate + random.uniform(-0.2, 0.2)
        temperature = self._temperature_base + random.uniform(-self._temperature_variance, self._temperature_variance)
        
        # Determine status based on parameters and random factors
        status_options = ["operational", "operational", "operational", "warming_up", "calibrating"]
        status = random.choice(status_options)
        
        telemetry_data = {
            "ts": current_time,
            "values": {
                "lidar.point_count": point_count,
                "lidar.valid_points": valid_points,
                "lidar.max_range": round(max_range, 1),
                "lidar.min_range": round(min_range, 2),
                "lidar.avg_reflectivity": avg_reflectivity,
                "lidar.scan_frequency": round(actual_scan_frequency, 2),
                "lidar.temperature": round(temperature, 1),
                "lidar.status": status
            }
        }
        
        return telemetry_data
    
    def _save_telemetry_to_file(self, telemetry_data: Dict[str, Any]):
        """
        Save telemetry data to the JSON file.
        
        Args:
            telemetry_data: Telemetry data to save
        """
        try:
            # Read existing data
            if self._file_path.exists():
                with open(self._file_path, 'r') as f:
                    existing_data = json.load(f)
            else:
                existing_data = []
            
            # Append new telemetry data
            existing_data.append(telemetry_data)
            
            # Write back to file
            with open(self._file_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
        except Exception as e:
            print(f"❌ Error saving LiDAR telemetry to file: {e}")
    
    def get_collection_status(self) -> Dict[str, Any]:
        """
        Get the current collection status.
        
        Returns:
            Dictionary containing collection status information
        """
        with self._lock:
            return {
                "collecting": self._collecting,
                "start_epoch": self._start_epoch,
                "entries_count": len(self._telemetry_entries),
                "file_path": str(self._file_path) if self._file_path else None,
                "file_size_bytes": self._file_path.stat().st_size if self._file_path and self._file_path.exists() else 0,
                "parameters": self._parameters.copy()
            }

