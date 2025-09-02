#!/usr/bin/env python3

import os
import boto3
import json
import argparse
from pathlib import Path
from typing import Optional, List
from botocore.exceptions import ClientError
import configparser

class SimpleS3Uploader:
    def __init__(self, config_path: str = "data/config/config.properties", device_id: str = None):
        """
        Initialize the Simple S3 Uploader
        
        Args:
            config_path: Path to configuration file (optional, only for AWS credentials)
            device_id: Device ID to include in folder structure and metadata (optional)
        """
        self.s3_client = None
        self.config = None
        self.device_id = device_id
        
        # Try to load config if it exists (only for AWS credentials)
        if os.path.exists(config_path):
            self.config = self._load_config(config_path)
            self._initialize_s3_from_config()
        else:
            print(f"Config file not found at {config_path}. Will use environment variables or manual setup.")
        
        if self.device_id:
            print(f"📱 Device ID set to: {self.device_id}")
    
    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        """Load configuration from properties file"""
        config = configparser.ConfigParser()
        config.read(config_path)
        return config
    
    def _initialize_s3_from_config(self):
        """Initialize S3 client from config file"""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.config.get('DEFAULT', 's3.region'),
                aws_access_key_id=self.config.get('DEFAULT', 's3.access_key'),
                aws_secret_access_key=self.config.get('DEFAULT', 's3.secret_key')
            )
            print("✅ S3 client initialized from config file")
        except Exception as e:
            print(f"❌ Failed to initialize S3 from config: {e}")
            self.s3_client = None
    
    def setup_s3_credentials(self, region: str = None, access_key: str = None, secret_key: str = None):
        """
        Manually setup S3 credentials
        
        Args:
            region: AWS region (e.g., 'us-east-1')
            access_key: AWS access key ID
            secret_key: AWS secret access key
        """
        try:
            # Use provided credentials or fall back to environment variables
            self.s3_client = boto3.client(
                's3',
                region_name=region or os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
                aws_access_key_id=access_key or os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
            )
            print("✅ S3 client initialized with provided/environment credentials")
        except Exception as e:
            print(f"❌ Failed to initialize S3 client: {e}")
            raise
    
    def upload_file(self, file_path: str, bucket_name: str, folder_path: str = "", 
                   custom_filename: str = None, metadata: dict = None) -> bool:
        """
        Upload a single file to S3
        
        Args:
            file_path: Local path to the file to upload
            bucket_name: S3 bucket name
            folder_path: Folder path in S3 (e.g., "data/sensors" or "images/2024")
            custom_filename: Custom filename for S3 (optional, uses original if not provided)
            metadata: Additional metadata to attach to the file
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        if not self.s3_client:
            print("❌ S3 client not initialized. Please setup credentials first.")
            return False
        
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return False
            
            # Determine filename
            filename = custom_filename if custom_filename else file_path.name
            
            # Build S3 key (folder_path + filename)
            if folder_path:
                # Ensure folder_path ends with / if not empty
                folder_path = folder_path.rstrip('/') + '/'
                s3_key = f"{folder_path}{filename}"
            else:
                s3_key = filename
            
            # Prepare extra arguments
            extra_args = {}
            
            # Add metadata if provided
            if metadata:
                extra_args['Metadata'] = {str(k): str(v) for k, v in metadata.items()}
            else:
                extra_args['Metadata'] = {}
            
            # Add device_id to metadata if available
            if self.device_id:
                extra_args['Metadata']['device_id'] = self.device_id
            
            # Set content type based on file extension
            suffix = file_path.suffix.lower()
            content_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.mp4': 'video/mp4',
                '.avi': 'video/x-msvideo',
                '.mov': 'video/quicktime',
                '.json': 'application/json',
                '.csv': 'text/csv',
                '.txt': 'text/plain',
                '.pdf': 'application/pdf',
                '.zip': 'application/zip',
                '.pcd': 'text/plain'
            }
            
            if suffix in content_types:
                extra_args['ContentType'] = content_types[suffix]
            
            # Upload the file
            self.s3_client.upload_file(str(file_path), bucket_name, s3_key, ExtraArgs=extra_args)
            
            s3_url = f"s3://{bucket_name}/{s3_key}"
            print(f"✅ Successfully uploaded: {file_path.name} -> {s3_url}")
            return True
            
        except ClientError as e:
            print(f"❌ S3 upload failed for {file_path}: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error uploading {file_path}: {e}")
            return False
    
    def upload_directory(self, directory_path: str, bucket_name: str, folder_path: str = "",
                        file_extensions: List[str] = None, recursive: bool = False) -> dict:
        """
        Upload all files from a directory to S3
        
        Args:
            directory_path: Local directory path
            bucket_name: S3 bucket name
            folder_path: Folder path in S3
            file_extensions: List of file extensions to upload (e.g., ['.jpg', '.png'])
            recursive: Whether to upload files from subdirectories
            
        Returns:
            dict: Summary of upload results
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            print(f"❌ Directory not found: {directory_path}")
            return {"success": 0, "failed": 0, "files": []}
        
        # Get files to upload
        files_to_upload = []
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in directory_path.glob(pattern):
            if file_path.is_file():
                # Filter by extensions if provided
                if file_extensions:
                    if file_path.suffix.lower() in [ext.lower() for ext in file_extensions]:
                        files_to_upload.append(file_path)
                else:
                    files_to_upload.append(file_path)
        
        print(f"📁 Found {len(files_to_upload)} files to upload from {directory_path}")
        
        # Upload files
        successful_uploads = 0
        failed_uploads = 0
        uploaded_files = []
        
        for file_path in files_to_upload:
            # Preserve directory structure if recursive
            if recursive:
                relative_path = file_path.relative_to(directory_path)
                file_folder = folder_path + "/" + str(relative_path.parent) if str(relative_path.parent) != "." else folder_path
            else:
                file_folder = folder_path
            
            metadata = {
                "source_directory": str(directory_path),
                "upload_timestamp": str(int(os.path.getmtime(file_path)))
            }
            
            if self.upload_file(str(file_path), bucket_name, file_folder, metadata=metadata):
                successful_uploads += 1
                uploaded_files.append({
                    "local_path": str(file_path),
                    "s3_key": f"{file_folder.rstrip('/')}/{file_path.name}" if file_folder else file_path.name,
                    "size_bytes": file_path.stat().st_size
                })
            else:
                failed_uploads += 1
        
        result = {
            "success": successful_uploads,
            "failed": failed_uploads,
            "files": uploaded_files
        }
        
        print(f"📊 Upload completed: {successful_uploads} successful, {failed_uploads} failed")
        return result
    
    def list_bucket_contents(self, bucket_name: str, prefix: str = "", max_keys: int = 100) -> List[dict]:
        """
        List contents of an S3 bucket
        
        Args:
            bucket_name: S3 bucket name
            prefix: Prefix to filter objects (folder path)
            max_keys: Maximum number of objects to return
            
        Returns:
            List of objects in the bucket
        """
        if not self.s3_client:
            print("❌ S3 client not initialized")
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            objects = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    objects.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        's3_url': f"s3://{bucket_name}/{obj['Key']}"
                    })
            
            print(f"📋 Found {len(objects)} objects in s3://{bucket_name}/{prefix}")
            return objects
            
        except ClientError as e:
            print(f"❌ Failed to list bucket contents: {e}")
            return []
    
    def generate_presigned_url(self, bucket_name: str, object_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for downloading an object
        
        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            expires_in: URL expiration time in seconds
            
        Returns:
            Presigned URL or None if failed
        """
        if not self.s3_client:
            print("❌ S3 client not initialized")
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=expires_in
            )
            print(f"🔗 Generated presigned URL (expires in {expires_in}s): {url}")
            return url
        except ClientError as e:
            print(f"❌ Failed to generate presigned URL: {e}")
            return None


def main():
    """Command line interface for the Simple S3 Uploader"""
    parser = argparse.ArgumentParser(description="Simple S3 Uploader")
    parser.add_argument('action', choices=['upload-file', 'upload-dir', 'list', 'url'], 
                       help='Action to perform')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--folder', default='', help='Folder path in S3 (e.g., data/sensors)')
    parser.add_argument('--file', help='File path to upload (for upload-file)')
    parser.add_argument('--directory', help='Directory path to upload (for upload-dir)')
    parser.add_argument('--extensions', help='File extensions to upload (comma-separated, e.g., .jpg,.png)')
    parser.add_argument('--recursive', action='store_true', help='Upload subdirectories recursively')
    parser.add_argument('--object-key', help='S3 object key (for url action)')
    parser.add_argument('--expires', type=int, default=3600, help='URL expiration time in seconds')
    parser.add_argument('--device-id', help='Device ID to include in metadata and optionally folder structure')
    parser.add_argument('--region', help='AWS region')
    parser.add_argument('--access-key', help='AWS access key ID')
    parser.add_argument('--secret-key', help='AWS secret access key')
    
    args = parser.parse_args()
    
    # Initialize uploader with device_id if provided
    uploader = SimpleS3Uploader(device_id=args.device_id)
    
    # Setup credentials if provided
    if args.region or args.access_key or args.secret_key:
        uploader.setup_s3_credentials(args.region, args.access_key, args.secret_key)
    elif not uploader.s3_client:
        print("❌ No S3 credentials found. Please provide credentials or setup config file.")
        return
    
    # Execute action
    if args.action == 'upload-file':
        if not args.file:
            print("❌ --file is required for upload-file action")
            return
        uploader.upload_file(args.file, args.bucket, args.folder)
    
    elif args.action == 'upload-dir':
        if not args.directory:
            print("❌ --directory is required for upload-dir action")
            return
        extensions = args.extensions.split(',') if args.extensions else None
        result = uploader.upload_directory(args.directory, args.bucket, args.folder, 
                                         extensions, args.recursive)
        print(f"📊 Final result: {json.dumps(result, indent=2)}")
    
    elif args.action == 'list':
        objects = uploader.list_bucket_contents(args.bucket, args.folder)
        for obj in objects:
            print(f"📄 {obj['key']} ({obj['size']} bytes) - {obj['s3_url']}")
    
    elif args.action == 'url':
        if not args.object_key:
            print("❌ --object-key is required for url action")
            return
        uploader.generate_presigned_url(args.bucket, args.object_key, args.expires)


if __name__ == "__main__":
    main()