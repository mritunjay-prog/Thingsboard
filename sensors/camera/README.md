# Camera Sensor Module

The camera sensor module provides comprehensive image and video capture functionality with automatic S3 upload integration.

## Features

- **Image Capture**: Support for JPEG and PNG formats with configurable quality and resolution
- **Video Capture**: MP4 video recording with H.264/H.265 codec support
- **S3 Integration**: Automatic upload to AWS S3 with presigned URL generation
- **Multiple Return Methods**: File URL, Base64 encoding, or S3 URL
- **Flexible Configuration**: Customizable resolution, quality, duration, and format settings
- **Hardware Compatibility**: Works with various camera hardware (libcamera, fswebcam, ffmpeg)
- **Simulation Mode**: Creates test files when camera hardware is not available

## File Structure

```
sensors/camera/
├── __init__.py                    # Module initialization and exports
├── camera_capture_service.py      # Main camera capture service
└── README.md                     # This documentation
```

## API Reference

### Image Capture

**RPC Method**: `camera.capture`

**Parameters**:
```json
{
  "method": "camera.capture",
  "params": {
    "resolution": "full|medium|low",
    "quality": 85,
    "format": "jpeg|png",
    "flash": false,
    "exposure_compensation": 0,
    "white_balance": "auto|daylight|cloudy|tungsten",
    "return_method": "url|base64|s3",
    "s3_upload": {
      "bucket": "papaya-parking-data",
      "prefix": "snapshots/",
      "generate_presigned_url": true,
      "url_expiry_seconds": 3600
    }
  }
}
```

**Response**:
```json
{
  "success": true,
  "image_url": "https://device.url/snapshots/12345.jpg",
  "s3_location": {
    "bucket": "papaya-parking-data",
    "key": "PSM100-123456/snapshots/2025-05-24/img_1716549600000.jpg",
    "region": "us-east-1",
    "presigned_url": "https://papaya-parking-data.s3.amazonaws.com/...",
    "expires_at": 1716553200000
  },
  "image_size_bytes": 485000,
  "capture_timestamp": 1716549600000
}
```

### Video Capture

**RPC Method**: `camera.video.capture`

**Parameters**:
```json
{
  "method": "camera.video.capture",
  "params": {
    "duration_seconds": 30,
    "resolution": "1080p|720p|480p",
    "fps": 30,
    "codec": "h264|h265",
    "bitrate_kbps": 2048,
    "audio_enabled": true,
    "s3_upload": {
      "bucket": "papaya-parking-data",
      "prefix": "videos/",
      "multipart_threshold_mb": 100
    }
  }
}
```

**Response**:
```json
{
  "success": true,
  "video_url": "file:///path/to/video.mp4",
  "s3_location": {
    "bucket": "papaya-parking-data",
    "key": "PSM100-123456/videos/2025-05-24/video_1716549600000.mp4",
    "region": "us-east-1"
  },
  "video_size_bytes": 15750000,
  "capture_timestamp": 1716549600000,
  "duration_seconds": 30
}
```

## Configuration Options

### Image Resolutions
- **full**: 1920x1080 (Full HD)
- **medium**: 1280x720 (HD)
- **low**: 640x480 (VGA)

### Video Resolutions
- **1080p**: 1920x1080 (Full HD)
- **720p**: 1280x720 (HD)
- **480p**: 854x480 (SD)

### Quality Settings
- **JPEG Quality**: 1-100 (recommended: 75-95)
- **Video Bitrate**: 512-4096 kbps (recommended: 1024-2048)
- **Frame Rate**: 15-60 fps (recommended: 30)

## S3 Upload Configuration

The S3 upload feature integrates with the `SimpleS3Uploader` service:

```json
{
  "s3_upload": {
    "bucket": "your-bucket-name",
    "prefix": "folder/subfolder/[DEVICE_ID]/",
    "generate_presigned_url": true,
    "url_expiry_seconds": 3600,
    "multipart_threshold_mb": 100
  }
}
```

- **bucket**: S3 bucket name
- **prefix**: Folder structure (supports [DEVICE_ID] placeholder)
- **generate_presigned_url**: Create downloadable URLs
- **url_expiry_seconds**: URL expiration time
- **multipart_threshold_mb**: File size threshold for multipart uploads

## Hardware Compatibility

The camera service automatically detects and uses available camera hardware:

1. **libcamera** (Raspberry Pi): Primary choice for Pi cameras
2. **fswebcam**: USB/webcam support
3. **ffmpeg**: Universal video capture with v4l2
4. **Simulation Mode**: Fallback for testing without hardware

## File Storage

Captured files are stored in:
- **Temporary Directory**: `data/temp/`
- **Filename Format**: `{device_id}_{timestamp}_{date}_image.{format}`
- **Video Format**: `{device_id}_{timestamp}_{date}_video.mp4`

## Usage Examples

### Basic Image Capture
```python
from sensors import get_camera_capture_service

camera_service = get_camera_capture_service()
result = camera_service.capture_image({
    "resolution": "medium",
    "quality": 85,
    "format": "jpeg"
}, device_id="PSM100-123456")
```

### Video with S3 Upload
```python
result = camera_service.capture_video({
    "duration_seconds": 30,
    "resolution": "720p",
    "fps": 30,
    "s3_upload": {
        "bucket": "my-bucket",
        "prefix": "videos/",
        "generate_presigned_url": True
    }
}, device_id="PSM100-123456")
```

### Service Status
```python
status = camera_service.get_status()
print(f"Camera service: {status}")
```

### Cleanup Old Files
```python
cleanup_result = camera_service.cleanup_temp_files(max_age_hours=24)
print(f"Cleaned up {cleanup_result['deleted_files']} files")
```

## Error Handling

The service provides comprehensive error handling:

- **Hardware Detection**: Graceful fallback to simulation mode
- **S3 Upload Failures**: Continue with local file storage
- **Invalid Parameters**: Clear error messages with validation
- **Timeout Protection**: Prevents hanging capture operations
- **File System Errors**: Proper error reporting and cleanup

## Dependencies

- **boto3**: AWS S3 integration
- **pathlib**: File system operations
- **subprocess**: Camera hardware interface
- **threading**: Concurrent operation support

## Testing

Run the camera demo to test functionality:

```bash
python examples/camera_capture_demo.py
```

This will test:
- Image capture with various configurations
- Video capture with different settings
- S3 upload functionality (if configured)
- Service status and cleanup operations

## Production Deployment

For production use:

1. **Install Camera Drivers**: Ensure proper camera hardware drivers
2. **Configure AWS Credentials**: Set up S3 access keys in config file
3. **Set Permissions**: Ensure camera device access permissions
4. **Test Hardware**: Verify camera functionality before deployment
5. **Monitor Storage**: Implement cleanup schedules for temporary files

## Troubleshooting

### Common Issues

1. **No Camera Hardware**: Service falls back to simulation mode
2. **Permission Denied**: Check camera device permissions (`/dev/video0`)
3. **S3 Upload Fails**: Verify AWS credentials and bucket permissions
4. **Large Video Files**: Adjust bitrate and resolution settings
5. **Storage Full**: Implement regular cleanup schedules

### Debug Mode

Enable debug logging by checking service status and reviewing capture results for detailed error information.
