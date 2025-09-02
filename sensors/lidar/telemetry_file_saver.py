"""
LiDAR Telemetry File Saver

This module handles saving LiDAR telemetry data to JSON files in the data/telemetry directory.
This is used for backward compatibility with the existing API telemetry saving system.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional


# Global variable for LiDAR telemetry data saver
_lidar_telemetry_saver = None


def save_lidar_telemetry_to_file(lidar_data: Dict[str, Any], filename: Optional[str] = None) -> bool:
    """
    Save LiDAR telemetry data to JSON file in data/telemetry directory.
    
    This function maintains compatibility with the existing API telemetry saving system.
    It saves telemetry data in the format expected by the original API.
    
    Args:
        lidar_data: LiDAR telemetry data in ThingsBoard format
        filename: Optional filename (will be auto-generated if not provided)
        
    Returns:
        True if saved successfully, False otherwise
    """
    global _lidar_telemetry_saver
    
    try:
        # Initialize saver if not exists
        if _lidar_telemetry_saver is None:
            telemetry_dir = Path("data/telemetry")
            telemetry_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename with timestamp if not provided
            if filename is None:
                timestamp = int(time.time())
                filename = f"api_lidar_telemetry_{timestamp}.json"
            
            file_path = telemetry_dir / filename
            _lidar_telemetry_saver = {
                "file_path": file_path,
                "entries": 0
            }
            
            # Initialize file with empty array
            with open(file_path, 'w') as f:
                json.dump([], f)
        
        # Read existing data
        try:
            with open(_lidar_telemetry_saver["file_path"], 'r') as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_data = []
        
        # Add new telemetry entry with timestamp
        telemetry_entry = {
            "timestamp": time.time(),
            "readable_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "data": lidar_data
        }
        existing_data.append(telemetry_entry)
        
        # Write back to file
        with open(_lidar_telemetry_saver["file_path"], 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        _lidar_telemetry_saver["entries"] += 1
        print(f"✅ LiDAR telemetry saved to {_lidar_telemetry_saver['file_path'].name} (total: {_lidar_telemetry_saver['entries']} entries)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving LiDAR telemetry: {e}")
        return False


def get_lidar_telemetry_file_status() -> Dict[str, Any]:
    """
    Get current LiDAR telemetry file status.
    
    Returns:
        Dictionary containing file status information
    """
    global _lidar_telemetry_saver
    if _lidar_telemetry_saver:
        return {
            "file_path": str(_lidar_telemetry_saver["file_path"]),
            "total_entries": _lidar_telemetry_saver["entries"],
            "file_size_bytes": _lidar_telemetry_saver["file_path"].stat().st_size if _lidar_telemetry_saver["file_path"].exists() else 0
        }
    return {"status": "No LiDAR telemetry file active"}


def reset_lidar_telemetry_saver():
    """Reset the LiDAR telemetry saver state."""
    global _lidar_telemetry_saver
    _lidar_telemetry_saver = None
