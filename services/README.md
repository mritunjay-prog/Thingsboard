# Media Module

Media processing and file management utilities

## Files in this module:

- **media_upload_service.py** - IoT device-specific media upload service with fixed hierarchical structure
- **simple_s3_uploader.py** - General-purpose S3 uploader with flexible bucket and folder structure

## Usage

### MediaUploadService (IoT Integration)
```python
from services import MediaUploadService

service = MediaUploadService()
service.upload_snapshot(file_path)  # Fixed structure
```

### SimpleS3Uploader (Flexible)
```python
from services import SimpleS3Uploader

uploader = SimpleS3Uploader(device_id='device-001')
uploader.upload_file('data.json', 'my-bucket', 'custom/folder/path')
```

## Command Line Usage

```bash
# Simple S3 Uploader CLI
python -m media.simple_s3_uploader upload-file \
    --bucket "my-bucket" \
    --folder "custom/path" \
    --file "data.json" \
    --device-id "device-001"
```

This module is part of the IoT Sensor Management System. See the main project README for overall usage instructions.

## Dependencies

Check the main `requirements.txt` for dependencies required by this module.
