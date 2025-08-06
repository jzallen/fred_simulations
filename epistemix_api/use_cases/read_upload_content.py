"""
Use case for reading uploaded content from S3.
This use case downloads and returns the human-readable contents of an uploaded file.
"""

import logging
import zipfile
import io
from typing import Optional
from returns.result import Result, Success, Failure

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ReadUploadContent:
    """
    Use case for reading uploaded content from S3.
    
    This use case handles downloading and reading files that were uploaded
    to S3, returning their human-readable contents.
    """
    
    def __init__(self, bucket_name: str, region_name: Optional[str] = None):
        """
        Initialize the read upload content use case.
        
        Args:
            bucket_name: The S3 bucket name to read from
            region_name: AWS region name (optional)
        """
        self.bucket_name = bucket_name
        
        session_kwargs = {}
        if region_name:
            session_kwargs["region_name"] = region_name
            
        try:
            self.s3_client = boto3.client('s3', **session_kwargs)
            logger.info(f"S3 client initialized for reading from bucket: {bucket_name}")
        except (NoCredentialsError, Exception) as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise ValueError(f"S3 client initialization failed: {e}")
    
    def execute(self, upload_location: str) -> Result[str, str]:
        """
        Read the contents of an uploaded file from S3.
        
        Args:
            upload_location: Either an S3 URL or an S3 key
            
        Returns:
            Result containing the file contents as a string, or an error message
        """
        try:
            # Parse the upload location to extract the S3 key
            s3_key = self._extract_s3_key(upload_location)
            
            if not s3_key:
                return Failure("Invalid upload location format")
            
            # Download the object from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Read the content as bytes
            content_bytes = response['Body'].read()
            
            # Check if this is a zip file (by magic bytes or key name)
            is_zip = (
                content_bytes[:4] == b'PK\x03\x04' or  # ZIP magic bytes
                content_bytes[:4] == b'PK\x05\x06' or  # Empty ZIP
                s3_key.endswith('.zip') or
                'job_input' in s3_key  # job_input files are typically zips
            )
            
            if is_zip:
                try:
                    # Handle as a zip file
                    zip_buffer = io.BytesIO(content_bytes)
                    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                        # List all files in the zip
                        file_list = zip_file.namelist()
                        content_parts = [f"[ZIP Archive Contents - {len(file_list)} files]\n"]
                        content_parts.append("=" * 60 + "\n")
                        
                        for file_name in file_list:
                            info = zip_file.getinfo(file_name)
                            content_parts.append(f"\n📁 {file_name}")
                            content_parts.append(f"   Size: {info.file_size} bytes")
                            content_parts.append(f"   Compressed: {info.compress_size} bytes")
                            content_parts.append(f"   Modified: {info.date_time}")
                            
                            # For text files, show a preview
                            if file_name.endswith(('.txt', '.json', '.fred', '.xml', '.csv', '.log', '.py', '.sh')):
                                try:
                                    with zip_file.open(file_name) as f:
                                        file_content = f.read().decode('utf-8', errors='replace')
                                        # Show first 500 chars as preview
                                        preview = file_content[:500]
                                        if len(file_content) > 500:
                                            preview += f"\n   ... (truncated, {len(file_content)} total chars)"
                                        content_parts.append(f"   Preview:\n   {'-' * 40}")
                                        for line in preview.split('\n')[:10]:  # First 10 lines
                                            content_parts.append(f"   {line}")
                                except Exception as e:
                                    content_parts.append(f"   [Could not preview: {e}]")
                            content_parts.append("")
                        
                        content_str = "\n".join(content_parts)
                        logger.info(f"Successfully read ZIP content from S3 key: {s3_key}")
                        return Success(content_str)
                except zipfile.BadZipFile:
                    logger.warning(f"File appears to be ZIP but couldn't be read as ZIP: {s3_key}")
                    # Fall through to try text decoding
                except Exception as e:
                    logger.warning(f"Error reading ZIP file {s3_key}: {e}")
                    # Fall through to try text decoding
            
            # Try to decode as UTF-8 text
            try:
                content_str = content_bytes.decode('utf-8')
                logger.info(f"Successfully read content from S3 key: {s3_key}")
                return Success(content_str)
            except UnicodeDecodeError:
                # If not UTF-8, try other encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        content_str = content_bytes.decode(encoding)
                        logger.info(f"Successfully read content from S3 key: {s3_key} using {encoding} encoding")
                        return Success(content_str)
                    except UnicodeDecodeError:
                        continue
                
                # If all decodings fail, return hex representation
                hex_content = content_bytes.hex()[:200]  # Show first 200 hex chars
                logger.warning(f"Could not decode content as text, returning hex for S3 key: {s3_key}")
                return Success(f"[Binary content - hex representation]:\n{hex_content}...")
                
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = f"S3 error ({error_code}): {e}"
            logger.error(error_message)
            return Failure(error_message)
        except Exception as e:
            error_message = f"Failed to read upload content: {e}"
            logger.error(error_message)
            return Failure(error_message)
    
    def _extract_s3_key(self, upload_location: str) -> Optional[str]:
        """
        Extract the S3 key from an upload location.
        
        The upload location can be:
        - A full S3 URL (https://bucket.s3.amazonaws.com/key or s3://bucket/key)
        - Just the S3 key itself
        
        Args:
            upload_location: The upload location string
            
        Returns:
            The S3 key, or None if invalid
        """
        if not upload_location:
            return None
        
        # If it looks like a URL, parse it
        if upload_location.startswith(('http://', 'https://', 's3://')):
            parsed = urlparse(upload_location)
            
            if upload_location.startswith('s3://'):
                # s3://bucket/key format
                # Remove the bucket name from the path
                path = parsed.path.lstrip('/')
                return path if path else None
            else:
                # https://bucket.s3.amazonaws.com/key format
                # or https://s3.amazonaws.com/bucket/key format
                path = parsed.path.lstrip('/')
                
                # Check if the host contains the bucket name
                if self.bucket_name in parsed.hostname:
                    # Bucket is in the hostname, path is the key
                    return path if path else None
                else:
                    # Bucket might be first part of path
                    parts = path.split('/', 1)
                    if len(parts) > 1 and parts[0] == self.bucket_name:
                        return parts[1]
                    # Otherwise assume the whole path is the key
                    return path if path else None
        else:
            # Assume it's just the S3 key
            return upload_location