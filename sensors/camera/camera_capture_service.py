#!/usr/bin/env python3

import os
import time
import json
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import base64

class CameraCaptureService:
    """
    Camera capture service for handling image and video capture operations.
    Supports various formats, resolutions, and automatic S3 upload functionality.
    """
    
    def __init__(self, temp_dir: str = "data/temp"):
        """
        Initialize the camera capture service
        
        Args:
            temp_dir: Directory to store temporary captured files
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Camera configuration defaults
        self.default_image_config = {
            "resolution": "medium",
            "quality": 85,
            "format": "jpeg",
            "flash": False,
            "exposure_compensation": 0,
            "white_balance": "auto",
            "return_method": "url"
        }
        
        self.default_video_config = {
            "duration_seconds": 30,
            "resolution": "720p",
            "fps": 30,
            "codec": "h264",
            "bitrate_kbps": 2048,
            "audio_enabled": True
        }
        
        # Resolution mappings
        self.image_resolutions = {
            "full": "1920x1080",
            "medium": "1280x720", 
            "low": "640x480"
        }
        
        self.video_resolutions = {
            "1080p": "1920x1080",
            "720p": "1280x720",
            "480p": "854x480"
        }
        
        self.capture_lock = threading.Lock()
        print("📷 Camera capture service initialized")
    
    def capture_image(self, params: Dict[str, Any] = None, device_id: str = None) -> Dict[str, Any]:
        """
        Capture a single image with specified parameters
        
        Args:
            params: Capture parameters (resolution, quality, format, etc.)
            device_id: Device identifier for file naming
            
        Returns:
            Dictionary containing capture results and file information
        """
        if params is None:
            params = {}
        
        # Merge with defaults
        config = {**self.default_image_config, **params}
        
        try:
            with self.capture_lock:
                # Generate timestamp and filename
                timestamp = int(time.time() * 1000)
                date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Create filename with device ID if available
                if device_id:
                    filename = f"{device_id}_{timestamp}_{date_str}_image.{config['format']}"
                else:
                    filename = f"{timestamp}_{date_str}_image.{config['format']}"
                
                file_path = self.temp_dir / filename
                
                print(f"📸 Capturing image: {filename}")
                print(f"📋 Configuration: {config}")
                
                # Execute image capture
                capture_success = self._execute_image_capture(file_path, config)
                
                if not capture_success:
                    return {
                        "success": False,
                        "error": "Image capture failed",
                        "timestamp": timestamp
                    }
                
                # Get file size
                file_size = file_path.stat().st_size if file_path.exists() else 0
                
                print(f"✅ Image captured successfully: {filename} ({file_size} bytes)")
                
                # Prepare response
                response = {
                    "success": True,
                    "filename": filename,
                    "local_path": str(file_path),
                    "image_size_bytes": file_size,
                    "capture_timestamp": timestamp,
                    "configuration": config
                }
                
                # Handle S3 upload if bucket and location are provided
                # if s3_bucket and s3_location:
                #     print(f"☁️ S3 upload requested: bucket={s3_bucket}, location={s3_location}")
                    
                #     # Create S3 config from direct arguments
                #     s3_config = {
                #         "bucket": s3_bucket,
                #         "location": s3_location,
                #         "include_date_folder": True,
                #         "generate_presigned_url": False
                #     }
                    
                #     # Add any additional S3 options from params if provided
                #     if params and "s3_upload" in params and isinstance(params["s3_upload"], dict):
                #         s3_options = params["s3_upload"]
                #         s3_config.update({
                #             "include_date_folder": s3_options.get("include_date_folder", True),
                #             "generate_presigned_url": s3_options.get("generate_presigned_url", False),
                #             "url_expiry_seconds": s3_options.get("url_expiry_seconds", 3600)
                #         })
                    
                #     s3_result = self._handle_s3_upload(file_path, s3_config, device_id, "image")
                #     if s3_result:
                #         response["s3_location"] = s3_result
                #         print(f"✅ Image uploaded to S3: {s3_result.get('s3_url', 'unknown')}")
                #     else:
                #         print(f"❌ S3 upload failed for image: {filename}")
                # elif s3_bucket or s3_location:
                #     print(f"⚠️ S3 upload requires both bucket and location. Provided: bucket={s3_bucket}, location={s3_location}")
                
                # # Handle return method
                # return_method = config.get("return_method", "url")
                # if return_method == "base64":
                #     response["image_base64"] = self._encode_file_base64(file_path)
                # elif return_method == "url":
                #     response["image_url"] = f"file://{file_path}"
                
                return response
                
        except Exception as e:
            print(f"❌ Image capture error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": int(time.time() * 1000)
            }
    
    def capture_video(self, params: Dict[str, Any] = None, device_id: str = None,
                     s3_bucket: str = None, s3_location: str = None) -> Dict[str, Any]:
        """
        Capture video with specified parameters
        
        Args:
            params: Capture parameters (duration, resolution, fps, etc.)
            device_id: Device identifier for file naming and S3 paths
            s3_bucket: S3 bucket name for uploading the captured video
            s3_location: S3 location/folder path where to store the video
            
        Returns:
            Dictionary containing capture results and file information
        """
        if params is None:
            params = {}
        
        # Merge with defaults
        config = {**self.default_video_config, **params}
        
        try:
            with self.capture_lock:
                # Generate timestamp and filename
                timestamp = int(time.time() * 1000)
                date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Create filename with device ID if available
                if device_id:
                    filename = f"{device_id}_{timestamp}_{date_str}_video.mp4"
                else:
                    filename = f"{timestamp}_{date_str}_video.mp4"
                
                file_path = self.temp_dir / filename
                
                print(f"🎥 Starting video capture: {filename}")
                print(f"📋 Configuration: {config}")
                print(f"⏱️ Duration: {config['duration_seconds']} seconds")
                
                # Execute video capture
                capture_success = self._execute_video_capture(file_path, config)
                
                if not capture_success:
                    return {
                        "success": False,
                        "error": "Video capture failed",
                        "timestamp": timestamp
                    }
                
                # Get file size
                file_size = file_path.stat().st_size if file_path.exists() else 0
                
                print(f"✅ Video captured successfully: {filename} ({file_size} bytes)")
                
                # Prepare response
                response = {
                    "success": True,
                    "filename": filename,
                    "local_path": str(file_path),
                    "video_size_bytes": file_size,
                    "capture_timestamp": timestamp,
                    "duration_seconds": config["duration_seconds"],
                    "configuration": config
                }
                
                # Handle S3 upload if bucket and location are provided
                if s3_bucket and s3_location:
                    print(f"☁️ S3 upload requested for video: bucket={s3_bucket}, location={s3_location}")
                    
                    # Create S3 config from direct arguments
                    s3_config = {
                        "bucket": s3_bucket,
                        "location": s3_location,
                        "include_date_folder": True,
                        "generate_presigned_url": False
                    }
                    
                    # Add any additional S3 options from params if provided
                    if params and "s3_upload" in params and isinstance(params["s3_upload"], dict):
                        s3_options = params["s3_upload"]
                        s3_config.update({
                            "include_date_folder": s3_options.get("include_date_folder", True),
                            "generate_presigned_url": s3_options.get("generate_presigned_url", False),
                            "url_expiry_seconds": s3_options.get("url_expiry_seconds", 3600)
                        })
                    
                    s3_result = self._handle_s3_upload(file_path, s3_config, device_id, "video")
                    if s3_result:
                        response["s3_location"] = s3_result
                        print(f"✅ Video uploaded to S3: {s3_result.get('s3_url', 'unknown')}")
                    else:
                        print(f"❌ S3 upload failed for video: {filename}")
                elif s3_bucket or s3_location:
                    print(f"⚠️ S3 upload requires both bucket and location. Provided: bucket={s3_bucket}, location={s3_location}")
                
                response["video_url"] = f"file://{file_path}"
                
                return response
                
        except Exception as e:
            print(f"❌ Video capture error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": int(time.time() * 1000)
            }
    
    def _execute_image_capture(self, file_path: Path, config: Dict[str, Any]) -> bool:
        """
        Execute the actual image capture using system camera
        
        Args:
            file_path: Path where image should be saved
            config: Image capture configuration
            
        Returns:
            bool: True if capture successful, False otherwise
        """
        try:
            # Build resolution parameter
            resolution = self.image_resolutions.get(config["resolution"], "1280x720")
            
            # For demonstration, we'll simulate image capture and create a placeholder
            # In production, you would use actual camera APIs like:
            # - libcamera (Raspberry Pi)
            # - OpenCV (cv2.VideoCapture)
            # - gstreamer
            # - fswebcam
            
            # Try using fswebcam if available
            try:
                cmd = [
                    "fswebcam",
                    "--no-banner",
                    f"--resolution={resolution}",
                    f"--jpeg={config['quality']}",
                    str(file_path)
                ]
                
                if not config.get("flash", False):
                    cmd.append("--no-flash")
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"📸 Image captured using fswebcam")
                    return True
                else:
                    print(f"⚠️ fswebcam failed: {result.stderr}")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print("⚠️ fswebcam not available, trying libcamera...")
                
                # Try libcamera-still (Raspberry Pi)
                try:
                    cmd = [
                        "libcamera-still",
                        "-o", str(file_path),
                        "--width", resolution.split('x')[0],
                        "--height", resolution.split('x')[1],
                        "--quality", str(config['quality']),
                        "--timeout", "5000"  # 5 second timeout
                    ]
                    
                    # Add exposure compensation if specified
                    if config.get("exposure_compensation", 0) != 0:
                        cmd.extend(["--ev", str(config["exposure_compensation"])])
                    
                    # Add white balance
                    if config.get("white_balance", "auto") != "auto":
                        cmd.extend(["--awb", config["white_balance"]])
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        print(f"📸 Image captured using libcamera-still")
                        return True
                    else:
                        print(f"⚠️ libcamera-still failed: {result.stderr}")
                        
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    print("⚠️ libcamera-still not available, creating simulation image...")
            
            # Fallback: Create a simulated image file for testing
            return self._create_simulated_image(file_path, config)
            
        except Exception as e:
            print(f"❌ Image capture execution error: {e}")
            return False
    
    def _execute_video_capture(self, file_path: Path, config: Dict[str, Any]) -> bool:
        """
        Execute the actual video capture using system camera
        
        Args:
            file_path: Path where video should be saved
            config: Video capture configuration
            
        Returns:
            bool: True if capture successful, False otherwise
        """
        try:
            # Build resolution parameter
            resolution = self.video_resolutions.get(config["resolution"], "1280x720")
            width, height = resolution.split('x')
            
            # Try using libcamera-vid if available (Raspberry Pi)
            try:
                # Ensure numeric parameters are properly converted with validation
                duration_seconds = config.get("duration_seconds", "30")
                fps_value = config.get("fps", "30")
                bitrate_value = config.get("bitrate_kbps", "2048")
                
                # Convert to integers with fallback to defaults if empty or invalid
                try:
                    duration_ms = int(duration_seconds) * 1000 if duration_seconds else 30000
                except (ValueError, TypeError):
                    print(f"⚠️ Invalid duration_seconds: '{duration_seconds}', using default: 30")
                    duration_ms = 30000
                
                try:
                    fps = int(fps_value) if fps_value else 30
                except (ValueError, TypeError):
                    print(f"⚠️ Invalid fps: '{fps_value}', using default: 30")
                    fps = 30
                
                try:
                    bitrate_bps = int(bitrate_value) * 1000 if bitrate_value else 2048000
                except (ValueError, TypeError):
                    print(f"⚠️ Invalid bitrate_kbps: '{bitrate_value}', using default: 2048")
                    bitrate_bps = 2048000
                
                cmd = [
                    "libcamera-vid",
                    "-o", str(file_path),
                    "-t", str(duration_ms),  # milliseconds
                    "--width", width,
                    "--height", height,
                    "--framerate", str(fps),
                    "--bitrate", str(bitrate_bps),  # bits per second
                    "--codec", config["codec"]
                ]
                
                if not config.get("audio_enabled", True):
                    cmd.append("--noaudio")
                
                print(f"🎥 Executing: {' '.join(cmd)}")
                try:
                    timeout_seconds = int(config.get("duration_seconds", "30")) + 30
                except (ValueError, TypeError):
                    timeout_seconds = 60  # Default timeout
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
                
                if result.returncode == 0:
                    print(f"🎥 Video captured using libcamera-vid")
                    return True
                else:
                    print(f"⚠️ libcamera-vid failed: {result.stderr}")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print("⚠️ libcamera-vid not available, trying ffmpeg...")
                
                # Try ffmpeg with v4l2 (Linux video capture)
                try:
                    # Ensure numeric parameters are properly converted with validation
                    duration_seconds = config.get("duration_seconds", "30")
                    fps_value = config.get("fps", "30")
                    bitrate_value = config.get("bitrate_kbps", "2048")
                    
                    # Convert to integers with fallback to defaults if empty or invalid
                    try:
                        duration_sec = int(duration_seconds) if duration_seconds else 30
                    except (ValueError, TypeError):
                        print(f"⚠️ Invalid duration_seconds: '{duration_seconds}', using default: 30")
                        duration_sec = 30
                    
                    try:
                        fps = int(fps_value) if fps_value else 30
                    except (ValueError, TypeError):
                        print(f"⚠️ Invalid fps: '{fps_value}', using default: 30")
                        fps = 30
                    
                    try:
                        bitrate_kbps = int(bitrate_value) if bitrate_value else 2048
                    except (ValueError, TypeError):
                        print(f"⚠️ Invalid bitrate_kbps: '{bitrate_value}', using default: 2048")
                        bitrate_kbps = 2048
                    
                    cmd = [
                        "ffmpeg",
                        "-f", "v4l2",
                        "-video_size", resolution,
                        "-framerate", str(fps),
                        "-i", "/dev/video0",
                        "-t", str(duration_sec),
                        "-c:v", "libx264" if config["codec"] == "h264" else "libx265",
                        "-b:v", f"{bitrate_kbps}k",
                        "-y",  # Overwrite output file
                        str(file_path)
                    ]
                    
                    if not config.get("audio_enabled", True):
                        cmd.extend(["-an"])  # No audio
                    
                    print(f"🎥 Executing: {' '.join(cmd)}")
                    try:
                        timeout_seconds = int(config.get("duration_seconds", "30")) + 30
                    except (ValueError, TypeError):
                        timeout_seconds = 60  # Default timeout
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
                    
                    if result.returncode == 0:
                        print(f"🎥 Video captured using ffmpeg")
                        return True
                    else:
                        print(f"⚠️ ffmpeg failed: {result.stderr}")
                        
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    print("⚠️ ffmpeg not available, creating simulation video...")
            
            # Fallback: Create a simulated video file for testing
            return self._create_simulated_video(file_path, config)
            
        except Exception as e:
            print(f"❌ Video capture execution error: {e}")
            return False
    
    def _create_simulated_image(self, file_path: Path, config: Dict[str, Any]) -> bool:
        """Create a simulated image file for testing purposes"""
        try:
            # Create a simple JSON metadata file as simulation
            simulation_data = {
                "type": "simulated_image",
                "timestamp": int(time.time() * 1000),
                "configuration": config,
                "resolution": self.image_resolutions.get(config["resolution"], "1280x720"),
                "format": config["format"],
                "quality": config["quality"],
                "simulated": True,
                "note": "This is a simulated capture for testing. In production, actual camera hardware would be used."
            }
            
            # Write JSON data to file with image extension for consistency
            with open(file_path.with_suffix('.json'), 'w') as f:
                json.dump(simulation_data, f, indent=2)
            
            # Also create a small placeholder file with the requested extension
            with open(file_path, 'wb') as f:
                # Write minimal file content to simulate image data
                placeholder_content = b"SIMULATED_IMAGE_DATA_" + str(time.time()).encode() + b"_END"
                f.write(placeholder_content)
            
            print(f"📸 Created simulated image: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create simulated image: {e}")
            return False
    
    def _create_simulated_video(self, file_path: Path, config: Dict[str, Any]) -> bool:
        """Create a simulated video file for testing purposes"""
        try:
            # Create a simple JSON metadata file as simulation
            simulation_data = {
                "type": "simulated_video",
                "timestamp": int(time.time() * 1000),
                "configuration": config,
                "resolution": self.video_resolutions.get(config["resolution"], "1280x720"),
                "duration_seconds": config["duration_seconds"],
                "fps": config["fps"],
                "codec": config["codec"],
                "bitrate_kbps": config["bitrate_kbps"],
                "simulated": True,
                "note": "This is a simulated capture for testing. In production, actual camera hardware would be used."
            }
            
            # Write JSON data to file
            with open(file_path.with_suffix('.json'), 'w') as f:
                json.dump(simulation_data, f, indent=2)
            
            # Also create a placeholder video file
            with open(file_path, 'wb') as f:
                # Write minimal file content to simulate video data
                try:
                    duration_str = str(int(config.get("duration_seconds", "30")))
                except (ValueError, TypeError):
                    duration_str = "30"  # Default duration
                placeholder_content = b"SIMULATED_VIDEO_DATA_" + str(time.time()).encode() + b"_DURATION_" + duration_str.encode() + b"_END"
                f.write(placeholder_content)
            
            print(f"🎥 Created simulated video: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create simulated video: {e}")
            return False
    
    def _handle_s3_upload(self, file_path: Path, s3_config: Dict[str, Any], device_id: str = None, media_type: str = "image") -> Optional[Dict[str, Any]]:
        """
        Handle S3 upload of captured media file
        
        Args:
            file_path: Path to the file to upload
            s3_config: S3 upload configuration
            device_id: Device identifier for S3 path structure
            media_type: Type of media (image/video)
            
        Returns:
            S3 location information or None if upload failed
        """
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
            
            # Parse S3 configuration parameters
            bucket = s3_config.get("bucket")
            if not bucket:
                print(f"❌ S3 upload failed: No bucket name provided")
                return None
                
            # Get location/prefix (support both 'location' and 'prefix' parameters)
            location = s3_config.get("location", s3_config.get("prefix", f"{media_type}s/"))
            
            # Build path structure: {device_id}/location
            if device_id:
                # Remove [DEVICE_ID] placeholder if present in location (legacy support)
                if "[DEVICE_ID]" in location:
                    location = location.replace("[DEVICE_ID]", "")
                
                # Construct path as {device_id}/location
                device_folder = f"{device_id}/{location.strip('/')}"
            else:
                # Fallback to original location if no device_id
                device_folder = location.strip('/')
            
            # Add date-based folder structure (optional)
            if s3_config.get("include_date_folder", True):
                date_folder = datetime.now().strftime("%Y-%m-%d")
                folder_path = f"{device_folder}/{date_folder}"
            else:
                folder_path = device_folder
            
            # Create S3 key with timestamp
            timestamp = int(time.time() * 1000)
            s3_filename = f"{media_type}_{timestamp}_{file_path.name}"
            
            # Upload file
            upload_success = uploader.upload_file(
                str(file_path),
                bucket,
                folder_path,
                custom_filename=s3_filename,
                metadata={
                    "media_type": media_type,
                    "capture_timestamp": str(timestamp),
                    "device_id": device_id or "unknown",
                    "original_filename": file_path.name
                }
            )
            
            if upload_success:
                s3_key = f"{folder_path}/{s3_filename}"
                
                result = {
                    "bucket": bucket,
                    "key": s3_key,
                    "region": "us-east-1",  # Default region, should be configurable
                    "s3_url": f"s3://{bucket}/{s3_key}"
                }
                
                # Generate presigned URL if requested
                if s3_config.get("generate_presigned_url", False):
                    expiry_seconds = s3_config.get("url_expiry_seconds", 3600)
                    presigned_url = uploader.generate_presigned_url(bucket, s3_key, expiry_seconds)
                    
                    if presigned_url:
                        result["presigned_url"] = presigned_url
                        result["expires_at"] = int((time.time() + expiry_seconds) * 1000)
                
                print(f"📤 Successfully uploaded {media_type} to S3: {s3_key}")
                return result
            else:
                print(f"❌ Failed to upload {media_type} to S3")
                return None
                
        except Exception as e:
            print(f"❌ S3 upload error: {e}")
            return None
    
    def _encode_file_base64(self, file_path: Path) -> Optional[str]:
        """
        Encode file as base64 string
        
        Args:
            file_path: Path to file to encode
            
        Returns:
            Base64 encoded string or None if failed
        """
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
                return base64.b64encode(file_data).decode('utf-8')
        except Exception as e:
            print(f"❌ Base64 encoding error: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current camera service status
        
        Returns:
            Dictionary containing service status information
        """
        return {
            "service": "camera_capture",
            "status": "active",
            "temp_directory": str(self.temp_dir),
            "supported_image_formats": ["jpeg", "png"],
            "supported_video_codecs": ["h264", "h265"],
            "image_resolutions": list(self.image_resolutions.keys()),
            "video_resolutions": list(self.video_resolutions.keys()),
            "capture_lock_active": self.capture_lock.locked()
        }
    
    def timed_camera_capture(
        self,
        capture_duration_seconds: int,
        burst_count: int,
        burst_interval_ms: int,
        save_location: str = None,
        device_id: str = None,
        stop_event: threading.Event = None,
        capture_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Perform timed camera capture with burst mode support.
        
        This method captures images in bursts at specified intervals for a given duration.
        It's designed to be used with the sensor.capture.all RPC method.
        
        Args:
            capture_duration_seconds (int): Total duration to capture images (in seconds)
            burst_count (int): Number of images to capture in each burst
            burst_interval_ms (int): Time interval between each image in a burst (in milliseconds)
            save_location (str, optional): Directory path where captured images should be saved
                                         If None, uses the service's temp_dir
            device_id (str, optional): Device identifier for file naming
            stop_event (threading.Event, optional): Event to signal early termination
            capture_params (dict, optional): Additional camera capture parameters
            
        Returns:
            dict: Results containing captured image information
                {
                    "success": bool,
                    "images_captured": int,
                    "total_bursts": int,
                    "capture_duration_actual": float,
                    "captured_files": List[str],
                    "error": str (if success=False)
                }
        """
        
        print(f"📸 Starting timed camera capture session")
        print(f"   Duration: {capture_duration_seconds}s")
        print(f"   Burst count: {burst_count} images")
        print(f"   Burst interval: {burst_interval_ms}ms")
        print(f"   Save location: {save_location or self.temp_dir}")
        
        # Initialize results
        results = {
            "success": False,
            "images_captured": 0,
            "total_bursts": 0,
            "capture_duration_actual": 0.0,
            "captured_files": [],
            "error": None
        }
        
        try:
            # Use provided save location or default to service temp_dir
            if save_location:
                save_dir = Path(save_location)
                save_dir.mkdir(parents=True, exist_ok=True)
                # Temporarily change the service temp_dir for this capture session
                original_temp_dir = self.temp_dir
                self.temp_dir = save_dir
            else:
                save_dir = self.temp_dir
                original_temp_dir = None
            
            # Default capture parameters
            default_params = {
                "resolution": "medium",
                "quality": 85,
                "format": "jpeg",
                "save_local": True,
                "return_method": "url"
            }
            
            # Merge with user-provided parameters
            if capture_params:
                default_params.update(capture_params)
            
            # Calculate timing
            burst_interval_seconds = burst_interval_ms / 1000.0
            
            # Calculate how long each complete burst takes
            burst_duration = (burst_count - 1) * burst_interval_seconds
            
            # Calculate time between bursts (10 seconds default, adjustable based on requirements)
            inter_burst_delay = max(10.0, burst_duration + 2.0)  # At least 2 seconds between bursts
            
            print(f"📊 Timing calculation:")
            print(f"   Burst duration: {burst_duration:.2f}s")
            print(f"   Inter-burst delay: {inter_burst_delay:.2f}s")
            print(f"   Total cycle time: {burst_duration + inter_burst_delay:.2f}s")
            
            # Track timing
            start_time = time.time()
            captured_files = []
            
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
                
                # Perform burst capture
                print(f"📸 Starting burst #{results['total_bursts'] + 1} at {elapsed_time:.2f}s")
                
                burst_start_time = time.time()
                burst_files = []
                
                for i in range(burst_count):
                    # Check if we should stop during burst
                    if stop_event and stop_event.is_set():
                        break
                        
                    if time.time() - start_time >= capture_duration_seconds:
                        break
                    
                    try:
                        # Add burst and sequence information to parameters
                        burst_params = default_params.copy()
                        burst_params.update({
                            "burst_number": results['total_bursts'] + 1,
                            "sequence_number": i + 1,
                            "capture_session": "timed_capture"
                        })
                        
                        # Capture image using the service's own capture_image method
                        capture_result = self.capture_image(
                            params=burst_params,
                            device_id=device_id
                        )
                        
                        if capture_result.get("success", False):
                            image_path = capture_result.get("local_path")
                            if image_path and os.path.exists(image_path):
                                captured_files.append(image_path)
                                burst_files.append(image_path)
                                results["images_captured"] += 1
                                
                                print(f"   📷 Image {i+1}/{burst_count}: {os.path.basename(image_path)}")
                            else:
                                print(f"   ❌ Image {i+1}/{burst_count}: File not found after capture")
                        else:
                            print(f"   ❌ Image {i+1}/{burst_count}: Capture failed - {capture_result.get('error', 'Unknown error')}")
                    
                    except Exception as img_error:
                        print(f"   ❌ Image {i+1}/{burst_count}: Exception - {img_error}")
                    
                    # Wait between images in burst (except after last image)
                    if i < burst_count - 1:
                        time.sleep(burst_interval_seconds)
                
                results["total_bursts"] += 1
                burst_duration_actual = time.time() - burst_start_time
                
                print(f"✅ Burst #{results['total_bursts']} completed: {len(burst_files)} images in {burst_duration_actual:.2f}s")
                
                # Check if we have time for another burst
                current_elapsed = time.time() - start_time
                remaining_time = capture_duration_seconds - current_elapsed
                
                if remaining_time < inter_burst_delay:
                    print(f"⏰ Insufficient time for another burst (remaining: {remaining_time:.2f}s)")
                    break
                
                # Wait before next burst
                if stop_event:
                    # Use event.wait() for interruptible sleep
                    if stop_event.wait(timeout=inter_burst_delay):
                        print(f"🛑 Stop event during inter-burst delay")
                        break
                else:
                    time.sleep(inter_burst_delay)
            
            # Calculate final results
            end_time = time.time()
            results["capture_duration_actual"] = end_time - start_time
            results["captured_files"] = captured_files
            results["success"] = True
            
            print(f"✅ Timed camera capture completed:")
            print(f"   Total images: {results['images_captured']}")
            print(f"   Total bursts: {results['total_bursts']}")
            print(f"   Actual duration: {results['capture_duration_actual']:.2f}s")
            print(f"   Files saved to: {save_dir}")
            
            # Restore original temp_dir if it was changed
            if original_temp_dir:
                self.temp_dir = original_temp_dir
            
        except Exception as e:
            error_msg = f"Timed camera capture failed: {str(e)}"
            print(f"❌ {error_msg}")
            results["error"] = error_msg
            results["capture_duration_actual"] = time.time() - start_time if 'start_time' in locals() else 0
            
            # Restore original temp_dir if it was changed
            if 'original_temp_dir' in locals() and original_temp_dir:
                self.temp_dir = original_temp_dir
        
        return results

    def estimate_capture_session(
        self,
        capture_duration_seconds: int,
        burst_count: int,
        burst_interval_ms: int
    ) -> Dict[str, Any]:
        """
        Estimate the results of a timed camera capture session without actually capturing.
        
        Args:
            capture_duration_seconds (int): Total duration to capture images
            burst_count (int): Number of images to capture in each burst
            burst_interval_ms (int): Time interval between images in a burst
            
        Returns:
            dict: Estimated capture session results
        """
        
        burst_interval_seconds = burst_interval_ms / 1000.0
        burst_duration = (burst_count - 1) * burst_interval_seconds
        inter_burst_delay = max(10.0, burst_duration + 2.0)
        total_cycle_time = burst_duration + inter_burst_delay
        
        # Estimate number of complete bursts
        estimated_bursts = max(1, int(capture_duration_seconds / total_cycle_time))
        estimated_images = estimated_bursts * burst_count
        
        return {
            "estimated_bursts": estimated_bursts,
            "estimated_images": estimated_images,
            "burst_duration": burst_duration,
            "inter_burst_delay": inter_burst_delay,
            "total_cycle_time": total_cycle_time,
            "capture_efficiency": min(100.0, (estimated_bursts * total_cycle_time / capture_duration_seconds) * 100)
        }

    def cleanup_temp_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Clean up old temporary files
        
        Args:
            max_age_hours: Maximum age of files to keep (in hours)
            
        Returns:
            Cleanup summary
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            deleted_files = []
            total_size_freed = 0
            
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
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
            
            print(f"🧹 Cleanup completed: {len(deleted_files)} files deleted, {total_size_freed} bytes freed")
            return result
            
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
