"""
S3-based upload location repository implementation.
This is a concrete implementation of the IUploadLocationRepository interface using AWS S3.
"""

import logging
import zipfile
import io
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

from epistemix_api.repositories.interfaces import IUploadLocationRepository
from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.models.upload_content import UploadContent, ZipFileEntry, ContentType


logger = logging.getLogger(__name__)


class S3UploadLocationRepository:
    """
    S3-based implementation of the upload location repository.
    
    This implementation generates pre-signed URLs for uploading files to AWS S3.
    It provides secure, time-limited URLs that can be used directly from a browser
    to upload files without exposing AWS credentials.
    """
    
    def __init__(
        self,
        bucket_name: str,
        region_name: Optional[str] = None,
        expiration_seconds: int = 3600
    ):
        """
        Initialize the S3 upload location repository.
        
        Uses AWS default credential chain for authentication, which looks for credentials in:
        1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        2. AWS credentials file (~/.aws/credentials)
        3. AWS config file (~/.aws/config)
        4. IAM roles for EC2 instances
        5. IAM roles for containers (ECS, EKS)
        6. AWS SSO
        
        Args:
            bucket_name: The S3 bucket name to upload files to
            region_name: AWS region name (optional, will use default region from config/environment)
            expiration_seconds: How long the pre-signed URL should be valid (default: 1 hour)
        """
        self.bucket_name = bucket_name
        self.expiration_seconds = expiration_seconds
        
        # Initialize S3 client using default credential chain
        session_kwargs = {}
        if region_name:
            session_kwargs["region_name"] = region_name
            
        try:
            self.s3_client = boto3.client('s3', **session_kwargs)
            # Get the actual region being used
            actual_region = self.s3_client.meta.region_name or "default"
            logger.info(f"S3 client initialized for bucket: {bucket_name}, region: {actual_region}")
        except (NoCredentialsError, BotoCoreError) as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise ValueError(f"S3 client initialization failed: {e}")
    
    def get_upload_location(self, resource_name: str) -> UploadLocation:
        """
        Generate a pre-signed URL for uploading a file to S3.
        
        Args:
            resource_name: The name/key of the resource to upload
            
        Returns:
            UploadLocation containing the pre-signed URL for upload
            
        Raises:
            ValueError: If the resource_name is invalid or upload location cannot be generated
        """
        if not resource_name or not resource_name.strip():
            raise ValueError("Resource name cannot be empty")
        
        # Sanitize the resource name to ensure it's a valid S3 key
        object_key = self._generate_s3_key(resource_name)
        
        try:
            # Generate pre-signed URL for PUT operation
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=self.expiration_seconds,
                HttpMethod='PUT'
            )
            
            logger.info(f"Generated pre-signed URL for resource: {resource_name} -> {object_key}")
            return UploadLocation(url=presigned_url)
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = f"S3 error ({error_code}): {e}"
            logger.error(error_message)
            raise ValueError(f"Failed to generate upload location: {error_message}")
            
        except (BotoCoreError, Exception) as e:
            error_message = f"Unexpected error generating pre-signed URL: {e}"
            logger.error(error_message)
            raise ValueError(error_message)
    
    def _generate_s3_key(self, resource_name: str) -> str:
        """Produces valid S3 object key from resource with timestamp prefix.
        
        Args:
            resource_name: The original resource name
            
        Returns:
            A valid S3 object key
        """
        # Remove leading/trailing whitespace
        key = resource_name.strip()
        
        # Replace spaces with underscores
        key = key.replace(' ', '_')
        
        # Add timestamp prefix to avoid collisions
        timestamp = datetime.utcnow().strftime("%Y/%m/%d/%H%M%S")
        key = f"{timestamp}/{key}"
        
        return key
    
    def read_content(self, location: UploadLocation) -> UploadContent:
        """
        Read the content from an S3 upload location.
        
        Args:
            location: The upload location containing the URL
            
        Returns:
            UploadContent domain model
            
        Raises:
            ValueError: If the content cannot be read or parsed
        """
        # Extract S3 key from the location URL
        s3_key = self._extract_s3_key_from_url(location.url)
        if not s3_key:
            raise ValueError(f"Could not extract S3 key from URL: {location.url}")
        
        try:
            # Download the object from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Read the content as bytes
            content_bytes = response['Body'].read()
            
            # Parse the content into domain model
            upload_content = self._parse_content(content_bytes, s3_key)
            
            logger.info(f"Successfully read content from S3 key: {s3_key}")
            return upload_content
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = f"S3 error ({error_code}): {e}"
            logger.error(error_message)
            raise ValueError(error_message)
        except NoCredentialsError as e:
            error_message = f"AWS credentials error: {e}"
            logger.error(error_message)
            raise ValueError(error_message)
        except Exception as e:
            error_message = f"Failed to read content: {e}"
            logger.error(error_message)
            raise ValueError(error_message)
    
    def _extract_s3_key_from_url(self, url: str) -> Optional[str]:
        """
        Extract the S3 key from a URL using pattern matching.
        
        Handles various S3 URL formats including pre-signed URLs.
        
        Args:
            url: The URL to parse
            
        Returns:
            The S3 key, or None if invalid
        """
        if not url:
            return None
        
        # Remove query parameters (AWS signature, etc.)
        clean_url = url.split('?')[0] if '?' in url else url
        
        # Use pattern matching for different URL formats
        match clean_url:
            case url if url.startswith(f"s3://{self.bucket_name}/"):
                # s3://bucket/key format
                return url[len(f"s3://{self.bucket_name}/"):]
            
            case url if f"{self.bucket_name}.s3.amazonaws.com/" in url:
                # https://bucket.s3.amazonaws.com/key format
                parts = url.split(f"{self.bucket_name}.s3.amazonaws.com/")
                return parts[1] if len(parts) > 1 else None
            
            case url if f"s3.amazonaws.com/{self.bucket_name}/" in url:
                # https://s3.amazonaws.com/bucket/key format
                parts = url.split(f"s3.amazonaws.com/{self.bucket_name}/")
                return parts[1] if len(parts) > 1 else None
            
            case url if url.startswith(('http://', 'https://')):
                # Generic HTTP(S) URL - parse it
                parsed = urlparse(url)
                path = parsed.path.lstrip('/')
                
                # Check if bucket is in hostname
                if parsed.hostname and self.bucket_name in parsed.hostname:
                    return path if path else None
                
                # Check if bucket is first part of path
                path_parts = path.split('/', 1)
                if len(path_parts) > 1 and path_parts[0] == self.bucket_name:
                    return path_parts[1]
                
                # Assume entire path is the key
                return path if path else None
            
            case _:
                # Treat as raw S3 key
                return clean_url
    
    def _parse_content(self, content_bytes: bytes, s3_key: str) -> UploadContent:
        """
        Parse content bytes into an UploadContent domain model.
        
        Args:
            content_bytes: Raw bytes from S3
            s3_key: The S3 key (used for type hints)
            
        Returns:
            UploadContent domain model
        """
        # Check if this is a zip file
        is_zip = (
            content_bytes[:4] == b'PK\x03\x04' or  # ZIP magic bytes
            content_bytes[:4] == b'PK\x05\x06' or  # Empty ZIP
            s3_key.endswith('.zip') or
            'job_input' in s3_key  # job_input files are typically zips
        )
        
        if is_zip:
            try:
                return self._parse_zip_content(content_bytes)
            except (zipfile.BadZipFile, Exception) as e:
                logger.warning(f"Failed to parse as ZIP, treating as text: {e}")
        
        # Try to decode as text
        try:
            content_str = content_bytes.decode('utf-8')
            
            # Check if it's JSON
            if s3_key.endswith('.json') or self._looks_like_json(content_str):
                return UploadContent.create_json(content_str)
            else:
                return UploadContent.create_text(content_str)
                
        except UnicodeDecodeError:
            # Try other encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    content_str = content_bytes.decode(encoding)
                    return UploadContent.create_text(content_str, encoding=encoding)
                except UnicodeDecodeError:
                    continue
            
            # If all decodings fail, return as binary
            hex_preview = content_bytes.hex()[:200]
            return UploadContent.create_binary(f"[Binary content - hex representation]:\n{hex_preview}...")
    
    def _parse_zip_content(self, content_bytes: bytes) -> UploadContent:
        """Parse ZIP archive content."""
        zip_buffer = io.BytesIO(content_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            entries = []
            content_parts = [f"[ZIP Archive Contents - {len(zip_file.namelist())} files]"]
            content_parts.append("=" * 60)
            
            for file_name in zip_file.namelist():
                info = zip_file.getinfo(file_name)
                
                # Create preview for text files
                preview = None
                if file_name.endswith(('.txt', '.json', '.fred', '.xml', '.csv', '.log', '.py', '.sh')):
                    try:
                        with zip_file.open(file_name) as f:
                            file_content = f.read().decode('utf-8', errors='replace')
                            preview = file_content[:500]
                            if len(file_content) > 500:
                                preview += f"\n... (truncated, {len(file_content)} total chars)"
                    except Exception as e:
                        preview = f"[Could not preview: {e}]"
                
                entry = ZipFileEntry(
                    name=file_name,
                    size=info.file_size,
                    compressed_size=info.compress_size,
                    preview=preview
                )
                entries.append(entry)
                
                # Build text summary
                content_parts.append(f"\n📁 {file_name}")
                content_parts.append(f"   Size: {info.file_size} bytes")
                content_parts.append(f"   Compressed: {info.compress_size} bytes")
                if preview:
                    content_parts.append(f"   Preview:")
                    content_parts.append(f"   {'-' * 40}")
                    for line in preview.split('\n')[:10]:
                        content_parts.append(f"   {line}")
            
            content_summary = "\n".join(content_parts)
            return UploadContent.create_zip_archive(content_summary, entries)
    
    def _looks_like_json(self, content: str) -> bool:
        """Check if content looks like JSON."""
        trimmed = content.strip()
        return (
            (trimmed.startswith('{') and trimmed.endswith('}')) or
            (trimmed.startswith('[') and trimmed.endswith(']'))
        )


class DummyS3UploadLocationRepository:
    """
    Dummy implementation of the upload location repository for testing.
    
    This implementation returns a fixed pre-signed URL without making any
    actual AWS calls. It's used in testing environments to avoid S3 dependencies.
    """
    
    def __init__(self, test_url: str = "http://localhost:5001/pre-signed-url"):
        """
        Initialize the dummy repository with a test URL.
        
        Args:
            test_url: The fixed URL to return for all upload locations
        """
        self.test_url = test_url
        logger.info(f"DummyS3UploadLocationRepository initialized with test URL: {test_url}")
    
    def get_upload_location(self, resource_name: str) -> UploadLocation:
        """
        Generate a dummy upload location for testing.
        
        Args:
            resource_name: The name/key of the resource (ignored in dummy implementation)
            
        Returns:
            UploadLocation containing the test URL
        """
        logger.info(f"Dummy upload location requested for resource: {resource_name}")
        return UploadLocation(url=self.test_url)
    
    def read_content(self, location: UploadLocation) -> UploadContent:
        """
        Return dummy content for testing.
        
        Args:
            location: The upload location (ignored in dummy implementation)
            
        Returns:
            Dummy UploadContent for testing
        """
        logger.info(f"Dummy read content requested for location: {location.url}")
        dummy_content = "This is dummy content for testing purposes."
        return UploadContent.create_text(dummy_content)


def create_upload_location_repository(
    env: str,
    bucket_name: Optional[str] = None,
    region_name: Optional[str] = None,
    **kwargs
) -> IUploadLocationRepository:
    """
    Factory method to create the appropriate upload location repository based on environment.
    
    Args:
        env: The environment (e.g., "TESTING", "PRODUCTION", "DEVELOPMENT")
        bucket_name: S3 bucket name (required for non-testing environments)
        region_name: AWS region name (optional)
        **kwargs: Additional arguments passed to the repository constructor
        
    Returns:
        An instance of IUploadLocationRepository appropriate for the environment
        
    Raises:
        ValueError: If required parameters are missing for the selected repository
    """
    match env.upper():
        case "TESTING":
            test_url = kwargs.get('test_url', "http://localhost:5001/pre-signed-url")
            return DummyS3UploadLocationRepository(test_url=test_url)
        case "PRODUCTION" | "DEVELOPMENT" | _:
            if not bucket_name:
                raise ValueError(f"bucket_name is required for {env} environment")
            return S3UploadLocationRepository(
                bucket_name=bucket_name,
                region_name=region_name,
                expiration_seconds=kwargs.get('expiration_seconds', 3600)
            )
