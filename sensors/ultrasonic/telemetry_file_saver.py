"""
Ultrasonic Telemetry File Saver

This module handles saving ultrasonic telemetry data to JSON files in data/telemetry/
with the format: api_ultrasonic_telemetry_<timestamp>.json
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional


# Global variable for ultrasonic telemetry data saver
ultrasonic_telemetry_saver = None


def save_ultrasonic_telemetry_to_file(ultrasonic_data: Dict[str, Any], filename: Optional[str] = None) -> bool:
    """
    Save ultrasonic telemetry data to JSON file in data/telemetry/
    
    Args:
        ultrasonic_data: Dictionary containing ultrasonic telemetry data
        filename: Optional custom filename, if not provided uses timestamp
        
    Returns:
        True if saved successfully, False otherwise
    """
    global ultrasonic_telemetry_saver
    
    try:
        # Initialize saver if not exists
        if ultrasonic_telemetry_saver is None:
            telemetry_dir = Path("data/telemetry")
            telemetry_dir.mkdir(parents=True, exist_ok=True)
            
            if filename is None:
                timestamp = int(time.time())
                filename = f"api_ultrasonic_telemetry_{timestamp}.json"
            
            file_path = telemetry_dir / filename
            ultrasonic_telemetry_saver = {
                "file_path": file_path,
                "entries": 0,
                "start_time": time.time(),
                "last_save_time": time.time()
            }
            
            # Initialize file with empty array
            with open(file_path, 'w') as f:
                json.dump([], f)
            
            print(f"📁 Ultrasonic telemetry file created: {filename}")
        
        # Read existing data
        try:
            with open(ultrasonic_telemetry_saver["file_path"], 'r') as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_data = []
        
        # Create telemetry entry with metadata
        telemetry_entry = {
            "timestamp": time.time(),
            "readable_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "entry_number": ultrasonic_telemetry_saver["entries"] + 1,
            "data": ultrasonic_data
        }
        
        # Append new entry
        existing_data.append(telemetry_entry)
        
        # Write back to file
        with open(ultrasonic_telemetry_saver["file_path"], 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        # Update metadata
        ultrasonic_telemetry_saver["entries"] += 1
        ultrasonic_telemetry_saver["last_save_time"] = time.time()
        
        # Log every 10 entries to avoid spam
        if ultrasonic_telemetry_saver["entries"] % 10 == 0:
            print(f"💾 Ultrasonic telemetry saved: {ultrasonic_telemetry_saver['entries']} entries to {ultrasonic_telemetry_saver['file_path'].name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving ultrasonic telemetry: {e}")
        return False


def get_ultrasonic_telemetry_file_status() -> Dict[str, Any]:
    """
    Get the current status of ultrasonic telemetry file saving
    
    Returns:
        Dictionary containing file status information
    """
    global ultrasonic_telemetry_saver
    
    if ultrasonic_telemetry_saver is None:
        return {
            "file_active": False,
            "message": "No ultrasonic telemetry file initialized"
        }
    
    try:
        file_size = ultrasonic_telemetry_saver["file_path"].stat().st_size
        uptime = time.time() - ultrasonic_telemetry_saver["start_time"]
        
        return {
            "file_active": True,
            "file_path": str(ultrasonic_telemetry_saver["file_path"]),
            "filename": ultrasonic_telemetry_saver["file_path"].name,
            "total_entries": ultrasonic_telemetry_saver["entries"],
            "file_size_bytes": file_size,
            "file_size_kb": round(file_size / 1024, 2),
            "uptime_seconds": round(uptime, 1),
            "last_save_time": ultrasonic_telemetry_saver["last_save_time"],
            "start_time": ultrasonic_telemetry_saver["start_time"],
            "entries_per_minute": round(ultrasonic_telemetry_saver["entries"] / (uptime / 60), 2) if uptime > 0 else 0
        }
        
    except Exception as e:
        return {
            "file_active": False,
            "error": str(e),
            "message": "Error reading ultrasonic telemetry file status"
        }


def reset_ultrasonic_telemetry_file() -> Dict[str, Any]:
    """
    Reset/create new ultrasonic telemetry file
    
    Returns:
        Dictionary containing reset result
    """
    global ultrasonic_telemetry_saver
    
    try:
        # Close current file if exists
        if ultrasonic_telemetry_saver is not None:
            old_entries = ultrasonic_telemetry_saver["entries"]
            old_filename = ultrasonic_telemetry_saver["file_path"].name
            print(f"📁 Closing ultrasonic telemetry file: {old_filename} ({old_entries} entries)")
        
        # Reset global variable
        ultrasonic_telemetry_saver = None
        
        # Create new file on next save
        return {
            "success": True,
            "message": "Ultrasonic telemetry file reset successfully",
            "previous_entries": old_entries if 'old_entries' in locals() else 0
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to reset ultrasonic telemetry file"
        }


def get_ultrasonic_telemetry_summary(limit: int = 10) -> Dict[str, Any]:
    """
    Get summary of recent ultrasonic telemetry entries
    
    Args:
        limit: Number of recent entries to include in summary
        
    Returns:
        Dictionary containing telemetry summary
    """
    global ultrasonic_telemetry_saver
    
    if ultrasonic_telemetry_saver is None:
        return {
            "summary_available": False,
            "message": "No ultrasonic telemetry file active"
        }
    
    try:
        with open(ultrasonic_telemetry_saver["file_path"], 'r') as f:
            all_data = json.load(f)
        
        if not all_data:
            return {
                "summary_available": False,
                "message": "No ultrasonic telemetry data available"
            }
        
        # Get recent entries
        recent_entries = all_data[-limit:] if len(all_data) >= limit else all_data
        
        # Calculate statistics
        total_entries = len(all_data)
        file_size = ultrasonic_telemetry_saver["file_path"].stat().st_size
        
        # Extract sensor data for analysis
        sensor_distances = {f"sensor_{i}": [] for i in range(1, 5)}
        sensor_confidences = {f"sensor_{i}": [] for i in range(1, 5)}
        temp_compensated_count = 0
        
        for entry in recent_entries:
            if "data" in entry and "values" in entry["data"]:
                values = entry["data"]["values"]
                for sensor_id in range(1, 5):
                    distance_key = f"ultrasonic.sensor_{sensor_id}.distance_cm"
                    confidence_key = f"ultrasonic.sensor_{sensor_id}.confidence"
                    temp_comp_key = f"ultrasonic.sensor_{sensor_id}.temperature_compensated"
                    
                    if distance_key in values:
                        sensor_distances[f"sensor_{sensor_id}"].append(values[distance_key])
                    if confidence_key in values:
                        sensor_confidences[f"sensor_{sensor_id}"].append(values[confidence_key])
                    if temp_comp_key in values and values[temp_comp_key]:
                        temp_compensated_count += 1
        
        # Calculate averages
        avg_distances = {}
        avg_confidences = {}
        for sensor_id in range(1, 5):
            sensor_key = f"sensor_{sensor_id}"
            if sensor_distances[sensor_key]:
                avg_distances[sensor_key] = round(sum(sensor_distances[sensor_key]) / len(sensor_distances[sensor_key]), 1)
            if sensor_confidences[sensor_key]:
                avg_confidences[sensor_key] = round(sum(sensor_confidences[sensor_key]) / len(sensor_confidences[sensor_key]), 2)
        
        return {
            "summary_available": True,
            "file_status": {
                "filename": ultrasonic_telemetry_saver["file_path"].name,
                "total_entries": total_entries,
                "file_size_kb": round(file_size / 1024, 2),
                "recent_entries_analyzed": len(recent_entries)
            },
            "sensor_analysis": {
                "average_distances_cm": avg_distances,
                "average_confidences": avg_confidences,
                "temperature_compensated_readings": temp_compensated_count,
                "temperature_compensation_rate": round(temp_compensated_count / (len(recent_entries) * 4) * 100, 1) if recent_entries else 0
            },
            "recent_entries": recent_entries
        }
        
    except Exception as e:
        return {
            "summary_available": False,
            "error": str(e),
            "message": "Failed to generate ultrasonic telemetry summary"
        }
