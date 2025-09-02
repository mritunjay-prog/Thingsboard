"""
Services module for various service operations and utilities.

This module contains services for media file processing, S3 uploads,
file management operations, and other service-related utilities.
"""

# Make S3 uploader import optional to avoid boto3 dependency issues
try:
    from .simple_s3_uploader import SimpleS3Uploader, main
    __all__ = [
        'SimpleS3Uploader',
        'main'
    ]
except ImportError as e:
    print(f"⚠️ S3 uploader not available: {e}")
    __all__ = []