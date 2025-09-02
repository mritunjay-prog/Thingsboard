"""
LiDAR Control Service

This service handles LiDAR control operations including start, stop, reset,
and configuration management. It manages the lifecycle of LiDAR operations
and coordinates with the telemetry streaming service.
"""

import threading
import time
import random
from typing import Dict, Any, Optional


class LidarControlService:
    """
    Service for controlling LiDAR operations and managing configuration.
    """
    
    def __init__(self):
        self._state = {
            "active": False,
            "scan_rate_hz": 10.0,
            "resolution": "medium",
            "range_filter": {
                "min_range_m": 0.5,
                "max_range_m": 30.0
            },
            "temperature": 35.0,
            "status": "idle",
            "last_started": None,
            "last_stopped": None,
            "total_scans": 0,
            "error_count": 0
        }
        self._lock = threading.RLock()
        self._telemetry_streaming_service = None
        self._data_collector = None
        
    def set_telemetry_streaming_service(self, service):
        """Set the telemetry streaming service reference"""
        with self._lock:
            self._telemetry_streaming_service = service
    
    def set_data_collector(self, collector):
        """Set the data collector reference"""
        with self._lock:
            self._data_collector = collector
            
    def start(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start LiDAR scanning operations.
        
        Args:
            config: Optional configuration parameters
            
        Returns:
            Dictionary containing the operation result and current state
        """
        with self._lock:
            try:
                # Apply configuration if provided
                if config:
                    self._apply_configuration(config)
                
                # Start LiDAR operations
                self._state["active"] = True
                self._state["status"] = "operational"
                self._state["last_started"] = int(time.time() * 1000)
                self._state["error_count"] = 0
                
                print(f"🟢 LiDAR Control Service started with config:")
                print(f"   - Scan rate: {self._state['scan_rate_hz']} Hz")
                print(f"   - Resolution: {self._state['resolution']}")
                print(f"   - Range: {self._state['range_filter']['min_range_m']}m to {self._state['range_filter']['max_range_m']}m")
                
                # Start telemetry streaming if available
                if self._telemetry_streaming_service:
                    streaming_result = self._telemetry_streaming_service.start_streaming()
                    print(f"📡 Telemetry streaming: {streaming_result}")
                
                # Start data collector if available
                if self._data_collector:
                    self._data_collector.start_collection(self._state)
                
                return self.current_state()
                
            except Exception as e:
                self._state["status"] = "error"
                self._state["error_count"] += 1
                print(f"❌ Failed to start LiDAR: {e}")
                return {
                    "active": False,
                    "status": "error",
                    "error": str(e)
                }
    
    def stop(self) -> Dict[str, Any]:
        """
        Stop LiDAR scanning operations.
        
        Returns:
            Dictionary containing the operation result and current state
        """
        with self._lock:
            try:
                # Stop data collector first
                if self._data_collector:
                    self._data_collector.stop_collection()
                
                # Stop telemetry streaming
                if self._telemetry_streaming_service:
                    streaming_result = self._telemetry_streaming_service.stop_streaming()
                    print(f"📡 Telemetry streaming stopped: {streaming_result}")
                
                # Stop LiDAR operations
                self._state["active"] = False
                self._state["status"] = "idle"
                self._state["last_stopped"] = int(time.time() * 1000)
                
                print(f"🔴 LiDAR Control Service stopped")
                print(f"   - Total scans collected: {self._state['total_scans']}")
                
                return self.current_state()
                
            except Exception as e:
                self._state["status"] = "error"
                self._state["error_count"] += 1
                print(f"❌ Failed to stop LiDAR: {e}")
                return {
                    "active": True,  # Still considered active if stop failed
                    "status": "error",
                    "error": str(e)
                }
    
    def reset(self) -> Dict[str, Any]:
        """
        Reset LiDAR control service to default state.
        
        Returns:
            Dictionary containing the reset state
        """
        with self._lock:
            try:
                # Stop first if running
                if self._state["active"]:
                    self.stop()
                
                # Reset to default configuration
                self._state.update({
                    "active": False,
                    "scan_rate_hz": 10.0,
                    "resolution": "medium",
                    "range_filter": {
                        "min_range_m": 0.5,
                        "max_range_m": 30.0
                    },
                    "status": "idle",
                    "total_scans": 0,
                    "error_count": 0,
                    "last_started": None,
                    "last_stopped": None
                })
                
                print(f"🔄 LiDAR Control Service reset to defaults")
                return self.current_state()
                
            except Exception as e:
                print(f"❌ Failed to reset LiDAR: {e}")
                return {
                    "active": False,
                    "status": "error",
                    "error": str(e)
                }
    
    def apply_config(self, scan_rate_hz: Optional[float] = None, 
                    resolution: Optional[str] = None,
                    range_filter: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Apply configuration parameters to the LiDAR service.
        
        Args:
            scan_rate_hz: Scanning frequency in Hz (1-50)
            resolution: Resolution setting ("high", "medium", "low")
            range_filter: Range filter settings with min_range_m and max_range_m
            
        Returns:
            Dictionary containing the applied configuration
        """
        with self._lock:
            config = {}
            
            if scan_rate_hz is not None:
                config['scan_rate_hz'] = scan_rate_hz
            if resolution is not None:
                config['resolution'] = resolution
            if range_filter is not None:
                config['range_filter'] = range_filter
                
            return self._apply_configuration(config)
    
    def _apply_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to apply configuration parameters.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dictionary containing the applied configuration
        """
        applied_config = {}
        
        # Validate and apply scan rate
        if 'scan_rate_hz' in config:
            scan_rate = float(config['scan_rate_hz'])
            if 1.0 <= scan_rate <= 50.0:
                self._state['scan_rate_hz'] = scan_rate
                applied_config['scan_rate_hz'] = scan_rate
            else:
                raise ValueError(f"Invalid scan rate: {scan_rate}. Must be between 1.0 and 50.0 Hz")
        
        # Validate and apply resolution
        if 'resolution' in config:
            resolution = config['resolution'].lower()
            if resolution in ['high', 'medium', 'low']:
                self._state['resolution'] = resolution
                applied_config['resolution'] = resolution
            else:
                raise ValueError(f"Invalid resolution: {resolution}. Must be 'high', 'medium', or 'low'")
        
        # Validate and apply range filter
        if 'range_filter' in config:
            range_filter = config['range_filter']
            if isinstance(range_filter, dict):
                min_range = range_filter.get('min_range_m', self._state['range_filter']['min_range_m'])
                max_range = range_filter.get('max_range_m', self._state['range_filter']['max_range_m'])
                
                if 0.1 <= min_range <= max_range <= 100.0:
                    self._state['range_filter'] = {
                        'min_range_m': float(min_range),
                        'max_range_m': float(max_range)
                    }
                    applied_config['range_filter'] = self._state['range_filter']
                else:
                    raise ValueError(f"Invalid range filter: min={min_range}, max={max_range}")
            else:
                raise ValueError("Range filter must be a dictionary with min_range_m and max_range_m")
        
        print(f"🔧 LiDAR configuration applied: {applied_config}")
        
        # Update data collector with new parameters if active
        if self._data_collector and self._state["active"]:
            self._data_collector.update_parameters(self._state)
        
        return applied_config
    
    def current_state(self) -> Dict[str, Any]:
        """
        Get the current state of the LiDAR control service.
        
        Returns:
            Dictionary containing the current state
        """
        with self._lock:
            return self._state.copy()
    
    def get_effective_generation_params(self) -> Dict[str, Any]:
        """
        Get the effective parameters for telemetry generation.
        
        Returns:
            Dictionary containing parameters for telemetry generation
        """
        with self._lock:
            return {
                "active": self._state["active"],
                "scan_rate_hz": self._state["scan_rate_hz"],
                "resolution": self._state["resolution"],
                "range_filter": self._state["range_filter"].copy(),
                "temperature": self._state["temperature"],
                "status": self._state["status"]
            }
    
    def increment_scan_count(self):
        """Increment the total scan count (called by data collector)"""
        with self._lock:
            self._state["total_scans"] += 1
    
    def update_temperature(self, temperature: float):
        """Update the LiDAR temperature reading"""
        with self._lock:
            self._state["temperature"] = temperature
    
    def get_status_summary(self) -> str:
        """Get a human-readable status summary"""
        with self._lock:
            if self._state["active"]:
                uptime = (time.time() * 1000 - self._state["last_started"]) / 1000 if self._state["last_started"] else 0
                return f"Active for {uptime:.1f}s, {self._state['total_scans']} scans, {self._state['scan_rate_hz']}Hz"
            else:
                return f"Idle, {self._state['total_scans']} total scans, {self._state['error_count']} errors"

    def timed_lidar_capture(
        self,
        capture_duration_seconds: int,
        point_cloud_format: str = "pcd",
        save_location: str = None,
        device_id: str = None,
        stop_event: threading.Event = None,
        capture_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Perform timed LiDAR data capture for a specified duration.
        
        This method captures LiDAR data (telemetry and point clouds) for a given duration.
        It's designed to be used with the sensor.capture.all RPC method.
        
        Args:
            capture_duration_seconds (int): Total duration to capture LiDAR data (in seconds)
            point_cloud_format (str): Point cloud format ("pcd", "las", or "ply")
            save_location (str, optional): Directory path where captured data should be saved
            device_id (str, optional): Device identifier for file naming
            stop_event (threading.Event, optional): Event to signal early termination
            capture_params (dict, optional): Additional LiDAR capture parameters
            
        Returns:
            dict: Results containing captured LiDAR data information
                {
                    "success": bool,
                    "scans_captured": int,
                    "telemetry_files": List[str],
                    "point_cloud_files": List[str],
                    "capture_duration_actual": float,
                    "total_points": int,
                    "error": str (if success=False)
                }
        """
        
        print(f"📡 Starting timed LiDAR capture session")
        print(f"   Duration: {capture_duration_seconds}s")
        print(f"   Point cloud format: {point_cloud_format}")
        print(f"   Save location: {save_location or 'default temp'}")
        
        # Validate point cloud format
        valid_formats = ["pcd", "las", "ply"]
        if point_cloud_format.lower() not in valid_formats:
            return {
                "success": False,
                "error": f"Invalid point cloud format: {point_cloud_format}. Must be one of {valid_formats}",
                "scans_captured": 0,
                "telemetry_files": [],
                "point_cloud_files": [],
                "capture_duration_actual": 0.0,
                "total_points": 0
            }
        
        # Initialize results
        results = {
            "success": False,
            "scans_captured": 0,
            "telemetry_files": [],
            "point_cloud_files": [],
            "capture_duration_actual": 0.0,
            "total_points": 0,
            "error": None
        }
        
        try:
            # Setup save directory
            if save_location:
                from pathlib import Path
                save_dir = Path(save_location)
                save_dir.mkdir(parents=True, exist_ok=True)
            else:
                save_dir = Path("data/temp")
                save_dir.mkdir(parents=True, exist_ok=True)
            
            # Default capture parameters
            default_params = {
                "scan_rate_hz": 10.0,
                "resolution": "medium",
                "range_filter": {
                    "min_range_m": 0.5,
                    "max_range_m": 30.0
                }
            }
            
            # Merge with user-provided parameters
            if capture_params:
                default_params.update(capture_params)
            
            # Store original state to restore later
            original_state = self.current_state()
            was_originally_active = original_state["active"]
            
            # Configure LiDAR with capture parameters
            if capture_params:
                print(f"🔧 Applying LiDAR configuration: {capture_params}")
                try:
                    self.apply_config(**capture_params)
                except Exception as cfg_err:
                    print(f"⚠️ Configuration warning: {cfg_err}")
            
            # Start LiDAR if not already active
            if not was_originally_active:
                start_result = self.start(default_params)
                if not start_result.get("active", False):
                    return {
                        "success": False,
                        "error": "Failed to start LiDAR for capture session",
                        "scans_captured": 0,
                        "telemetry_files": [],
                        "point_cloud_files": [],
                        "capture_duration_actual": 0.0,
                        "total_points": 0
                    }
                print(f"✅ LiDAR started for capture session")
            else:
                print(f"📡 Using already active LiDAR service")
            
            # Calculate timing
            scan_rate = self._state["scan_rate_hz"]
            scan_interval = 1.0 / scan_rate
            expected_scans = int(capture_duration_seconds * scan_rate)
            
            print(f"📊 Capture plan:")
            print(f"   Scan rate: {scan_rate}Hz")
            print(f"   Scan interval: {scan_interval:.2f}s")
            print(f"   Expected scans: {expected_scans}")
            
            # Track timing and data
            start_time = time.time()
            captured_files = []
            point_cloud_files = []
            total_points = 0
            
            # Import telemetry functions
            from .telemetry_file_saver import save_lidar_telemetry_to_file
            from . import get_lidar_telemetry_data
            
            scan_count = 0
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
                    # Get LiDAR telemetry data
                    lidar_data = get_lidar_telemetry_data()
                    
                    if lidar_data and "values" in lidar_data:
                        scan_count += 1
                        
                        # Save telemetry data to JSON file
                        timestamp = int(time.time() * 1000)
                        telemetry_filename = f"lidar_telemetry_{timestamp}.json"
                        telemetry_path = save_dir / telemetry_filename
                        
                        # Save with timestamp wrapper
                        telemetry_entry = {
                            "timestamp": time.time(),
                            "readable_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "device_id": device_id,
                            "scan_number": scan_count,
                            "data": lidar_data
                        }
                        
                        with open(telemetry_path, 'w') as f:
                            import json
                            json.dump(telemetry_entry, f, indent=2)
                        
                        captured_files.append(str(telemetry_path))
                        results["scans_captured"] += 1
                        
                        # Extract point count for statistics
                        point_count = lidar_data.get("values", {}).get("lidar.point_count", 0)
                        total_points += point_count
                        
                        # Generate point cloud file
                        point_cloud_file = self._generate_point_cloud_file(
                            save_dir, timestamp, point_cloud_format, 
                            lidar_data, device_id, scan_count
                        )
                        
                        if point_cloud_file:
                            point_cloud_files.append(str(point_cloud_file))
                        
                        if scan_count % 10 == 0:
                            print(f"📡 LiDAR: {scan_count} scans captured, {point_count} points in latest scan")
                    
                except Exception as scan_error:
                    print(f"❌ LiDAR scan error: {scan_error}")
                
                # Wait for next scan
                time.sleep(scan_interval)
            
            # Calculate final results
            end_time = time.time()
            results["capture_duration_actual"] = end_time - start_time
            results["telemetry_files"] = captured_files
            results["point_cloud_files"] = point_cloud_files
            results["total_points"] = total_points
            results["success"] = True
            
            print(f"✅ Timed LiDAR capture completed:")
            print(f"   Total scans: {results['scans_captured']}")
            print(f"   Telemetry files: {len(captured_files)}")
            print(f"   Point cloud files: {len(point_cloud_files)}")
            print(f"   Total points: {total_points:,}")
            print(f"   Actual duration: {results['capture_duration_actual']:.2f}s")
            print(f"   Files saved to: {save_dir}")
            
            # Restore original LiDAR state if we started it
            if not was_originally_active and self._state["active"]:
                print(f"🔄 Stopping LiDAR (was not originally active)")
                self.stop()
            
        except Exception as e:
            error_msg = f"Timed LiDAR capture failed: {str(e)}"
            print(f"❌ {error_msg}")
            results["error"] = error_msg
            results["capture_duration_actual"] = time.time() - start_time if 'start_time' in locals() else 0
        
        return results

    def _generate_point_cloud_file(
        self, 
        save_dir, 
        timestamp: int, 
        format_type: str, 
        lidar_data: Dict[str, Any], 
        device_id: str = None,
        scan_number: int = 0
    ) -> Optional[str]:
        """
        Generate a point cloud file in the specified format.
        
        Args:
            save_dir: Directory to save the file
            timestamp: Timestamp for filename
            format_type: Point cloud format (pcd, las, ply)
            lidar_data: LiDAR telemetry data
            device_id: Device identifier
            scan_number: Scan sequence number
            
        Returns:
            Path to generated file or None if failed
        """
        try:
            from pathlib import Path
            import json
            import random
            
            # Generate filename
            if device_id:
                filename = f"{device_id}_{timestamp}_scan{scan_number:04d}_pointcloud.{format_type.lower()}"
            else:
                filename = f"{timestamp}_scan{scan_number:04d}_pointcloud.{format_type.lower()}"
            
            file_path = Path(save_dir) / filename
            
            # Extract data from LiDAR telemetry
            values = lidar_data.get("values", {})
            point_count = values.get("lidar.point_count", random.randint(250000, 300000))
            range_min = values.get("lidar.range_min_m", 0.5)
            range_max = values.get("lidar.range_max_m", 30.0)
            
            # For simulation, create metadata file alongside point cloud
            metadata = {
                "format": format_type.upper(),
                "timestamp": timestamp,
                "scan_number": scan_number,
                "device_id": device_id,
                "point_count": point_count,
                "range_min_m": range_min,
                "range_max_m": range_max,
                "resolution": self._state.get("resolution", "medium"),
                "scan_rate_hz": self._state.get("scan_rate_hz", 10.0),
                "simulated": True,
                "note": f"Simulated {format_type.upper()} point cloud data. In production, actual LiDAR hardware would generate real point cloud files."
            }
            
            # Create format-specific content
            if format_type.lower() == "pcd":
                content = self._generate_pcd_content(point_count, metadata)
            elif format_type.lower() == "las":
                content = self._generate_las_content(point_count, metadata)
            elif format_type.lower() == "ply":
                content = self._generate_ply_content(point_count, metadata)
            else:
                content = f"# Simulated {format_type.upper()} point cloud\n# Points: {point_count}\n"
            
            # Write point cloud file
            with open(file_path, 'w') as f:
                f.write(content)
            
            # Write metadata file
            metadata_path = file_path.with_suffix(f'.{format_type.lower()}.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"📊 Generated {format_type.upper()} point cloud: {filename} ({point_count:,} points)")
            return str(file_path)
            
        except Exception as e:
            print(f"❌ Failed to generate point cloud file: {e}")
            return None

    def _generate_pcd_content(self, point_count: int, metadata: Dict[str, Any]) -> str:
        """Generate PCD format content"""
        return f"""# .PCD v0.7 - Point Cloud Data file format
VERSION 0.7
FIELDS x y z intensity
SIZE 4 4 4 4
TYPE F F F F
COUNT 1 1 1 1
WIDTH {point_count}
HEIGHT 1
VIEWPOINT 0 0 0 1 0 0 0
POINTS {point_count}
DATA ascii
# Simulated PCD data - {point_count:,} points
# Device: {metadata.get('device_id', 'unknown')}
# Scan: {metadata.get('scan_number', 0)}
# In production, actual point cloud data would be here
"""

    def _generate_las_content(self, point_count: int, metadata: Dict[str, Any]) -> str:
        """Generate LAS format content"""
        return f"""# LAS 1.2 Point Data Record Format
# Public Header Block
File Signature: LASF
File Source ID: 0
Project ID (GUID): {metadata.get('device_id', 'unknown')}
Version Major: 1
Version Minor: 2
System Identifier: ThingsBoard LiDAR Simulator
Generating Software: LiDAR Control Service
File Creation Day/Year: {time.strftime('%j/%Y')}
Header Size: 227
Offset to point data: 227
Number of Variable Length Records: 0
Point Data Record Format: 1
Point Data Record Length: 28
Number of point records: {point_count}
# Simulated LAS data - {point_count:,} points
# Device: {metadata.get('device_id', 'unknown')}
# Scan: {metadata.get('scan_number', 0)}
# In production, actual LAS binary data would follow
"""

    def _generate_ply_content(self, point_count: int, metadata: Dict[str, Any]) -> str:
        """Generate PLY format content"""
        return f"""ply
format ascii 1.0
comment Simulated PLY point cloud data
comment Device: {metadata.get('device_id', 'unknown')}
comment Scan: {metadata.get('scan_number', 0)}
comment Points: {point_count:,}
element vertex {point_count}
property float x
property float y
property float z
property float intensity
end_header
# Simulated PLY data - {point_count:,} points
# In production, actual point coordinates would be listed here
"""

    def estimate_lidar_capture_session(
        self,
        capture_duration_seconds: int,
        scan_rate_hz: float = None
    ) -> Dict[str, Any]:
        """
        Estimate the results of a timed LiDAR capture session without actually capturing.
        
        Args:
            capture_duration_seconds (int): Total duration to capture LiDAR data
            scan_rate_hz (float, optional): Override scan rate (uses current if None)
            
        Returns:
            dict: Estimated capture session results
        """
        
        effective_scan_rate = scan_rate_hz or self._state["scan_rate_hz"]
        estimated_scans = int(capture_duration_seconds * effective_scan_rate)
        estimated_points_per_scan = 275000  # Average point count
        estimated_total_points = estimated_scans * estimated_points_per_scan
        
        # Estimate file sizes (approximate)
        telemetry_size_per_file = 2048  # ~2KB per telemetry JSON
        pcd_size_per_file = estimated_points_per_scan * 50  # ~50 bytes per point in ASCII
        
        return {
            "estimated_scans": estimated_scans,
            "estimated_total_points": estimated_total_points,
            "estimated_points_per_scan": estimated_points_per_scan,
            "scan_rate_hz": effective_scan_rate,
            "scan_interval_seconds": 1.0 / effective_scan_rate,
            "estimated_telemetry_files": estimated_scans,
            "estimated_point_cloud_files": estimated_scans,
            "estimated_telemetry_size_mb": (estimated_scans * telemetry_size_per_file) / (1024 * 1024),
            "estimated_point_cloud_size_mb": (estimated_scans * pcd_size_per_file) / (1024 * 1024),
            "capture_efficiency": 100.0  # LiDAR captures continuously
        }

