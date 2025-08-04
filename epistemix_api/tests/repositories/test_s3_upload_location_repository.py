"""
Tests for S3UploadLocationRepository.
"""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from epistemix_api.repositories.s3_upload_location_repository import S3UploadLocationRepository
from epistemix_api.models.upload_location import UploadLocation


class TestS3UploadLocationRepository:
    """Test cases for the S3UploadLocationRepository."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        with patch('boto3.client') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def repository(self, mock_s3_client):
        """Create a repository instance with mocked S3 client."""
        repo = S3UploadLocationRepository(
            bucket_name="test-bucket",
            region_name="us-east-1"
        )
        return repo
    
    def test_init__with_region__creates_s3_client(self, mock_s3_client):
        """Test that repository initializes correctly with region."""
        repo = S3UploadLocationRepository(
            bucket_name="test-bucket",
            region_name="us-west-2"
        )
        
        assert repo.bucket_name == "test-bucket"
        assert repo.expiration_seconds == 3600  # default
    
    def test_init__without_region__creates_s3_client(self, mock_s3_client):
        """Test that repository initializes correctly without explicit region."""
        repo = S3UploadLocationRepository(
            bucket_name="test-bucket"
        )
        
        assert repo.bucket_name == "test-bucket"
        assert repo.expiration_seconds == 3600  # default
    
    def test_init__with_custom_expiration__sets_expiration(self, mock_s3_client):
        """Test that custom expiration is set correctly."""
        repo = S3UploadLocationRepository(
            bucket_name="test-bucket",
            expiration_seconds=7200
        )
        
        assert repo.expiration_seconds == 7200
    
    def test_get_upload_location__valid_resource_name__returns_upload_location(self, repository, mock_s3_client):
        """Test getting upload location with valid resource name."""
        # Arrange
        mock_s3_client.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test-file?signature=abc123"
        
        # Act
        result = repository.get_upload_location("test-file.txt")
        
        # Assert
        assert isinstance(result, UploadLocation)
        assert result.url == "https://test-bucket.s3.amazonaws.com/test-file?signature=abc123"
        mock_s3_client.generate_presigned_url.assert_called_once()
    
    def test_get_upload_location__empty_resource_name__raises_value_error(self, repository):
        """Test that empty resource name raises ValueError."""
        with pytest.raises(ValueError, match="Resource name cannot be empty"):
            repository.get_upload_location("")
        
        with pytest.raises(ValueError, match="Resource name cannot be empty"):
            repository.get_upload_location("   ")
    
    def test_get_upload_location__s3_client_error__raises_value_error(self, repository, mock_s3_client):
        """Test that S3 client error is handled properly."""
        # Arrange
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}
        mock_s3_client.generate_presigned_url.side_effect = ClientError(error_response, 'generate_presigned_url')
        
        # Act & Assert
        with pytest.raises(ValueError, match="Failed to generate upload location"):
            repository.get_upload_location("test-file.txt")
    
    def test_generate_s3_key__normal_filename__adds_timestamp_prefix(self, repository):
        """Test that S3 key generation works correctly."""
        result = repository._generate_s3_key("test-file.txt")
        
        # Should have timestamp prefix format: YYYY/MM/DD/HHMMSS/test-file.txt
        parts = result.split('/')
        assert len(parts) == 5
        assert parts[-1] == "test-file.txt"
    
    def test_generate_s3_key__filename_with_spaces__replaces_spaces(self, repository):
        """Test that spaces in filename are replaced with underscores."""
        result = repository._generate_s3_key("test file name.txt")
        
        assert "test_file_name.txt" in result
        assert " " not in result
