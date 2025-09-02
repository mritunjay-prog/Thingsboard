#!/usr/bin/env python3
"""
Telemetry Saver

A simple program to save telemetry data to the SQLite database.
Can be imported by other programs to save sensor data.
"""

import sqlite3
import json
import time
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class TelemetrySaver:
    """Simple telemetry data saver"""
    
    def __init__(self, db_path: str = "data/database/papaya-parking-data.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"📊 TelemetrySaver initialized - Database: {self.db_path}")
    
    def _ensure_table_exists(self):
        """Ensure telemetry table exists with proper schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create telemetry table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp BIGINT NOT NULL,
                sensor_type VARCHAR(50) NOT NULL,
                data_json TEXT NOT NULL,
                sync_status INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes if they don't exist
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON telemetry(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status ON telemetry(sync_status)")
        
        conn.commit()
        conn.close()
    
    def save_telemetry(self, sensor_type: str, data: Dict[str, Any], 
                      sync_status: int = 0, timestamp: Optional[int] = None) -> bool:
        """
        Save telemetry data to database
        
        Args:
            sensor_type: Type of sensor (e.g., 'lidar', 'ultrasonic', 'camera')
            data: Telemetry data as dictionary
            sync_status: 0 for successful send, 1 for failed send
            timestamp: Unix timestamp (uses current time if None)
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            self._ensure_table_exists()
            
            if timestamp is None:
                timestamp = int(time.time())
            
            # Convert data to JSON string
            data_json = json.dumps(data, default=str)
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO telemetry (timestamp, sensor_type, data_json, sync_status)
                VALUES (?, ?, ?, ?)
            """, (timestamp, sensor_type, data_json, sync_status))
            
            conn.commit()
            conn.close()
            
            print(f"💾 Saved {sensor_type} telemetry - ID: {cursor.lastrowid}, Sync: {sync_status}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving telemetry data: {e}")
            return False
    
    def save_lidar(self, data: Dict[str, Any], sync_status: int = 0) -> bool:
        """Save LiDAR telemetry data"""
        return self.save_telemetry('lidar', data, sync_status)
    
    def save_ultrasonic(self, data: Dict[str, Any], sync_status: int = 0) -> bool:
        """Save ultrasonic telemetry data"""
        return self.save_telemetry('ultrasonic', data, sync_status)
    
    def save_camera(self, data: Dict[str, Any], sync_status: int = 0) -> bool:
        """Save camera telemetry data"""
        return self.save_telemetry('camera', data, sync_status)
    
    def save_environmental(self, data: Dict[str, Any], sync_status: int = 0) -> bool:
        """Save environmental telemetry data"""
        return self.save_telemetry('environmental', data, sync_status)
    
    def save_ble(self, data: Dict[str, Any], sync_status: int = 0) -> bool:
        """Save BLE telemetry data"""
        return self.save_telemetry('ble', data, sync_status)


# Global instance
_telemetry_saver = None

def get_telemetry_saver() -> TelemetrySaver:
    """Get global telemetry saver instance"""
    global _telemetry_saver
    if _telemetry_saver is None:
        _telemetry_saver = TelemetrySaver()
    return _telemetry_saver

def save_telemetry(sensor_type: str, data: Dict[str, Any], 
                  sync_status: int = 0) -> bool:
    """
    Convenience function to save telemetry data
    
    Args:
        sensor_type: Type of sensor
        data: Telemetry data
        sync_status: 0 for successful send, 1 for failed send
    
    Returns:
        bool: True if saved successfully
    """
    saver = get_telemetry_saver()
    return saver.save_telemetry(sensor_type, data, sync_status)


# Command line interface
def main():
    """Command line interface for testing"""
    if len(sys.argv) < 3:
        print("Usage: python telemetry_saver.py <sensor_type> <data_json> [sync_status]")
        print("Example: python telemetry_saver.py lidar '{\"distance\": 150.5}' 0")
        sys.exit(1)
    
    sensor_type = sys.argv[1]
    try:
        data = json.loads(sys.argv[2])
    except json.JSONDecodeError:
        print("❌ Invalid JSON data")
        sys.exit(1)
    
    sync_status = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    
    # Save telemetry
    success = save_telemetry(sensor_type, data, sync_status)
    
    if success:
        print("✅ Telemetry saved successfully")
        sys.exit(0)
    else:
        print("❌ Failed to save telemetry")
        sys.exit(1)


if __name__ == "__main__":
    main()

