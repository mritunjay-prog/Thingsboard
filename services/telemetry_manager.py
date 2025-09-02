"""Telemetry Data Manager

Handles saving and managing telemetry data with proper naming conventions.
Saves telemetry data as JSON files with format: telemetry_start_epoch_end_epoch.json
"""

import json
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional
import threading
from datetime import datetime

class TelemetryManager:
    def __init__(self, data_dir: str = "data/telemetry"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Session tracking
        self.current_session = None
        self.session_data = []
        self.session_lock = threading.Lock()
        
        print(f"✅ TelemetryManager initialized - Data directory: {self.data_dir}")
    
    def start_session(self) -> int:
        """Start a new telemetry session and return the start epoch"""
        with self.session_lock:
            if self.current_session:
                print("⚠️ Session already active, ending previous session")
                self.end_session()
            
            self.current_session = int(time.time())
            self.session_data = []
            
            print(f"🚀 Started telemetry session: {self.current_session}")
            return self.current_session
    
    def add_telemetry_data(self, data: Dict[str, Any]) -> None:
        """Add telemetry data to current session"""
        with self.session_lock:
            if not self.current_session:
                print("⚠️ No active session, starting new session")
                self.start_session()
            
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = int(time.time())
            
            # Add readable timestamp for debugging
            data['readable_time'] = datetime.fromtimestamp(data['timestamp']).isoformat()
            
            self.session_data.append(data)
            print(f"📊 Added telemetry data: {len(self.session_data)} records in session")
    
    def end_session(self) -> Optional[str]:
        """End current session and save data to file"""
        with self.session_lock:
            if not self.current_session:
                print("⚠️ No active session to end")
                return None
            
            end_epoch = int(time.time())
            filename = f"telemetry_{self.current_session}_{end_epoch}.json"
            filepath = self.data_dir / filename
            
            # Prepare session metadata
            session_info = {
                "session_start": self.current_session,
                "session_end": end_epoch,
                "duration_seconds": end_epoch - self.current_session,
                "total_records": len(self.session_data),
                "start_time_readable": datetime.fromtimestamp(self.current_session).isoformat(),
                "end_time_readable": datetime.fromtimestamp(end_epoch).isoformat(),
                "telemetry_data": self.session_data
            }
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(session_info, f, indent=2, default=str)
                
                print(f"💾 Saved telemetry session: {filename}")
                print(f"📈 Session stats: {len(self.session_data)} records, {end_epoch - self.current_session}s duration")
                
                # Upload to S3 with new structure
                self._upload_to_s3(filepath)
                
                # Reset session
                self.current_session = None
                self.session_data = []
                
                return str(filepath)
                
            except Exception as e:
                print(f"❌ Error saving telemetry data: {e}")
                return None
    
    def save_single_telemetry(self, data: Dict[str, Any], custom_name: str = None) -> str:
        """Save a single telemetry record immediately"""
        timestamp = int(time.time())
        
        if custom_name:
            filename = f"{custom_name}_{timestamp}.json"
        else:
            filename = f"telemetry_single_{timestamp}.json"
        
        filepath = self.data_dir / filename
        
        # Add metadata
        telemetry_record = {
            "timestamp": timestamp,
            "readable_time": datetime.fromtimestamp(timestamp).isoformat(),
            "data": data
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(telemetry_record, f, indent=2, default=str)
            
            print(f"💾 Saved single telemetry: {filename}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Error saving single telemetry: {e}")
            return None
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get current session status"""
        with self.session_lock:
            if self.current_session:
                current_time = int(time.time())
                return {
                    "active": True,
                    "session_start": self.current_session,
                    "current_time": current_time,
                    "duration_seconds": current_time - self.current_session,
                    "records_count": len(self.session_data),
                    "start_time_readable": datetime.fromtimestamp(self.current_session).isoformat()
                }
            else:
                return {"active": False}
    
    def list_saved_files(self) -> list:
        """List all saved telemetry files"""
        try:
            files = list(self.data_dir.glob("telemetry_*.json"))
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            file_info = []
            for file in files:
                stat = file.stat()
                file_info.append({
                    "filename": file.name,
                    "path": str(file),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            
            return file_info
            
        except Exception as e:
            print(f"❌ Error listing telemetry files: {e}")
            return []
    
    def _upload_to_s3(self, filepath: Path) -> None:
        """Upload telemetry file to S3 using the new hierarchical structure"""
        try:
            # Import MediaUploadService here to avoid circular imports
            from services.media_upload_service import MediaUploadService
            
            # Initialize MediaUploadService
            upload_service = MediaUploadService()
            
            # Get device info
            upload_service.device_info = upload_service.get_device_info_by_hostname()
            
            if upload_service.device_info:
                # Upload telemetry file to S3 with telemetry folder type
                success = upload_service.upload_telemetry(filepath)
                if success:
                    print(f"☁️ Telemetry uploaded to S3: {filepath.name}")
                else:
                    print(f"⚠️ Failed to upload telemetry to S3: {filepath.name}")
            else:
                print("⚠️ Device info not available, skipping S3 upload")
                
        except Exception as e:
            print(f"⚠️ Error uploading telemetry to S3: {e}")
            # Don't fail the session save if S3 upload fails

# Global telemetry manager instance
_telemetry_manager = None

def get_telemetry_manager() -> TelemetryManager:
    """Get global telemetry manager instance"""
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager()
    return _telemetry_manager

def save_telemetry_data(data: Dict[str, Any]) -> None:
    """Convenience function to save telemetry data"""
    manager = get_telemetry_manager()
    manager.add_telemetry_data(data)

def start_telemetry_session() -> int:
    """Convenience function to start telemetry session"""
    manager = get_telemetry_manager()
    return manager.start_session()

def end_telemetry_session() -> Optional[str]:
    """Convenience function to end telemetry session"""
    manager = get_telemetry_manager()
    return manager.end_session()