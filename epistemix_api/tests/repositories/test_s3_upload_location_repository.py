"""
Tests for S3UploadLocationRepository.
"""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from epistemix_api.repositories.s3_upload_location_repository import (
    S3UploadLocationRepository,
    DummyS3UploadLocationRepository,
    create_upload_location_repository
)
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


class TestDummyS3UploadLocationRepository:
    """Test cases for the DummyS3UploadLocationRepository."""
    
    def test_init__with_default_url(self):
        """Test initialization with default URL."""
        repository = DummyS3UploadLocationRepository()
        assert repository.test_url == "http://localhost:5001/pre-signed-url"
    
    def test_init__with_custom_url(self):
        """Test initialization with custom URL."""
        custom_url = "http://test.example.com/upload"
        repository = DummyS3UploadLocationRepository(test_url=custom_url)
        assert repository.test_url == custom_url
    
    def test_get_upload_location__returns_fixed_url(self):
        """Test that get_upload_location returns the fixed URL."""
        repository = DummyS3UploadLocationRepository()
        result = repository.get_upload_location("test-resource")
        
        assert isinstance(result, UploadLocation)
        assert result.url == "http://localhost:5001/pre-signed-url"
    
    def test_get_upload_location__ignores_resource_name(self):
        """Test that resource name is ignored and same URL is returned."""
        repository = DummyS3UploadLocationRepository()
        result1 = repository.get_upload_location("resource1")
        result2 = repository.get_upload_location("resource2")
        
        assert result1.url == result2.url


class TestCreateUploadLocationRepository:
    """Test cases for the factory method."""
    
    @patch('epistemix_api.repositories.s3_upload_location_repository.boto3.client')
    def test_create_upload_location_repository__testing_env__returns_dummy(self, mock_boto3_client):
        """Test that TESTING environment returns DummyS3UploadLocationRepository."""
        repository = create_upload_location_repository(env="TESTING")
        
        assert isinstance(repository, DummyS3UploadLocationRepository)
        assert repository.test_url == "http://localhost:5001/pre-signed-url"
        # boto3 should not be called for testing environment
        mock_boto3_client.assert_not_called()
    
    @patch('epistemix_api.repositories.s3_upload_location_repository.boto3.client')
    def test_create_upload_location_repository__testing_env_with_custom_url(self, mock_boto3_client):
        """Test that TESTING environment with custom URL works."""
        custom_url = "http://custom.test.url"
        repository = create_upload_location_repository(
            env="TESTING", 
            test_url=custom_url
        )
        
        assert isinstance(repository, DummyS3UploadLocationRepository)
        assert repository.test_url == custom_url
    
    @patch('epistemix_api.repositories.s3_upload_location_repository.boto3.client')
    def test_create_upload_location_repository__production_env__returns_s3(self, mock_boto3_client):
        """Test that PRODUCTION environment returns S3UploadLocationRepository."""
        mock_boto3_client.return_value.meta.region_name = "us-east-1"
        
        repository = create_upload_location_repository(
            env="PRODUCTION",
            bucket_name="test-bucket",
            region_name="us-east-1"
        )
        
        assert isinstance(repository, S3UploadLocationRepository)
        assert repository.bucket_name == "test-bucket"
        mock_boto3_client.assert_called_once()
    
    def test_create_upload_location_repository__production_without_bucket__raises_error(self):
        """Test that production environment without bucket name raises error."""
        with pytest.raises(ValueError, match="bucket_name is required for PRODUCTION environment"):
            create_upload_location_repository(env="PRODUCTION")
    
    @patch('epistemix_api.repositories.s3_upload_location_repository.boto3.client')
    def test_create_upload_location_repository__development_env__returns_s3(self, mock_boto3_client):
        """Test that DEVELOPMENT environment returns S3UploadLocationRepository."""
        mock_boto3_client.return_value.meta.region_name = "us-west-2"
        
        repository = create_upload_location_repository(
            env="DEVELOPMENT",
            bucket_name="dev-bucket",
            region_name="us-west-2"
        )
        
        assert isinstance(repository, S3UploadLocationRepository)
        assert repository.bucket_name == "dev-bucket"
    
    @patch('epistemix_api.repositories.s3_upload_location_repository.boto3.client')
    def test_create_upload_location_repository__unknown_env__returns_s3(self, mock_boto3_client):
        """Test that unknown environment defaults to S3UploadLocationRepository."""
        mock_boto3_client.return_value.meta.region_name = "eu-west-1"
        
        repository = create_upload_location_repository(
            env="STAGING",
            bucket_name="staging-bucket"
        )
        
        assert isinstance(repository, S3UploadLocationRepository)
        assert repository.bucket_name == "staging-bucket"
