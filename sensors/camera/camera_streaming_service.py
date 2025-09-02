#!/usr/bin/env python3

import os
import time
import json
import threading
import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import signal

class CameraStreamingService:
    """
    Camera streaming service for handling live video streaming operations.
    Supports RTSP, WebRTC, and HLS streaming with S3 upload integration.
    """
    
    def __init__(self, temp_dir: str = "data/temp"):
        """
        Initialize the camera streaming service
        
        Args:
            temp_dir: Directory to store temporary streaming files
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Active streams tracking
        self.active_streams = {}  # stream_id -> stream_info
        self.stream_processes = {}  # stream_id -> subprocess
        self.stream_lock = threading.Lock()
        
        # Stream configuration defaults
        self.default_stream_config = {
            "stream_type": "rtsp",
            "resolution": "720p",
            "fps": 30,
            "bitrate_kbps": 1024,
            "audio_enabled": False,
            "max_duration_seconds": 300
        }
        
        # Resolution mappings
        self.video_resolutions = {
            "1080p": "1920x1080",
            "720p": "1280x720",
            "480p": "854x480"
        }
        
        print("📺 Camera streaming service initialized")
    
    def start_stream(self, params: Dict[str, Any] = None, device_id: str = None) -> Dict[str, Any]:
        """
        Start a video stream with specified parameters
        
        Args:
            params: Stream parameters (type, resolution, destination, etc.)
            device_id: Device identifier for stream naming and endpoints
            
        Returns:
            Dictionary containing stream results and information
        """
        if params is None:
            params = {}
        
        # Merge with defaults
        config = {**self.default_stream_config, **params}
        
        try:
            with self.stream_lock:
                # Generate unique stream ID
                stream_id = f"stream_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
                timestamp = int(time.time() * 1000)
                
                print(f"📺 Starting video stream: {stream_id}")
                print(f"📋 Configuration: {config}")
                
                # Process destination configuration
                destination = config.get("destination", {})
                destination_type = destination.get("type", "rtsp_server")
                endpoint = destination.get("endpoint", "")
                
                # Replace [DEVICE_ID] placeholder in endpoint
                if device_id and "[DEVICE_ID]" in endpoint:
                    endpoint = endpoint.replace("[DEVICE_ID]", device_id)
                
                # Start streaming process
                stream_process, stream_url = self._start_streaming_process(
                    stream_id, config, destination_type, endpoint, device_id
                )
                
                if not stream_process:
                    return {
                        "success": False,
                        "error": "Failed to start streaming process",
                        "timestamp": timestamp
                    }
                
                # Store stream information
                stream_info = {
                    "stream_id": stream_id,
                    "stream_url": stream_url,
                    "status": "active",
                    "viewers": 1,  # Initial viewer count
                    "bandwidth_kbps": config["bitrate_kbps"],
                    "started_at": timestamp,
                    "device_id": device_id,
                    "configuration": config,
                    "destination": destination
                }
                
                self.active_streams[stream_id] = stream_info
                self.stream_processes[stream_id] = stream_process
                
                print(f"✅ Stream started successfully: {stream_id}")
                print(f"📡 Stream URL: {stream_url}")
                
                # Start duration monitoring if max_duration is specified
                max_duration = config.get("max_duration_seconds")
                if max_duration:
                    self._start_duration_monitor(stream_id, max_duration)
                
                # Prepare response
                response = {
                    "success": True,
                    "stream_info": {
                        "stream_id": stream_id,
                        "stream_url": stream_url,
                        "status": "active",
                        "viewers": 1,
                        "bandwidth_kbps": config["bitrate_kbps"],
                        "started_at": timestamp
                    }
                }
                
                return response
                
        except Exception as e:
            print(f"❌ Stream start error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": int(time.time() * 1000)
            }
    
    def stop_stream(self, params: Dict[str, Any] = None, device_id: str = None) -> Dict[str, Any]:
        """
        Stop a video stream and optionally save recording
        
        Args:
            params: Stop parameters (stream_id, save_recording, s3_upload)
            device_id: Device identifier for S3 paths
            
        Returns:
            Dictionary containing stop results and file information
        """
        if params is None:
            params = {}
        
        stream_id = params.get("stream_id")
        save_recording = params.get("save_recording", False)
        s3_upload_config = params.get("s3_upload", {})
        
        try:
            with self.stream_lock:
                timestamp = int(time.time() * 1000)
                
                if not stream_id:
                    return {
                        "success": False,
                        "error": "stream_id is required",
                        "timestamp": timestamp
                    }
                
                # Check if stream exists
                if stream_id not in self.active_streams:
                    return {
                        "success": False,
                        "error": f"Stream {stream_id} not found or already stopped",
                        "timestamp": timestamp
                    }
                
                print(f"🛑 Stopping video stream: {stream_id}")
                
                # Get stream info
                stream_info = self.active_streams[stream_id]
                stream_process = self.stream_processes.get(stream_id)
                
                # Stop the streaming process
                if stream_process:
                    self._stop_streaming_process(stream_process)
                
                # Prepare base response
                response = {
                    "success": True,
                    "data": {
                        "stream_id": stream_id,
                        "status": "stopped"
                    },
                    "timestamp": timestamp
                }
                
                # Handle recording save if requested
                if save_recording:
                    recording_result = self._save_stream_recording(
                        stream_id, stream_info, s3_upload_config, device_id
                    )
                    
                    if recording_result:
                        response["data"].update(recording_result)
                
                # Clean up stream data
                self.active_streams.pop(stream_id, None)
                self.stream_processes.pop(stream_id, None)
                
                print(f"✅ Stream stopped successfully: {stream_id}")
                
                return response
                
        except Exception as e:
            print(f"❌ Stream stop error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": int(time.time() * 1000)
            }
    
    def _start_streaming_process(self, stream_id: str, config: Dict[str, Any], 
                                destination_type: str, endpoint: str, device_id: str) -> tuple:
        """
        Start the actual streaming process based on configuration
        
        Returns:
            Tuple of (process, stream_url)
        """
        try:
            resolution = self.video_resolutions.get(config["resolution"], "1280x720")
            width, height = resolution.split('x')
            
            # Build base ffmpeg command
            cmd = self._build_ffmpeg_command(config, width, height, destination_type, endpoint, stream_id)
            
            if not cmd:
                print(f"❌ Failed to build streaming command for {destination_type}")
                return None, None
            
            print(f"📺 Executing streaming command: {' '.join(cmd)}")
            
            # Start the streaming process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give process time to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"❌ Streaming process failed to start: {stderr}")
                return None, None
            
            # Determine stream URL
            stream_url = self._determine_stream_url(destination_type, endpoint, stream_id, device_id)
            
            return process, stream_url
            
        except Exception as e:
            print(f"❌ Error starting streaming process: {e}")
            return None, None
    
    def _build_ffmpeg_command(self, config: Dict[str, Any], width: str, height: str,
                             destination_type: str, endpoint: str, stream_id: str) -> Optional[List[str]]:
        """Build FFmpeg command based on stream type and destination"""
        
        base_cmd = [
            "ffmpeg",
            "-f", "v4l2",
            "-video_size", f"{width}x{height}",
            "-framerate", str(config["fps"]),
            "-i", "/dev/video0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-b:v", f"{config['bitrate_kbps']}k",
            "-bufsize", f"{config['bitrate_kbps'] * 2}k",
            "-maxrate", f"{config['bitrate_kbps'] * 1.2}k"
        ]
        
        # Add audio configuration
        if config.get("audio_enabled", False):
            base_cmd.extend(["-f", "alsa", "-i", "default"])
        else:
            base_cmd.extend(["-an"])
        
        # Add destination-specific options
        if destination_type == "rtsp_server":
            base_cmd.extend([
                "-f", "rtsp",
                "-rtsp_transport", "tcp",
                endpoint
            ])
            
        elif destination_type == "webrtc_peer":
            # WebRTC streaming (simplified - would need proper WebRTC implementation)
            output_file = self.temp_dir / f"{stream_id}_webrtc.mp4"
            base_cmd.extend([
                "-f", "mp4",
                "-movflags", "frag_keyframe+empty_moov",
                str(output_file)
            ])
            
        elif destination_type == "s3_hls":
            # HLS streaming for S3
            hls_dir = self.temp_dir / f"{stream_id}_hls"
            hls_dir.mkdir(exist_ok=True)
            
            base_cmd.extend([
                "-f", "hls",
                "-hls_time", "6",
                "-hls_list_size", "10",
                "-hls_flags", "delete_segments",
                str(hls_dir / "playlist.m3u8")
            ])
            
        else:
            # Default to file output
            output_file = self.temp_dir / f"{stream_id}_output.mp4"
            base_cmd.extend([
                "-f", "mp4",
                str(output_file)
            ])
        
        return base_cmd
    
    def _determine_stream_url(self, destination_type: str, endpoint: str, 
                             stream_id: str, device_id: str) -> str:
        """Determine the stream URL based on destination type"""
        
        if destination_type == "rtsp_server" and endpoint:
            return endpoint
            
        elif destination_type == "webrtc_peer":
            return f"webrtc://localhost:8080/stream/{stream_id}"
            
        elif destination_type == "s3_hls":
            return f"https://s3.amazonaws.com/bucket/{device_id}/hls/{stream_id}/playlist.m3u8"
            
        else:
            # Default local stream URL
            return f"rtsp://localhost:8554/stream/{stream_id}"
    
    def _stop_streaming_process(self, process: subprocess.Popen) -> None:
        """Stop a streaming process gracefully"""
        try:
            # Send SIGTERM first
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=5)
                print("📺 Streaming process terminated gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop
                process.kill()
                process.wait()
                print("📺 Streaming process force killed")
                
        except Exception as e:
            print(f"⚠️ Error stopping streaming process: {e}")
    
    def _save_stream_recording(self, stream_id: str, stream_info: Dict[str, Any],
                              s3_upload_config: Dict[str, Any], device_id: str) -> Optional[Dict[str, Any]]:
        """Save stream recording and upload to S3 if configured"""
        try:
            # Create recording file path
            timestamp = int(time.time() * 1000)
            recording_filename = f"{stream_id}.mp4"
            recording_path = self.temp_dir / recording_filename
            
            # For simulation, create a placeholder recording file
            # In production, this would save the actual stream buffer
            recording_data = {
                "stream_id": stream_id,
                "device_id": device_id,
                "started_at": stream_info.get("started_at"),
                "stopped_at": timestamp,
                "duration_ms": timestamp - stream_info.get("started_at", timestamp),
                "configuration": stream_info.get("configuration", {}),
                "recording_type": "stream_recording",
                "note": "This is a simulated recording. In production, actual stream data would be saved."
            }
            
            # Save recording metadata
            with open(recording_path.with_suffix('.json'), 'w') as f:
                json.dump(recording_data, f, indent=2)
            
            # Create placeholder video file
            with open(recording_path, 'wb') as f:
                placeholder_content = f"STREAM_RECORDING_{stream_id}_{timestamp}".encode()
                f.write(placeholder_content)
            
            print(f"💾 Stream recording saved: {recording_filename}")
            
            result = {
                "recording_file": recording_filename,
                "local_path": str(recording_path)
            }
            
            # Handle S3 upload if configured
            if s3_upload_config:
                s3_result = self._upload_recording_to_s3(
                    recording_path, s3_upload_config, device_id, stream_id
                )
                if s3_result:
                    result["s3_key"] = s3_result
            
            return result
            
        except Exception as e:
            print(f"❌ Error saving stream recording: {e}")
            return None
    
    def _upload_recording_to_s3(self, recording_path: Path, s3_config: Dict[str, Any],
                               device_id: str, stream_id: str) -> Optional[str]:
        """Upload stream recording to S3"""
        try:
            # Import S3 uploader
            import sys
            from pathlib import Path
            
            # Add the project root to path if needed
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from services.simple_s3_uploader import SimpleS3Uploader
            
            # Initialize uploader with device_id
            uploader = SimpleS3Uploader(device_id=device_id)
            
            # Build S3 folder path with structure: {device_id}/prefix
            bucket = s3_config.get("bucket", "papaya-parking-data")
            prefix = s3_config.get("prefix", "recordings/")
            
            # Build path structure: {device_id}/prefix
            if device_id:
                # Remove [DEVICE_ID] placeholder if present in prefix
                if "[DEVICE_ID]" in prefix:
                    prefix = prefix.replace("[DEVICE_ID]", "")
                
                # Construct path as {device_id}/prefix
                device_folder = f"{device_id}/{prefix.strip('/')}"
            else:
                # Fallback to original prefix if no device_id
                device_folder = prefix.strip('/')
            
            # Add date-based folder structure
            date_folder = datetime.now().strftime("%Y-%m-%d")
            folder_path = f"{device_folder}/{date_folder}"
            
            # Create S3 filename
            s3_filename = f"{stream_id}.mp4"
            
            # Upload file
            upload_success = uploader.upload_file(
                str(recording_path),
                bucket,
                folder_path,
                custom_filename=s3_filename,
                metadata={
                    "media_type": "stream_recording",
                    "stream_id": stream_id,
                    "device_id": device_id or "unknown",
                    "upload_timestamp": str(int(time.time() * 1000))
                }
            )
            
            if upload_success:
                s3_key = f"{folder_path}/{s3_filename}"
                print(f"📤 Successfully uploaded recording to S3: {s3_key}")
                return s3_key
            else:
                print(f"❌ Failed to upload recording to S3")
                return None
                
        except Exception as e:
            print(f"❌ S3 upload error: {e}")
            return None
    
    def _start_duration_monitor(self, stream_id: str, max_duration_seconds: int) -> None:
        """Start a thread to monitor stream duration and auto-stop"""
        def monitor():
            time.sleep(max_duration_seconds)
            with self.stream_lock:
                if stream_id in self.active_streams:
                    print(f"⏰ Stream {stream_id} reached max duration, stopping...")
                    self.stop_stream({"stream_id": stream_id})
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def get_active_streams(self) -> Dict[str, Any]:
        """Get information about all active streams"""
        with self.stream_lock:
            return {
                "active_streams": len(self.active_streams),
                "streams": list(self.active_streams.values())
            }
    
    def get_stream_status(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific stream"""
        with self.stream_lock:
            return self.active_streams.get(stream_id)
    
    def stop_all_streams(self) -> Dict[str, Any]:
        """Stop all active streams"""
        with self.stream_lock:
            stopped_streams = []
            
            for stream_id in list(self.active_streams.keys()):
                try:
                    result = self.stop_stream({"stream_id": stream_id})
                    stopped_streams.append({
                        "stream_id": stream_id,
                        "success": result.get("success", False)
                    })
                except Exception as e:
                    stopped_streams.append({
                        "stream_id": stream_id,
                        "success": False,
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "stopped_streams": len(stopped_streams),
                "results": stopped_streams
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current streaming service status"""
        with self.stream_lock:
            return {
                "service": "camera_streaming",
                "status": "active",
                "temp_directory": str(self.temp_dir),
                "active_streams": len(self.active_streams),
                "supported_stream_types": ["rtsp", "webrtc", "hls"],
                "supported_destinations": ["rtsp_server", "webrtc_peer", "s3_hls"],
                "video_resolutions": list(self.video_resolutions.keys()),
                "streams": list(self.active_streams.keys())
            }
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Clean up old temporary streaming files"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            deleted_files = []
            total_size_freed = 0
            
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file() and (file_path.name.startswith("stream_") or 
                                          "_hls" in file_path.name):
                    file_age = current_time - file_path.stat().st_mtime
                    
                    if file_age > max_age_seconds:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                        total_size_freed += file_size
            
            result = {
                "success": True,
                "deleted_files": len(deleted_files),
                "size_freed_bytes": total_size_freed,
                "max_age_hours": max_age_hours,
                "files": deleted_files
            }
            
            print(f"🧹 Streaming cleanup completed: {len(deleted_files)} files deleted, {total_size_freed} bytes freed")
            return result
            
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
