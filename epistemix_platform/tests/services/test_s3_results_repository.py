"""
Unit tests for S3ResultsRepository service.

These tests verify the S3 results repository behavior using behavioral
specifications (Gherkin-style), with focus on security (credential sanitization).

Behavioral Specifications:
==========================

Scenario 1: Successfully upload results to S3 and return HTTPS URL
  Given a configured S3 client and bucket name
  And simulation results as ZIP bytes
  When I call upload_results with job_id=12, run_id=4
  Then the S3 client puts the object with correct parameters
  And an UploadLocation is returned with HTTPS URL
  And the URL format is "https://{bucket}.s3.amazonaws.com/results/job_12/run_4.zip"

Scenario 2: Sanitize AWS credentials in ClientError exceptions
  Given an S3 client that raises ClientError with AWS credentials in the message
  When I call upload_results
  Then a ResultsStorageError is raised
  And the error message has AWS access keys replaced with [REDACTED_KEY]
  And the error message has secrets replaced with [REDACTED]
  And the sanitized flag is True

Scenario 3: Sanitize AWS credentials in unexpected exceptions
  Given an S3 client that raises a non-ClientError exception
  When I call upload_results
  Then a ResultsStorageError is raised
  And credentials are sanitized from the error message
  And the sanitized flag is True

Scenario 4: Generate correct S3 object key format
  Given job_id=123 and run_id=45
  When I generate the results key
  Then the key is "results/job_123/run_45.zip"

Scenario 5: Successfully generate presigned download URL
  Given a results URL "https://bucket.s3.amazonaws.com/results/job_12/run_4.zip"
  When I call get_download_url with expiration_seconds=7200
  Then the S3 client generates a presigned URL
  And an UploadLocation with the presigned URL is returned

Scenario 6: Extract S3 key from various URL formats
  Given S3 URLs in different formats:
    - "https://bucket.s3.amazonaws.com/results/job_12/run_4.zip"
    - "https://bucket.s3.us-east-1.amazonaws.com/results/job_12/run_4.zip"
    - "s3://bucket/results/job_12/run_4.zip"
  When I extract the key from each URL
  Then I get "results/job_12/run_4.zip" for all formats

Scenario 7: Reject invalid S3 URL formats
  Given an invalid S3 URL "https://example.com/file.zip"
  When I call get_download_url
  Then a ValueError is raised
  And the error message indicates invalid URL format
"""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from epistemix_platform.exceptions import ResultsStorageError
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories.s3_results_repository import S3ResultsRepository


class TestS3ResultsRepository:
    """Test suite for S3ResultsRepository service."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        return MagicMock()

    @pytest.fixture
    def bucket_name(self):
        """S3 bucket name for testing."""
        return "test-simulation-results"

    @pytest.fixture
    def repository(self, mock_s3_client, bucket_name):
        """Create an S3ResultsRepository instance."""
        return S3ResultsRepository(s3_client=mock_s3_client, bucket_name=bucket_name)

    @pytest.fixture
    def zip_content(self):
        """Sample ZIP file content."""
        return b"fake zip content representing simulation results"

    @pytest.fixture
    def sample_prefix(self):
        """Create a sample JobS3Prefix for testing."""
        from datetime import datetime
        from epistemix_platform.models.job_s3_prefix import JobS3Prefix  # pants: no-infer-dep

        return JobS3Prefix(
            job_id=12,
            timestamp=datetime(2025, 10, 23, 21, 15, 0),
        )

    # ==========================================================================
    # Scenario 1: Successfully upload results to S3 and return HTTPS URL
    # ==========================================================================

    def test_upload_results_success(self, repository, mock_s3_client, bucket_name, zip_content, sample_prefix):
        """
        Given a configured S3 client and bucket name
        And simulation results as ZIP bytes
        When I call upload_results with job_id=12, run_id=4
        Then the S3 client puts the object with correct parameters
        And an UploadLocation is returned with HTTPS URL
        And the URL format is "https://{bucket}.s3.amazonaws.com/results/job_12/run_4.zip"
        """
        # Arrange
        job_id = 12
        run_id = 4

        # Act
        result = repository.upload_results(job_id=job_id, run_id=run_id, zip_content=zip_content, s3_prefix=sample_prefix)

        # Assert
        # Verify S3 put_object was called with correct parameters
        expected_key = "jobs/12/2025/10/23/211500/run_4_results.zip"
        mock_s3_client.put_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=expected_key,
            Body=zip_content,
            ContentType="application/zip",
        )

        # Verify returned URL
        assert isinstance(result, UploadLocation)
        expected_url = f"https://{bucket_name}.s3.amazonaws.com/{expected_key}"
        assert result.url == expected_url

    # ==========================================================================
    # Scenario 2: Sanitize AWS credentials in ClientError exceptions
    # ==========================================================================

    def test_sanitize_credentials_in_client_error(self, repository, mock_s3_client, zip_content, sample_prefix):
        """
        Given an S3 client that raises ClientError with AWS credentials in the message
        When I call upload_results
        Then a ResultsStorageError is raised
        And the error message has AWS access keys replaced with [REDACTED_KEY]
        And the error message has secrets replaced with [REDACTED]
        And the sanitized flag is True
        """
        # Arrange - Using fake credentials that match AWS format patterns
        error_response = {
            "Error": {
                "Code": "AccessDenied",
                "Message": "Access denied for AKIAFAKECREDENTIAL99 with secret ThisIsAFakeSecretKeyForTestingPurposes1234567890",
            }
        }
        mock_s3_client.put_object.side_effect = ClientError(error_response, "PutObject")

        # Act & Assert
        with pytest.raises(ResultsStorageError) as exc_info:
            repository.upload_results(job_id=12, run_id=4, zip_content=zip_content, s3_prefix=sample_prefix)

        # Verify credentials were sanitized
        error_message = str(exc_info.value)
        assert "AKIAFAKECREDENTIAL99" not in error_message  # Key should be redacted
        assert "[REDACTED_KEY]" in error_message
        assert "ThisIsAFakeSecretKeyForTestingPurposes1234567890" not in error_message  # Secret redacted
        assert "[REDACTED]" in error_message

        # Verify sanitized flag
        assert exc_info.value.sanitized is True

    # ==========================================================================
    # Scenario 3: Sanitize AWS credentials in unexpected exceptions
    # ==========================================================================

    def test_sanitize_credentials_in_unexpected_error(self, repository, mock_s3_client, zip_content, sample_prefix):
        """
        Given an S3 client that raises a non-ClientError exception
        When I call upload_results
        Then a ResultsStorageError is raised
        And credentials are sanitized from the error message
        And the sanitized flag is True
        """
        # Arrange - Using fake credentials in unexpected error (must be 20 chars: AKIA + 16)
        mock_s3_client.put_object.side_effect = Exception(
            "Network error with credentials AKIATESTKEY000000XYZ and secret FakeSecretForTestingOnly1234567890XYZABC"
        )

        # Act & Assert
        with pytest.raises(ResultsStorageError) as exc_info:
            repository.upload_results(job_id=12, run_id=4, zip_content=zip_content, s3_prefix=sample_prefix)

        # Verify credentials were sanitized
        error_message = str(exc_info.value)
        assert "AKIATESTKEY000000XYZ" not in error_message
        assert "[REDACTED_KEY]" in error_message
        assert "FakeSecretForTestingOnly1234567890XYZABC" not in error_message

        # Verify sanitized flag
        assert exc_info.value.sanitized is True

    # ==========================================================================
    # Scenario 4: Generate correct S3 object key format
    # ==========================================================================

    def test_generate_results_key_format(self, repository):
        """
        Given job_id=123 and run_id=45
        When I generate the results key
        Then the key is "results/job_123/run_45.zip"
        """
        # Act
        key = repository._generate_results_key(job_id=123, run_id=45)

        # Assert
        assert key == "results/job_123/run_45.zip"

    # ==========================================================================
    # Scenario 5: Successfully generate presigned download URL
    # ==========================================================================

    def test_generate_presigned_download_url(self, repository, mock_s3_client, bucket_name):
        """
        Given a results URL "https://bucket.s3.amazonaws.com/results/job_12/run_4.zip"
        When I call get_download_url with expiration_seconds=7200
        Then the S3 client generates a presigned URL
        And an UploadLocation with the presigned URL is returned
        """
        # Arrange
        results_url = f"https://{bucket_name}.s3.amazonaws.com/results/job_12/run_4.zip"
        presigned_url = "https://presigned-url-with-signature.amazonaws.com/..."
        mock_s3_client.generate_presigned_url.return_value = presigned_url

        # Act
        result = repository.get_download_url(results_url=results_url, expiration_seconds=7200)

        # Assert
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": bucket_name,
                "Key": "results/job_12/run_4.zip",
            },
            ExpiresIn=7200,
        )

        assert isinstance(result, UploadLocation)
        assert result.url == presigned_url

    # ==========================================================================
    # Scenario 6: Extract S3 key from various URL formats
    # ==========================================================================

    @pytest.mark.parametrize(
        "s3_url,expected_key",
        [
            (
                "https://bucket.s3.amazonaws.com/results/job_12/run_4.zip",
                "results/job_12/run_4.zip",
            ),
            (
                "https://bucket.s3.us-east-1.amazonaws.com/results/job_12/run_4.zip",
                "results/job_12/run_4.zip",
            ),
            (
                "s3://bucket/results/job_12/run_4.zip",
                "results/job_12/run_4.zip",
            ),
            (
                "https://bucket.s3.amazonaws.com/results/job_12/run_4.zip?versionId=abc123",
                "results/job_12/run_4.zip",
            ),
        ],
    )
    def test_extract_key_from_various_url_formats(self, repository, s3_url, expected_key):
        """
        Given S3 URLs in different formats
        When I extract the key from each URL
        Then I get "results/job_12/run_4.zip" for all formats
        """
        # Act
        extracted_key = repository._extract_key_from_url(s3_url)

        # Assert
        assert extracted_key == expected_key

    # ==========================================================================
    # Scenario 7: Reject invalid S3 URL formats
    # ==========================================================================

    def test_reject_invalid_s3_url_format(self, repository, mock_s3_client):
        """
        Given an invalid S3 URL "https://example.com/file.zip"
        When I call get_download_url
        Then a ValueError is raised
        And the error message indicates invalid URL format
        """
        # Arrange
        invalid_url = "https://example.com/file.zip"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            repository.get_download_url(results_url=invalid_url)

        assert "invalid" in str(exc_info.value).lower()

    # ==========================================================================
    # Additional Security Tests: Comprehensive Credential Sanitization
    # ==========================================================================

    def test_sanitize_xml_credential_fields(self, repository):
        """
        Verify that XML-formatted AWS credentials are sanitized.
        """
        # Arrange - Using completely fake credentials in XML format
        error_with_xml = """
        <Error>
            <AWSAccessKeyId>AKIAFAKEXML000000000</AWSAccessKeyId>
            <SecretAccessKey>FakeXMLSecretKeyForTestingPurposes12345678901234</SecretAccessKey>
            <Signature>FakeBase64SignatureValueForXMLTesting123456789012</Signature>
        </Error>
        """

        # Act
        sanitized = repository._sanitize_credentials(error_with_xml)

        # Assert
        assert "AKIAFAKEXML000000000" not in sanitized
        assert "<AWSAccessKeyId>[REDACTED_KEY]</AWSAccessKeyId>" in sanitized
        assert "FakeXMLSecretKeyForTestingPurposes12345678901234" not in sanitized
        assert "<SecretAccessKey>[REDACTED]</SecretAccessKey>" in sanitized
        assert "FakeBase64SignatureValueForXMLTesting123456789012" not in sanitized
        assert "<Signature>[REDACTED]</Signature>" in sanitized

    def test_sanitize_json_credential_fields(self, repository):
        """
        Verify that JSON-formatted AWS credentials are sanitized.
        """
        # Arrange - Using completely fake credentials in JSON format
        error_with_json = """
        {
            "AWSAccessKeyId": "AKIAFAKEJSON00000000",
            "SecretAccessKey": "FakeJSONSecretKeyForTestingPurposes12345678901234",
            "Signature": "FakeBase64SignatureValueForJSONTesting123456789012"
        }
        """

        # Act
        sanitized = repository._sanitize_credentials(error_with_json)

        # Assert
        assert "AKIAFAKEJSON00000000" not in sanitized
        assert '"AWSAccessKeyId": "[REDACTED_KEY]"' in sanitized
        assert "FakeJSONSecretKeyForTestingPurposes12345678901234" not in sanitized
        assert '"SecretAccessKey": "[REDACTED]"' in sanitized
        assert "FakeBase64SignatureValueForJSONTesting123456789012" not in sanitized
        assert '"Signature": "[REDACTED]"' in sanitized

    def test_sanitize_mixed_xml_and_json_credentials(self, repository):
        """
        Verify that both XML and JSON credential patterns in the same message are sanitized.
        """
        # Arrange - Using fake values that match AWS patterns but are clearly not real
        error_with_mixed = """
        XML Error: <AWSAccessKeyId>FAKEKEYFORTEST123</AWSAccessKeyId>
        JSON Error: {"AWSAccessKeyId": "DUMMYKEYVALUE456", "SecretAccessKey": "thisisafakelongsecretvaluefortest1234567890"}
        """

        # Act
        sanitized = repository._sanitize_credentials(error_with_mixed)

        # Assert
        # XML credentials should be redacted (tags replaced)
        assert "FAKEKEYFORTEST123" not in sanitized
        assert "<AWSAccessKeyId>[REDACTED_KEY]</AWSAccessKeyId>" in sanitized

        # JSON credentials should be redacted (field values replaced)
        assert "DUMMYKEYVALUE456" not in sanitized
        assert '"AWSAccessKeyId": "[REDACTED_KEY]"' in sanitized
        assert "thisisafakelongsecretvaluefortest1234567890" not in sanitized
        assert '"SecretAccessKey": "[REDACTED]"' in sanitized


# ==========================================================================
# JobS3Prefix Integration Tests
# ==========================================================================


class TestS3ResultsRepositoryWithJobS3Prefix:
    """
    Tests for S3ResultsRepository integration with JobS3Prefix.

    Behavioral Specifications:
    ==========================

    Scenario 1: Upload results using JobS3Prefix
      Given a JobS3Prefix with job_id=12 and timestamp
      And an S3ResultsRepository
      When I call upload_results with the prefix
      Then the S3 client uploads to the prefix-based key
      And the key is "jobs/12/2025/10/23/211500/run_4_results.zip"

    Scenario 2: Multiple uploads use same prefix
      Given a single JobS3Prefix created from job.created_at
      When I upload results for run_4 and run_5
      Then both uploads use the same timestamp directory
      And keys are "jobs/12/.../run_4_results.zip" and "jobs/12/.../run_5_results.zip"

    Scenario 3: Prefix consistency across restarts
      Given a JobS3Prefix created from job.created_at
      When I create repository instances at different times
      Then all uploads still use the original job.created_at timestamp
    """

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        return MagicMock()

    @pytest.fixture
    def bucket_name(self):
        """S3 bucket name for testing."""
        return "test-simulation-results"

    @pytest.fixture
    def repository(self, mock_s3_client, bucket_name):
        """Create an S3ResultsRepository instance."""
        return S3ResultsRepository(s3_client=mock_s3_client, bucket_name=bucket_name)

    @pytest.fixture
    def zip_content(self):
        """Sample ZIP file content."""
        return b"fake zip content representing simulation results"

    @pytest.fixture
    def sample_prefix(self):
        """Create a sample JobS3Prefix for testing."""
        from datetime import datetime
        from epistemix_platform.models.job_s3_prefix import JobS3Prefix  # pants: no-infer-dep

        return JobS3Prefix(
            job_id=12,
            timestamp=datetime(2025, 10, 23, 21, 15, 0),
        )

    # ==========================================================================
    # Scenario 1: Upload results using JobS3Prefix
    # ==========================================================================

    def test_upload_results_with_prefix(self, repository, mock_s3_client, bucket_name, sample_prefix, zip_content):
        """
        Given a JobS3Prefix with job_id=12 and timestamp
        And an S3ResultsRepository
        When I call upload_results with the prefix
        Then the S3 client uploads to the prefix-based key
        And the key is "jobs/12/2025/10/23/211500/run_4_results.zip"
        """
        # Act
        result = repository.upload_results(
            job_id=12,
            run_id=4,
            zip_content=zip_content,
            s3_prefix=sample_prefix,
        )

        # Assert
        # Verify S3 put_object was called with prefix-based key
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args.kwargs

        assert call_kwargs["Bucket"] == bucket_name
        assert call_kwargs["Key"] == "jobs/12/2025/10/23/211500/run_4_results.zip"
        assert call_kwargs["Body"] == zip_content
        assert call_kwargs["ContentType"] == "application/zip"

        # Verify returned URL
        assert isinstance(result, UploadLocation)
        expected_url = f"https://{bucket_name}.s3.amazonaws.com/jobs/12/2025/10/23/211500/run_4_results.zip"
        assert result.url == expected_url

    # ==========================================================================
    # Scenario 2: Multiple uploads use same prefix
    # ==========================================================================

    def test_multiple_uploads_same_prefix(self, repository, mock_s3_client, sample_prefix, zip_content):
        """
        Given a single JobS3Prefix created from job.created_at
        When I upload results for run_4 and run_5
        Then both uploads use the same timestamp directory
        And keys are "jobs/12/.../run_4_results.zip" and "jobs/12/.../run_5_results.zip"
        """
        # Act - Upload for run 4
        result_4 = repository.upload_results(
            job_id=12, run_id=4, zip_content=zip_content, s3_prefix=sample_prefix
        )

        # Act - Upload for run 5 (same prefix!)
        result_5 = repository.upload_results(
            job_id=12, run_id=5, zip_content=zip_content, s3_prefix=sample_prefix
        )

        # Assert - Both calls used put_object
        assert mock_s3_client.put_object.call_count == 2

        # Get the two S3 keys used
        calls = mock_s3_client.put_object.call_args_list
        key_4 = calls[0].kwargs["Key"]
        key_5 = calls[1].kwargs["Key"]

        # Both should use same base prefix
        expected_base = "jobs/12/2025/10/23/211500"
        assert key_4.startswith(expected_base)
        assert key_5.startswith(expected_base)

        # But different run IDs
        assert key_4 == "jobs/12/2025/10/23/211500/run_4_results.zip"
        assert key_5 == "jobs/12/2025/10/23/211500/run_5_results.zip"

    # ==========================================================================
    # Scenario 3: Prefix consistency across restarts
    # ==========================================================================

    def test_prefix_consistency_across_repository_instances(self, mock_s3_client, bucket_name, sample_prefix, zip_content):
        """
        Given a JobS3Prefix created from job.created_at
        When I create repository instances at different times
        Then all uploads still use the original job.created_at timestamp
        """
        # Create first repository instance
        repo1 = S3ResultsRepository(s3_client=mock_s3_client, bucket_name=bucket_name)
        result1 = repo1.upload_results(
            job_id=12, run_id=4, zip_content=zip_content, s3_prefix=sample_prefix
        )

        # Simulate time passing - create second repository instance
        repo2 = S3ResultsRepository(s3_client=mock_s3_client, bucket_name=bucket_name)
        result2 = repo2.upload_results(
            job_id=12, run_id=5, zip_content=zip_content, s3_prefix=sample_prefix  # SAME prefix!
        )

        # Assert - Both uploads used the SAME timestamp
        calls = mock_s3_client.put_object.call_args_list
        key_1 = calls[0].kwargs["Key"]
        key_2 = calls[1].kwargs["Key"]

        # Both share the exact same base prefix (from job.created_at)
        assert "jobs/12/2025/10/23/211500" in key_1
        assert "jobs/12/2025/10/23/211500" in key_2
