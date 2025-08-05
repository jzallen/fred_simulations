"""
S3-based upload location repository implementation.
This is a concrete implementation of the IUploadLocationRepository interface using AWS S3.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

from epistemix_api.repositories.interfaces import IUploadLocationRepository
from epistemix_api.models.upload_location import UploadLocation


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
