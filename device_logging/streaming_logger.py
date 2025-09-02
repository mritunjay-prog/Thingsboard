import logging
import time
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import socket
import atexit
import json
import threading

class StreamingLogger:
    """Dedicated logger for camera streaming operations with session tracking."""
    
    def __init__(self, device_name: Optional[str] = None, log_base_dir: str = "data/logs"):
        # Fallback to old location if new location doesn't exist and old one does
        if not Path(log_base_dir).exists() and Path("device_logs").exists():
            log_base_dir = "device_logs"
        self.device_name = device_name or self._get_device_name()
        self.log_base_dir = Path(log_base_dir)
        
        # Create base log directory
        self.log_base_dir.mkdir(exist_ok=True)
        
        # Store active streaming sessions
        self._active_streams: Dict[str, Dict] = {}
        self._stream_loggers: Dict[str, logging.Logger] = {}
        self._stream_handlers: Dict[str, logging.FileHandler] = {}
        
        # Thread lock for concurrent stream operations
        self._lock = threading.Lock()
        
        # Register cleanup on exit
        atexit.register(self._cleanup_all_streams)
        
        print(f"Streaming logger initialized for device: {self.device_name}")
    
    def _get_device_name(self) -> str:
        """Get device name from hostname."""
        try:
            return socket.gethostname().replace('.', '_').replace('-', '_')
        except Exception:
            return "unknown_device"
    
    def start_stream_session(self, stream_id: str, stream_params: Dict) -> logging.Logger:
        """Start a new streaming session with dedicated logger."""
        with self._lock:
            if stream_id in self._active_streams:
                # Return existing logger if stream already exists
                return self._stream_loggers[stream_id]
            
            # Record session start time
            start_epoch = int(time.time())
            
            # Create session info
            self._active_streams[stream_id] = {
                'stream_id': stream_id,
                'start_time': start_epoch,
                'end_time': None,
                'log_file': None,
                'stream_params': stream_params,
                'status': 'active'
            }
            
            # Create log file name for active stream
            log_file = self.log_base_dir / f"streaming_{stream_id}_{start_epoch}_active.log"
            self._active_streams[stream_id]['log_file'] = log_file
            
            # Create dedicated logger for this stream
            logger_name = f"{self.device_name}_streaming_{stream_id}_{start_epoch}"
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
            
            # Clear any existing handlers
            if logger.handlers:
                logger.handlers.clear()
            
            # Create file handler
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # Create specialized formatter for streaming
            formatter = logging.Formatter(
                '%(asctime)s | STREAM[%(stream_id)s] | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Create a custom filter to add stream_id to log records
            class StreamFilter(logging.Filter):
                def __init__(self, stream_id):
                    super().__init__()
                    self.stream_id = stream_id
                
                def filter(self, record):
                    record.stream_id = self.stream_id
                    return True
            
            file_handler.addFilter(StreamFilter(stream_id))
            file_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            
            # Store references
            self._stream_loggers[stream_id] = logger
            self._stream_handlers[stream_id] = file_handler
            
            # Log session start
            logger.info(f"Streaming session started for {stream_id}")
            self.log_stream_data(stream_id, "INFO", "Stream session initialized", stream_params)
            
            return logger
    
    def get_stream_logger(self, stream_id: str) -> Optional[logging.Logger]:
        """Get logger for an active stream."""
        with self._lock:
            return self._stream_loggers.get(stream_id)
    
    def log_stream_data(self, stream_id: str, level: str, message: str, data: Optional[Dict] = None):
        """Log streaming data with structured information."""
        logger = self.get_stream_logger(stream_id)
        if not logger:
            return
        
        if data:
            message = f"{message} | Data: {json.dumps(data, default=str)}"
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, message)
    
    def log_stream_error(self, stream_id: str, error: Exception, context: str = ""):
        """Log streaming error with context."""
        logger = self.get_stream_logger(stream_id)
        if not logger:
            return
        
        error_msg = f"STREAMING ERROR in {context}: {type(error).__name__}: {str(error)}"
        logger.error(error_msg)
    
    def log_stream_status(self, stream_id: str, status: Dict):
        """Log streaming status update."""
        logger = self.get_stream_logger(stream_id)
        if not logger:
            return
        
        status_msg = f"Stream status update: {json.dumps(status, default=str)}"
        logger.info(status_msg)
    
    def log_stream_metrics(self, stream_id: str, metrics: Dict):
        """Log streaming performance metrics."""
        logger = self.get_stream_logger(stream_id)
        if not logger:
            return
        
        metrics_msg = f"Stream metrics: {json.dumps(metrics, default=str)}"
        logger.info(metrics_msg)
    
    def log_viewer_activity(self, stream_id: str, activity: str, viewer_info: Dict = None):
        """Log viewer connection/disconnection activity."""
        logger = self.get_stream_logger(stream_id)
        if not logger:
            return
        
        viewer_data = viewer_info or {}
        self.log_stream_data(stream_id, "INFO", f"Viewer activity: {activity}", viewer_data)
    
    def end_stream_session(self, stream_id: str, final_metrics: Dict = None):
        """End streaming session and rename log file."""
        with self._lock:
            if stream_id not in self._active_streams:
                return
            
            session = self._active_streams[stream_id]
            end_epoch = int(time.time())
            session['end_time'] = end_epoch
            session['status'] = 'stopped'
            
            # Log final metrics if provided
            if final_metrics:
                self.log_stream_metrics(stream_id, final_metrics)
            
            # Close the current handler
            if stream_id in self._stream_handlers:
                handler = self._stream_handlers[stream_id]
                logger = self._stream_loggers[stream_id]
                
                # Log session end
                logger.info(f"Streaming session ended for {stream_id}")
                duration = end_epoch - session['start_time']
                logger.info(f"Stream duration: {duration} seconds")
                
                # Remove handler and close it
                logger.removeHandler(handler)
                handler.close()
                
                # Rename log file to final format
                old_file = session['log_file']
                new_file = self.log_base_dir / f"streaming_{stream_id}_{session['start_time']}_{end_epoch}.log"
                
                try:
                    if old_file.exists():
                        old_file.rename(new_file)
                        print(f"✅ Streaming log renamed: {new_file.name}")
                except Exception as e:
                    print(f"❌ Failed to rename streaming log for {stream_id}: {e}")
                
                # Clean up references
                del self._stream_handlers[stream_id]
                del self._stream_loggers[stream_id]
                del self._active_streams[stream_id]
    
    def get_active_streams(self) -> Dict[str, Dict]:
        """Get information about active streaming sessions."""
        with self._lock:
            active_streams = {}
            current_time = int(time.time())
            
            for stream_id, session in self._active_streams.items():
                if session['status'] == 'active':
                    active_streams[stream_id] = {
                        'stream_id': stream_id,
                        'start_time': session['start_time'],
                        'start_datetime': datetime.fromtimestamp(session['start_time']).isoformat(),
                        'duration_seconds': current_time - session['start_time'],
                        'log_file': str(session['log_file']),
                        'stream_params': session['stream_params'],
                        'status': session['status']
                    }
            
            return active_streams
    
    def get_completed_streams(self) -> List[Dict]:
        """Get list of completed streaming sessions from log files."""
        completed_streams = []
        
        # Look for completed streaming log files
        for log_file in self.log_base_dir.glob("streaming_*_*_*.log"):
            if "_active.log" in log_file.name:
                continue
            
            parts = log_file.stem.split('_')
            if len(parts) >= 4 and parts[0] == "streaming":
                try:
                    stream_id = parts[1]
                    start_epoch = int(parts[2])
                    end_epoch = int(parts[3])
                    
                    completed_streams.append({
                        'stream_id': stream_id,
                        'start_epoch': start_epoch,
                        'end_epoch': end_epoch,
                        'start_datetime': datetime.fromtimestamp(start_epoch).isoformat(),
                        'end_datetime': datetime.fromtimestamp(end_epoch).isoformat(),
                        'duration_seconds': end_epoch - start_epoch,
                        'file_path': str(log_file),
                        'file_size_bytes': log_file.stat().st_size
                    })
                except (ValueError, IndexError):
                    continue
        
        return sorted(completed_streams, key=lambda x: x['start_epoch'], reverse=True)
    
    def get_streaming_summary(self) -> Dict:
        """Get comprehensive streaming summary."""
        active_streams = self.get_active_streams()
        completed_streams = self.get_completed_streams()
        
        return {
            'device_name': self.device_name,
            'log_directory': str(self.log_base_dir),
            'active_streams': active_streams,
            'completed_streams': completed_streams,
            'total_active_streams': len(active_streams),
            'total_completed_streams': len(completed_streams),
            'summary_generated_at': datetime.now().isoformat()
        }
    
    def cleanup_old_streaming_logs(self, days_to_keep: int = 7):
        """Clean up old streaming log files."""
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        removed_count = 0
        
        for log_file in self.log_base_dir.glob("streaming_*.log"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    removed_count += 1
            except Exception as e:
                print(f"Failed to remove old streaming log file {log_file}: {e}")
        
        if removed_count > 0:
            print(f"Cleaned up {removed_count} old streaming log files")
    
    def _cleanup_all_streams(self):
        """Cleanup function called on exit."""
        with self._lock:
            active_stream_ids = list(self._active_streams.keys())
            for stream_id in active_stream_ids:
                if self._active_streams[stream_id]['status'] == 'active':
                    self.end_stream_session(stream_id, {'cleanup_reason': 'application_exit'})

# Global streaming logger instance
_streaming_logger_instance: Optional[StreamingLogger] = None

def setup_streaming_logger(device_name: Optional[str] = None, log_base_dir: str = "data/logs") -> StreamingLogger:
    """Setup streaming logger system."""
    global _streaming_logger_instance
    _streaming_logger_instance = StreamingLogger(device_name, log_base_dir)
    return _streaming_logger_instance

def get_streaming_logger() -> Optional[StreamingLogger]:
    """Get the global streaming logger instance."""
    return _streaming_logger_instance

if __name__ == "__main__":
    # Test the streaming logger
    print("Testing Streaming Logger...")
    
    # Setup logger
    streaming_logger = setup_streaming_logger("test_device")
    
    # Test multiple streams
    streams = [
        {"stream_id": "stream_001", "params": {"type": "rtsp", "resolution": "1080p", "fps": 30}},
        {"stream_id": "stream_002", "params": {"type": "webrtc", "resolution": "720p", "fps": 25}},
        {"stream_id": "stream_003", "params": {"type": "hls", "resolution": "480p", "fps": 20}}
    ]
    
    # Start streams
    for stream_info in streams:
        stream_id = stream_info["stream_id"]
        params = stream_info["params"]
        
        logger = streaming_logger.start_stream_session(stream_id, params)
        
        # Log some streaming activities
        streaming_logger.log_stream_status(stream_id, {"status": "starting", "bitrate": 1024})
        streaming_logger.log_viewer_activity(stream_id, "connected", {"viewer_ip": "192.168.1.100"})
        streaming_logger.log_stream_metrics(stream_id, {"fps": params["fps"], "bitrate_kbps": 1024, "dropped_frames": 0})
        
        time.sleep(1)
    
    # Show active streams
    print("\nActive Streams:")
    active = streaming_logger.get_active_streams()
    for stream_id, info in active.items():
        print(f"  {stream_id}: {info['duration_seconds']}s active ({info['stream_params']['type']})")
    
    # End some streams
    print("\nEnding streams...")
    for stream_info in streams:
        stream_id = stream_info["stream_id"]
        final_metrics = {
            "total_viewers": 5,
            "peak_bitrate_kbps": 1200,
            "total_dropped_frames": 3,
            "average_fps": stream_info["params"]["fps"] - 1
        }
        streaming_logger.end_stream_session(stream_id, final_metrics)
        time.sleep(0.5)
    
    # Show summary
    print("\nStreaming Summary:")
    summary = streaming_logger.get_streaming_summary()
    print(f"Device: {summary['device_name']}")
    print(f"Active streams: {summary['total_active_streams']}")
    print(f"Completed streams: {summary['total_completed_streams']}")
    
    for stream in summary['completed_streams']:
        print(f"  {stream['stream_id']}: {stream['duration_seconds']}s ({stream['file_path']})")