"""
Tests for S3UploadLocationRepository.
"""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from freezegun import freeze_time

from epistemix_api.repositories.s3_upload_location_repository import (
    S3UploadLocationRepository,
    DummyS3UploadLocationRepository,
    create_upload_location_repository
)
from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.models.upload_content import UploadContent
from epistemix_api.models.job_upload import JobUpload


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
        """Test getting upload location with valid JobUpload."""
        # Arrange
        mock_s3_client.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test-file?signature=abc123"
        job_upload = JobUpload(
            context="job",
            upload_type="input",
            job_id=123
        )
        
        # Act
        result = repository.get_upload_location(job_upload)
        
        # Assert
        assert isinstance(result, UploadLocation)
        assert result.url == "https://test-bucket.s3.amazonaws.com/test-file?signature=abc123"
        mock_s3_client.generate_presigned_url.assert_called_once()
    
    def test_get_upload_location__empty_resource_name__raises_value_error(self, repository):
        """Test that None JobUpload raises ValueError."""
        with pytest.raises(ValueError, match="JobUpload cannot be None"):
            repository.get_upload_location(None)
    
    def test_get_upload_location__s3_client_error__raises_value_error(self, repository, mock_s3_client):
        """Test that S3 client error is handled properly."""
        # Arrange
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}
        mock_s3_client.generate_presigned_url.side_effect = ClientError(error_response, 'generate_presigned_url')
        job_upload = JobUpload(
            context="job",
            upload_type="config",
            job_id=456
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="Failed to generate upload location"):
            repository.get_upload_location(job_upload)
    
    @freeze_time("2025-01-15 14:30:45")
    def test_generate_s3_key__normal_filename__adds_timestamp_prefix(self, repository):
        """Test that S3 key generation works correctly for files without job_id."""
        result = repository._generate_s3_key("test-file.txt")
        
        # Should have timestamp prefix format for non-job files: YYYY/MM/DD/HHMMSS/test-file.txt
        assert result == "2025/01/15/143045/test-file.txt"
    
    @freeze_time("2025-01-15 14:30:45")
    def test_generate_s3_key__filename_with_spaces__replaces_spaces(self, repository):
        """Test that spaces in filename are replaced with underscores."""
        result = repository._generate_s3_key("test file name.txt")
        assert result == "2025/01/15/143045/test_file_name.txt"
    
    @freeze_time("2025-02-28 09:15:30")
    def test_generate_s3_key__job_input__creates_proper_structure(self, repository):
        """Test that job_input resources get proper S3 key structure."""
        result = repository._generate_s3_key("job_123_job_input")
        
        # Should have new format: /jobs/123/YYYY/MM/DD/HHMMSS/job_input.zip
        assert result == "/jobs/123/2025/02/28/091530/job_input.zip"
    
    @freeze_time("2025-12-31 23:59:59")
    def test_generate_s3_key__job_config__creates_proper_structure(self, repository):
        """Test that job_config resources get proper S3 key structure."""
        result = repository._generate_s3_key("job_456_job_config")
        
        # Should have new format: /jobs/456/YYYY/MM/DD/HHMMSS/job_config.json
        assert result == "/jobs/456/2025/12/31/235959/job_config.json"
    
    @freeze_time("2025-07-04 16:20:00")
    def test_generate_s3_key__run_config__creates_proper_structure(self, repository):
        """Test that run_config resources get proper S3 key structure."""
        result = repository._generate_s3_key("job_789_run_config")
        
        # Should have new format: /jobs/789/YYYY/MM/DD/HHMMSS/run_config.json
        assert result == "/jobs/789/2025/07/04/162000/run_config.json"
    
    @freeze_time("2025-03-15 08:45:12")
    def test_generate_s3_key__run_with_id_config__creates_proper_structure(self, repository):
        """Test that run_config with run_id gets proper S3 key structure."""
        result = repository._generate_s3_key("job_111_run_222_run_config")
        
        # Should have new format: /jobs/111/YYYY/MM/DD/HHMMSS/run_config.json
        assert result == "/jobs/111/2025/03/15/084512/run_config.json"
    
    def test_read_content__valid_location__returns_upload_content(self, repository, mock_s3_client):
        """Test reading content from a valid location."""
        # Arrange
        location = UploadLocation(url="https://test-bucket.s3.amazonaws.com/2024/01/01/test-file.txt")
        mock_response = {
            'Body': Mock(read=Mock(return_value=b"Hello, World!"))
        }
        mock_s3_client.get_object.return_value = mock_response
        
        # Act
        content = repository.read_content(location)
        
        # Assert
        assert isinstance(content, UploadContent)
        assert content.content_type.value == "text"
        assert content.raw_content == "Hello, World!"
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="2024/01/01/test-file.txt"
        )
    
    def test_read_content__json_file__returns_json_content(self, repository, mock_s3_client):
        """Test reading JSON content."""
        # Arrange
        location = UploadLocation(url="https://test-bucket.s3.amazonaws.com/config.json")
        json_data = '{"key": "value", "number": 42}'
        mock_response = {
            'Body': Mock(read=Mock(return_value=json_data.encode()))
        }
        mock_s3_client.get_object.return_value = mock_response
        
        # Act
        content = repository.read_content(location)
        
        # Assert
        assert content.content_type.value == "json"
        assert content.raw_content == json_data
    
    def test_read_content__binary_file__returns_content(self, repository, mock_s3_client):
        """Test reading binary-like content that can be decoded."""
        # Arrange
        location = UploadLocation(url="https://test-bucket.s3.amazonaws.com/binary.dat")
        # This binary data can actually be decoded as latin-1, which is expected behavior
        binary_data = b'\x00\x01\x02\x03\x04\x05'
        mock_response = {
            'Body': Mock(read=Mock(return_value=binary_data))
        }
        mock_s3_client.get_object.return_value = mock_response
        
        # Act
        content = repository.read_content(location)
        
        # Assert
        # The content should be successfully decoded (latin-1 can decode any byte sequence)
        assert isinstance(content, UploadContent)
        # It's correctly treated as text since it could be decoded
        assert content.content_type.value == "text"
    
    def test_read_content__s3_error__raises_value_error(self, repository, mock_s3_client):
        """Test that S3 errors are properly handled."""
        # Arrange
        location = UploadLocation(url="https://test-bucket.s3.amazonaws.com/missing.txt")
        error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'Key not found'}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, 'get_object')
        
        # Act & Assert
        with pytest.raises(ValueError, match="S3 error.*NoSuchKey"):
            repository.read_content(location)
    
    def test_read_content__invalid_url__raises_value_error(self, repository):
        """Test that invalid URLs raise an error."""
        # Arrange
        location = UploadLocation(url="not-a-valid-url")
        
        # Act & Assert
        with pytest.raises(ValueError):
            repository.read_content(location)


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
        job_upload = JobUpload(
            context="job",
            upload_type="input",
            job_id=789
        )
        result = repository.get_upload_location(job_upload)
        
        assert isinstance(result, UploadLocation)
        assert result.url == "http://localhost:5001/pre-signed-url"
    
    def test_get_upload_location__ignores_resource_name(self):
        """Test that different JobUploads return the same URL."""
        repository = DummyS3UploadLocationRepository()
        job_upload1 = JobUpload(
            context="job",
            upload_type="input",
            job_id=111
        )
        job_upload2 = JobUpload(
            context="run",
            upload_type="config",
            job_id=222,
            run_id=333
        )
        result1 = repository.get_upload_location(job_upload1)
        result2 = repository.get_upload_location(job_upload2)
        
        assert result1.url == result2.url
    
    def test_read_content__returns_dummy_content(self):
        """Test that read_content returns dummy text content."""
        repository = DummyS3UploadLocationRepository()
        location = UploadLocation(url="http://example.com/any-url")
        
        content = repository.read_content(location)
        
        assert isinstance(content, UploadContent)
        assert content.content_type.value == "text"
        assert content.raw_content == "This is dummy content for testing purposes."


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
