"""
Tests for S3UploadLocationRepository.
"""

import os
from datetime import datetime
from unittest.mock import Mock, patch

import boto3
import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.stub import Stubber
from freezegun import freeze_time

from epistemix_platform.models.job import Job
from epistemix_platform.models.job_s3_prefix import JobS3Prefix
from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.upload_content import UploadContent
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories.s3_upload_location_repository import (
    DummyS3UploadLocationRepository,
    S3UploadLocationRepository,
    create_upload_location_repository,
)


class TestS3UploadLocationRepository:
    @pytest.fixture
    def s3_stubber(self):
        os.environ["AWS_ACCESS_KEY_ID"] = "test-access-key"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret-key"

        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_stub = Stubber(s3_client)

        try:
            s3_stub.activate()
            yield s3_client, s3_stub
        finally:
            s3_stub.deactivate()
            os.environ.pop("AWS_ACCESS_KEY_ID", None)
            os.environ.pop("AWS_SECRET_ACCESS_KEY", None)

    @pytest.fixture
    def repository(self, s3_stubber):
        s3_client, _ = s3_stubber
        repo = S3UploadLocationRepository(
            bucket_name="test-bucket", region_name="us-east-1", s3_client=s3_client
        )
        return repo

    @pytest.fixture
    def s3_prefix(self):
        """Fixture providing JobS3Prefix with frozen timestamp matching test frozen time."""
        job = Job(
            id=123, user_id=1, tags=[], created_at=datetime.fromisoformat("2025-01-01 12:00:00")
        )
        return JobS3Prefix.from_job(job)

    @freeze_time("2025-01-01 12:00:00")
    def test_get_upload_location__context_job_and_upload_type_input__returns_zip_upload_location(
        self, repository, s3_stubber, s3_prefix
    ):
        # arrange
        s3_client, _ = s3_stubber
        current_time = datetime.fromisoformat("2025-01-01 12:00:00")
        expiration_seconds = 3600  # 1 hour from repository default
        job_upload = JobUpload(context="job", upload_type="input", job_id=123)

        # Mock generate_presigned_url to capture the call
        original_generate_presigned_url = s3_client.generate_presigned_url
        s3_client.generate_presigned_url = Mock(wraps=original_generate_presigned_url)

        # act
        result = repository.get_upload_location(job_upload, s3_prefix)
        url, querystring = result.url.split("?")
        params = querystring.split("&")

        # assert
        expected_expires_timestamp = int(current_time.timestamp()) + expiration_seconds

        # We expect 3 parameters: AWSAccessKeyId, Signature, Expires
        # ServerSideEncryption is NOT included as it's handled by bucket default encryption
        assert len(params) == 3
        assert isinstance(result, UploadLocation)
        assert (
            url == "https://test-bucket.s3.amazonaws.com/jobs/123/2025/01/01/120000/job_input.zip"
        )

        # Verify all expected parameters are present in query string
        param_dict = dict(param.split("=", 1) for param in params)
        assert "AWSAccessKeyId" in param_dict
        assert "Signature" in param_dict
        assert param_dict.get("Expires") == str(expected_expires_timestamp)

        # Verify that generate_presigned_url was called without ServerSideEncryption parameter
        # (encryption is handled by bucket default settings)
        s3_client.generate_presigned_url.assert_called_once()
        call_args = s3_client.generate_presigned_url.call_args
        assert "ServerSideEncryption" not in call_args[1]["Params"]

    @freeze_time("2025-01-01 12:00:00")
    def test_get_upload_location__context_job_and_upload_type_config__returns_json_upload_location(
        self, repository, s3_stubber, s3_prefix
    ):
        # arrange
        s3_client, _ = s3_stubber
        current_time = datetime.fromisoformat("2025-01-01 12:00:00")
        expiration_seconds = 3600  # 1 hour from repository default
        job_upload = JobUpload(context="job", upload_type="config", job_id=123)

        # Mock generate_presigned_url to capture the call
        original_generate_presigned_url = s3_client.generate_presigned_url
        s3_client.generate_presigned_url = Mock(wraps=original_generate_presigned_url)

        # act
        result = repository.get_upload_location(job_upload, s3_prefix)
        url, querystring = result.url.split("?")
        params = querystring.split("&")

        # assert
        expected_expires_timestamp = int(current_time.timestamp()) + expiration_seconds

        # We expect 3 parameters: AWSAccessKeyId, Signature, Expires
        assert len(params) == 3
        assert isinstance(result, UploadLocation)
        assert (
            url == "https://test-bucket.s3.amazonaws.com/jobs/123/2025/01/01/120000/job_config.json"
        )

        # Verify all expected parameters are present in query string
        param_dict = dict(param.split("=", 1) for param in params)
        assert "AWSAccessKeyId" in param_dict
        assert "Signature" in param_dict
        assert param_dict.get("Expires") == str(expected_expires_timestamp)

        # Verify that generate_presigned_url was called without ServerSideEncryption parameter
        s3_client.generate_presigned_url.assert_called_once()
        call_args = s3_client.generate_presigned_url.call_args
        assert "ServerSideEncryption" not in call_args[1]["Params"]

    @freeze_time("2025-01-01 12:00:00")
    def test_get_upload_location__context_run_and_upload_type_config__returns_json_upload_location(
        self, repository, s3_stubber, s3_prefix
    ):
        # arrange
        s3_client, _ = s3_stubber
        current_time = datetime.fromisoformat("2025-01-01 12:00:00")
        expiration_seconds = 3600  # 1 hour from repository default
        job_upload = JobUpload(context="run", upload_type="config", job_id=123, run_id=456)

        # Mock generate_presigned_url to capture the call
        original_generate_presigned_url = s3_client.generate_presigned_url
        s3_client.generate_presigned_url = Mock(wraps=original_generate_presigned_url)

        # act
        result = repository.get_upload_location(job_upload, s3_prefix)
        url, querystring = result.url.split("?")
        params = querystring.split("&")

        # assert
        expected_expires_timestamp = int(current_time.timestamp()) + expiration_seconds

        # We expect 3 parameters: AWSAccessKeyId, Signature, Expires
        assert len(params) == 3
        assert isinstance(result, UploadLocation)
        assert (
            url
            == "https://test-bucket.s3.amazonaws.com/jobs/123/2025/01/01/120000/run_456_config.json"
        )

        # Verify all expected parameters are present in query string
        param_dict = dict(param.split("=", 1) for param in params)
        assert "AWSAccessKeyId" in param_dict
        assert "Signature" in param_dict
        assert param_dict.get("Expires") == str(expected_expires_timestamp)

        # Verify that generate_presigned_url was called without ServerSideEncryption parameter
        s3_client.generate_presigned_url.assert_called_once()
        call_args = s3_client.generate_presigned_url.call_args
        assert "ServerSideEncryption" not in call_args[1]["Params"]

    def test_get_upload_location__empty_resource_name__raises_value_error(
        self, repository, s3_prefix
    ):
        with pytest.raises(ValueError, match="JobUpload cannot be None"):
            repository.get_upload_location(None, s3_prefix)

    def test_get_upload_location__s3_client_error__raises_value_error(
        self, repository, s3_stubber, s3_prefix
    ):
        s3_client, _ = s3_stubber
        # generate_presigned_url is a local operation and Stubber is only able to mock
        # actual requests to S3
        s3_client.generate_presigned_url = Mock(
            side_effect=ClientError({"Error": {}}, "GeneratePresignedUrl")
        )
        job_upload = JobUpload(context="job", upload_type="config", job_id=456)

        with pytest.raises(ValueError, match="Failed to generate upload location"):
            repository.get_upload_location(job_upload, s3_prefix)

    @freeze_time("2025-01-01 12:00:00")
    def test_get_upload_location__presigned_url_does_not_include_server_side_encryption(
        self, repository, s3_stubber, s3_prefix
    ):
        # Arrange
        s3_client, _ = s3_stubber
        # Mock generate_presigned_url to capture the call
        original_generate_presigned_url = s3_client.generate_presigned_url
        s3_client.generate_presigned_url = Mock(wraps=original_generate_presigned_url)
        job_upload = JobUpload(context="job", upload_type="input", job_id=123)

        # Act
        result = repository.get_upload_location(job_upload, s3_prefix)

        # Assert
        s3_client.generate_presigned_url.assert_called_once()
        call_args = s3_client.generate_presigned_url.call_args

        # Verify that generate_presigned_url was NOT called with ServerSideEncryption parameter
        # Encryption is handled by S3 bucket default encryption settings
        assert "ServerSideEncryption" not in call_args[1]["Params"], (
            "ServerSideEncryption should NOT be in presigned URL params. "
            "It's handled by bucket default encryption to avoid requiring clients to send headers."
        )
        assert isinstance(result, UploadLocation)

    @freeze_time("2025-01-15 14:30:45")
    def test_generate_s3_key__normal_filename__adds_timestamp_prefix(self, repository):
        result = repository._generate_s3_key("test-file.txt")

        # Should have timestamp prefix format for non-job files: YYYY/MM/DD/HHMMSS/test-file.txt
        assert result == "2025/01/15/143045/test-file.txt"

    @freeze_time("2025-01-15 14:30:45")
    def test_generate_s3_key__filename_with_spaces__replaces_spaces(self, repository):
        result = repository._generate_s3_key("test file name.txt")
        assert result == "2025/01/15/143045/test_file_name.txt"

    @freeze_time("2025-02-28 09:15:30")
    def test_generate_s3_key__job_input__creates_proper_structure(self, repository):
        result = repository._generate_s3_key("job_123_job_input")
        assert result == "jobs/123/2025/02/28/091530/job_input.zip"

    @freeze_time("2025-12-31 23:59:59")
    def test_generate_s3_key__job_config__creates_proper_structure(self, repository):
        result = repository._generate_s3_key("job_456_job_config")
        assert result == "jobs/456/2025/12/31/235959/job_config.json"

    @freeze_time("2025-07-04 16:20:00")
    def test_generate_s3_key__run_config__creates_proper_structure(self, repository):
        result = repository._generate_s3_key("job_789_run_config")
        assert result == "jobs/789/2025/07/04/162000/run_config.json"

    @freeze_time("2025-03-15 08:45:12")
    def test_generate_s3_key__run_with_id_config__creates_proper_structure(self, repository):
        result = repository._generate_s3_key("job_111_run_222_run_config")
        assert result == "jobs/111/2025/03/15/084512/run_config.json"

    def test_read_content__valid_location__returns_upload_content(self, repository, s3_stubber):
        # Arrange
        _, s3_stub = s3_stubber
        s3_stub.add_response(
            "get_object",
            {"Body": Mock(read=Mock(return_value=b"Hello, World!"))},
            expected_params={"Bucket": "test-bucket", "Key": "2024/01/01/test-file.txt"},
        )
        location = UploadLocation(
            url="https://test-bucket.s3.amazonaws.com/2024/01/01/test-file.txt"
        )

        # Act
        content = repository.read_content(location)

        # Assert
        assert isinstance(content, UploadContent)
        assert content.content_type.value == "text"
        assert content.raw_content == "Hello, World!"

    def test_read_content__json_file__returns_json_content(self, repository, s3_stubber):
        # Arrange
        _, s3_stub = s3_stubber
        location = UploadLocation(url="https://test-bucket.s3.amazonaws.com/config.json")
        json_data = '{"key": "value", "number": 42}'
        s3_stub.add_response(
            "get_object",
            {"Body": Mock(read=Mock(return_value=json_data.encode()))},
            expected_params={"Bucket": "test-bucket", "Key": "config.json"},
        )

        # Act
        content = repository.read_content(location)

        # Assert
        assert content.content_type.value == "json"
        assert content.raw_content == json_data

    def test_read_content__binary_file__returns_content(self, repository, s3_stubber):
        # Arrange
        _, s3_stub = s3_stubber
        location = UploadLocation(url="https://test-bucket.s3.amazonaws.com/binary.dat")
        # This binary data can actually be decoded as latin-1, which is expected behavior
        binary_data = b"\x00\x01\x02\x03\x04\x05"
        s3_stub.add_response(
            "get_object",
            {"Body": Mock(read=Mock(return_value=binary_data))},
            expected_params={"Bucket": "test-bucket", "Key": "binary.dat"},
        )

        # Act
        content = repository.read_content(location)

        # Assert
        # The content should be successfully decoded (latin-1 can decode any byte sequence)
        assert isinstance(content, UploadContent)
        # It's correctly treated as text since it could be decoded
        assert content.content_type.value == "text"

    def test_read_content__s3_client_error__raises_value_error(self, repository, s3_stubber):
        # Arrange
        _, s3_stub = s3_stubber
        location = UploadLocation(url="https://test-bucket.s3.amazonaws.com/missing.txt")
        s3_stub.add_client_error(
            "get_object",
            service_error_code="NoSuchKey",
            service_message="Key not found",
            expected_params={"Bucket": "test-bucket", "Key": "missing.txt"},
        )

        # Act & Assert
        with pytest.raises(ValueError, match="S3 error.*NoSuchKey"):
            repository.read_content(location)

    def test_read_content__no_aws_credentials__raises_value_error(self):
        mock_s3_client = Mock()
        mock_s3_client.get_object.side_effect = NoCredentialsError
        repository = S3UploadLocationRepository(bucket_name="test-bucket", s3_client=mock_s3_client)
        location = UploadLocation(url="https://test-bucket.s3.amazonaws.com/file.txt")

        with pytest.raises(ValueError, match="AWS credentials error: Unable to locate credentials"):
            repository.read_content(location)

    def test_read_content__invalid_url__raises_value_error(self, repository):
        # Arrange
        location = UploadLocation(url="not-a-valid-url")

        # Act & Assert
        with pytest.raises(ValueError):
            repository.read_content(location)

    @freeze_time("2025-01-15 12:00:00")
    def test_filter_by_age__with_age_threshold__returns_old_uploads(self, repository, s3_stubber):
        # Unpack the stubber
        s3_client, s3_stub = s3_stubber

        # Setup locations with different S3 keys
        location1 = UploadLocation(url="https://test-bucket.s3.amazonaws.com/2025/01/10/file1.txt")
        location2 = UploadLocation(url="https://test-bucket.s3.amazonaws.com/2025/01/14/file2.txt")
        location3 = UploadLocation(url="https://test-bucket.s3.amazonaws.com/2025/01/15/file3.txt")

        # Add stubbed responses for head_object calls
        s3_stub.add_response(
            "head_object",
            {"LastModified": datetime(2025, 1, 10, 10, 0, 0)},  # 5 days old
            {"Bucket": "test-bucket", "Key": "2025/01/10/file1.txt"},
        )

        s3_stub.add_response(
            "head_object",
            {"LastModified": datetime(2025, 1, 14, 10, 0, 0)},  # 1 day old
            {"Bucket": "test-bucket", "Key": "2025/01/14/file2.txt"},
        )

        s3_stub.add_response(
            "head_object",
            {"LastModified": datetime(2025, 1, 15, 10, 0, 0)},  # 2 hours old
            {"Bucket": "test-bucket", "Key": "2025/01/15/file3.txt"},
        )

        # Filter for files older than 2 days
        age_threshold = datetime(2025, 1, 13, 12, 0, 0)
        result = repository.filter_by_age([location1, location2, location3], age_threshold)

        # Should only return the 5-day old file
        assert len(result) == 1
        assert result[0] == location1

    def test_filter_by_age__without_threshold__returns_all(self, repository, s3_stubber):
        # Unpack the stubber
        s3_client, s3_stub = s3_stubber

        # Setup locations
        locations = [
            UploadLocation(url="https://test-bucket.s3.amazonaws.com/file1.txt"),
            UploadLocation(url="https://test-bucket.s3.amazonaws.com/file2.txt"),
        ]

        # No need to add stub responses since we're not making any S3 calls

        result = repository.filter_by_age(locations, None)

        # Should return all locations without checking S3
        assert result == locations

        # Verify no S3 calls were made
        s3_stub.assert_no_pending_responses()

    def test_filter_by_age__handles_s3_errors_gracefully(self, repository, s3_stubber):
        # Unpack the stubber
        s3_client, s3_stub = s3_stubber

        locations = [
            UploadLocation(url="https://test-bucket.s3.amazonaws.com/file1.txt"),
            UploadLocation(url="https://test-bucket.s3.amazonaws.com/file2.txt"),
        ]

        # Add error response for first file
        s3_stub.add_client_error(
            "head_object",
            service_error_code="NoSuchKey",
            service_message="The specified key does not exist.",
            expected_params={"Bucket": "test-bucket", "Key": "file1.txt"},
        )

        # Add successful response for second file
        s3_stub.add_response(
            "head_object",
            {"LastModified": datetime(2025, 1, 10, 10, 0, 0)},
            {"Bucket": "test-bucket", "Key": "file2.txt"},
        )

        age_threshold = datetime(2025, 1, 15, 12, 0, 0)
        result = repository.filter_by_age(locations, age_threshold)

        # Should return only the second file (first had error)
        assert len(result) == 1
        assert result[0] == locations[1]

        # Verify all stubs were used
        s3_stub.assert_no_pending_responses()

    @freeze_time("2025-01-15 12:00:00")
    def test_archive_uploads__transitions_to_glacier(self, repository, s3_stubber):
        # Unpack the stubber
        s3_client, s3_stub = s3_stubber

        locations = [
            UploadLocation(url="https://test-bucket.s3.amazonaws.com/job1/file1.txt"),
            UploadLocation(url="https://test-bucket.s3.amazonaws.com/job2/file2.txt"),
        ]

        # Then copy_object to transition file1 to Glacier
        s3_stub.add_response(
            "copy_object",
            {"CopyObjectResult": {}},
            expected_params={
                "Bucket": "test-bucket",
                "CopySource": {"Bucket": "test-bucket", "Key": "job1/file1.txt"},
                "Key": "job1/file1.txt",
                "MetadataDirective": "COPY",
                "StorageClass": "GLACIER",
            },
        )

        # Then copy_object for file2
        s3_stub.add_response(
            "copy_object",
            {"CopyObjectResult": {}},
            expected_params={
                "Bucket": "test-bucket",
                "CopySource": {"Bucket": "test-bucket", "Key": "job2/file2.txt"},
                "Key": "job2/file2.txt",
                "MetadataDirective": "COPY",
                "StorageClass": "GLACIER",
            },
        )

        result = repository.archive_uploads(locations)

        # Should return both locations as archived
        assert len(result) == 2
        assert result == locations

        # Verify all expected S3 calls were made
        s3_stub.assert_no_pending_responses()

    @freeze_time("2025-01-15 12:00:00")
    def test_archive_uploads__with_age_threshold__filters_by_age(self, repository, s3_stubber):
        _, s3_stub = s3_stubber

        locations = [
            UploadLocation(url="https://test-bucket.s3.amazonaws.com/old_file.txt"),
            UploadLocation(url="https://test-bucket.s3.amazonaws.com/new_file.txt"),
        ]

        # Add head_object responses for age checking
        s3_stub.add_response(
            "head_object",
            {
                "StorageClass": "STANDARD",
                "LastModified": datetime(2025, 1, 5, 10, 0, 0),  # 10 days old
            },
            expected_params={"Bucket": "test-bucket", "Key": "old_file.txt"},
        )

        s3_stub.add_response(
            "head_object",
            {
                "StorageClass": "STANDARD",
                "LastModified": datetime(2025, 1, 14, 10, 0, 0),  # 1 day old
            },
            expected_params={"Bucket": "test-bucket", "Key": "new_file.txt"},
        )

        # Add copy_object response for the old file only (since new file won't be archived)
        s3_stub.add_response(
            "copy_object",
            {"CopyObjectResult": {}},
            expected_params={
                "Bucket": "test-bucket",
                "CopySource": {"Bucket": "test-bucket", "Key": "old_file.txt"},
                "Key": "old_file.txt",
                "MetadataDirective": "COPY",
                "StorageClass": "GLACIER",
            },
        )

        # Archive files older than 7 days
        age_threshold = datetime(2025, 1, 8, 12, 0, 0)
        result = repository.archive_uploads(locations, age_threshold=age_threshold)

        # Should only archive and return the old file
        assert len(result) == 1
        assert result[0] == locations[0]

        # Verify all expected S3 calls were made
        s3_stub.assert_no_pending_responses()

    def test_archive_uploads__handles_copy_errors(self, repository, s3_stubber):
        _, s3_stub = s3_stubber

        locations = [
            UploadLocation(url="https://test-bucket.s3.amazonaws.com/file1.txt"),
            UploadLocation(url="https://test-bucket.s3.amazonaws.com/file2.txt"),
        ]

        # Add client error for first copy operation
        s3_stub.add_client_error(
            "copy_object",
            service_error_code="AccessDenied",
            service_message="Access Denied",
            expected_params={
                "Bucket": "test-bucket",
                "CopySource": {"Bucket": "test-bucket", "Key": "file1.txt"},
                "Key": "file1.txt",
                "MetadataDirective": "COPY",
                "StorageClass": "GLACIER",
            },
        )

        # Add successful response for second file
        s3_stub.add_response(
            "copy_object",
            {"CopyObjectResult": {}},
            expected_params={
                "Bucket": "test-bucket",
                "CopySource": {"Bucket": "test-bucket", "Key": "file2.txt"},
                "Key": "file2.txt",
                "MetadataDirective": "COPY",
                "StorageClass": "GLACIER",
            },
        )

        result = repository.archive_uploads(locations)

        # Should only return the successfully archived file
        assert result == locations
        assert result[0].errors == ["Failed to archive file1.txt: AccessDenied"]
        assert not bool(result[1].errors)

        # Verify all expected S3 calls were made
        s3_stub.assert_no_pending_responses()

    def test_archive_uploads__empty_list__returns_empty(self, repository):
        result = repository.archive_uploads([])

        assert result == []


class TestDummyS3UploadLocationRepository:
    """Test cases for the DummyS3UploadLocationRepository."""

    @pytest.fixture
    def s3_prefix(self):
        """Fixture providing JobS3Prefix with frozen timestamp matching test frozen time."""
        job = Job(
            id=123, user_id=1, tags=[], created_at=datetime.fromisoformat("2025-01-01 12:00:00")
        )
        return JobS3Prefix.from_job(job)

    def test_init__with_default_url(self):
        """Test initialization with default URL."""
        repository = DummyS3UploadLocationRepository()
        assert repository.test_url == "http://localhost:5001/pre-signed-url"

    def test_init__with_custom_url(self):
        """Test initialization with custom URL."""
        custom_url = "http://test.example.com/upload"
        repository = DummyS3UploadLocationRepository(test_url=custom_url)
        assert repository.test_url == custom_url

    def test_get_upload_location__returns_fixed_url(self, s3_prefix):
        """Test that get_upload_location returns the fixed URL."""
        repository = DummyS3UploadLocationRepository()
        job_upload = JobUpload(context="job", upload_type="input", job_id=789)
        result = repository.get_upload_location(job_upload, s3_prefix)

        assert isinstance(result, UploadLocation)
        assert result.url == "http://localhost:5001/pre-signed-url"

    def test_get_upload_location__ignores_resource_name(self, s3_prefix):
        """Test that different JobUploads return the same URL."""
        repository = DummyS3UploadLocationRepository()
        job_upload1 = JobUpload(context="job", upload_type="input", job_id=111)
        job_upload2 = JobUpload(context="run", upload_type="config", job_id=222, run_id=333)
        result1 = repository.get_upload_location(job_upload1, s3_prefix)
        result2 = repository.get_upload_location(job_upload2, s3_prefix)

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

    @patch("epistemix_platform.repositories.s3_upload_location_repository.boto3.client")
    def test_create_upload_location_repository__testing_env__returns_dummy(self, mock_boto3_client):
        """Test that TESTING environment returns DummyS3UploadLocationRepository."""
        repository = create_upload_location_repository(env="TESTING")

        assert isinstance(repository, DummyS3UploadLocationRepository)
        assert repository.test_url == "http://localhost:5001/pre-signed-url"
        # boto3 should not be called for testing environment
        mock_boto3_client.assert_not_called()

    @patch("epistemix_platform.repositories.s3_upload_location_repository.boto3.client")
    def test_create_upload_location_repository__testing_env_with_custom_url(
        self, _mock_boto3_client
    ):
        """Test that TESTING environment with custom URL works."""
        custom_url = "http://custom.test.url"
        repository = create_upload_location_repository(env="TESTING", test_url=custom_url)

        assert isinstance(repository, DummyS3UploadLocationRepository)
        assert repository.test_url == custom_url

    @patch("epistemix_platform.repositories.s3_upload_location_repository.boto3.client")
    def test_create_upload_location_repository__production_env__returns_s3(self, mock_boto3_client):
        """Test that PRODUCTION environment returns S3UploadLocationRepository."""
        mock_boto3_client.return_value.meta.region_name = "us-east-1"

        repository = create_upload_location_repository(
            env="PRODUCTION", bucket_name="test-bucket", region_name="us-east-1"
        )

        assert isinstance(repository, S3UploadLocationRepository)
        assert repository.bucket_name == "test-bucket"
        mock_boto3_client.assert_called_once()

    def test_create_upload_location_repository__production_without_bucket__raises_error(self):
        """Test that production environment without bucket name raises error."""
        with pytest.raises(ValueError, match="bucket_name is required for PRODUCTION environment"):
            create_upload_location_repository(env="PRODUCTION")

    @patch("epistemix_platform.repositories.s3_upload_location_repository.boto3.client")
    def test_create_upload_location_repository__development_env__returns_s3(
        self, mock_boto3_client
    ):
        """Test that DEVELOPMENT environment returns S3UploadLocationRepository."""
        mock_boto3_client.return_value.meta.region_name = "us-west-2"

        repository = create_upload_location_repository(
            env="DEVELOPMENT", bucket_name="dev-bucket", region_name="us-west-2"
        )

        assert isinstance(repository, S3UploadLocationRepository)
        assert repository.bucket_name == "dev-bucket"

    @patch("epistemix_platform.repositories.s3_upload_location_repository.boto3.client")
    def test_create_upload_location_repository__unknown_env__returns_s3(self, mock_boto3_client):
        """Test that unknown environment defaults to S3UploadLocationRepository."""
        mock_boto3_client.return_value.meta.region_name = "eu-west-1"

        repository = create_upload_location_repository(env="STAGING", bucket_name="staging-bucket")

        assert isinstance(repository, S3UploadLocationRepository)
        assert repository.bucket_name == "staging-bucket"
