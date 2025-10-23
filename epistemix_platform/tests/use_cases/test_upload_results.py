"""
Tests for upload_results use case.

Based on Gherkin behavioral specifications:
- Scenario 1: Successfully upload results for completed simulation
- Scenario 2: Upload fails when run does not exist
- Scenario 3: Upload fails when results directory is empty
- Scenario 4: Upload succeeds but database update fails
- Scenario 5: Server-side upload uses IAM credentials (not presigned URLs)
"""

import io
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from epistemix_platform.models.run import Run, RunStatus
from epistemix_platform.services import PackagedResults
from epistemix_platform.use_cases.upload_results import upload_results


@pytest.fixture
def mock_run_repository():
    """Mock run repository."""
    return Mock()


@pytest.fixture
def mock_results_packager():
    """Mock results packager service."""
    return Mock()


@pytest.fixture
def mock_results_repository():
    """Mock results repository for server-side uploads."""
    return Mock()


@pytest.fixture
def mock_time_provider():
    """Mock time provider service."""
    return Mock()


@pytest.fixture
def completed_run():
    """A completed simulation run."""
    return Run(
        id=1,
        job_id=123,
        user_id=100,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 30, 0),
        request={"some": "config"},
        status=RunStatus.RUNNING,  # Status will be updated to DONE after upload
        config_url="https://example.com/config.json",
    )


@pytest.fixture
def results_dir(tmp_path):
    """Create a temporary results directory with sample files."""
    results_path = tmp_path / "RUN4"
    results_path.mkdir()

    # Create sample result files
    (results_path / "out1.txt").write_text("Day 1 results")
    (results_path / "out2.txt").write_text("Day 2 results")
    (results_path / "metrics.csv").write_text("metric,value\ninfected,100")

    return results_path


class TestUploadResults:
    """Test suite for upload_results use case."""

    def test_successfully_upload_results_for_completed_simulation(
        self,
        mock_run_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        completed_run,
        results_dir,
    ):
        """
        Scenario 1: Successfully upload results for completed simulation

        Given a completed simulation run exists with run_id 1
        And the results directory contains simulation output files
        And the S3 results repository is available
        When I upload results for job_id 123 and run_id 1
        Then the results should be zipped
        And the ZIP should be uploaded to S3 using direct boto3 (not presigned URL)
        And the run record should be updated with results_url
        And the run record should be updated with results_uploaded_at timestamp
        And the run status should be set to DONE
        And the function should return the S3 results URL
        """
        # Arrange
        fixed_time = datetime(2025, 10, 23, 20, 0, 0)
        mock_run_repository.find_by_id.return_value = completed_run
        mock_results_packager.package_directory.return_value = PackagedResults(
            zip_content=b"fake zip content",
            file_count=3,
            total_size_bytes=100,
            directory_name="RUN4"
        )
        mock_results_repository.upload_results.return_value = Mock(
            url="https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        )
        mock_time_provider.now_utc.return_value = fixed_time

        # Act
        results_url = upload_results(
            run_repository=mock_run_repository,
            results_packager=mock_results_packager,
            results_repository=mock_results_repository,
            time_provider=mock_time_provider,
            job_id=123,
            run_id=1,
            results_dir=results_dir,
        )

        # Assert
        # Verify run was fetched
        mock_run_repository.find_by_id.assert_called_once_with(1)

        # Verify packaging was called
        mock_results_packager.package_directory.assert_called_once_with(results_dir)

        # Verify upload was called with packaged content
        mock_results_repository.upload_results.assert_called_once()
        call_args = mock_results_repository.upload_results.call_args
        assert call_args.kwargs["job_id"] == 123
        assert call_args.kwargs["run_id"] == 1
        assert call_args.kwargs["zip_content"] == b"fake zip content"

        # Verify time provider was called
        mock_time_provider.now_utc.assert_called_once()

        # Verify run was updated
        assert completed_run.results_url == "https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        assert completed_run.results_uploaded_at == fixed_time
        assert completed_run.status == RunStatus.DONE
        mock_run_repository.save.assert_called_once_with(completed_run)

        # Verify return value
        assert results_url == "https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"

    def test_upload_fails_when_run_does_not_exist(
        self,
        mock_run_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        results_dir,
    ):
        """
        Scenario 2: Upload fails when run does not exist

        Given no simulation run exists for run_id 999
        When I attempt to upload results for job_id 123 and run_id 999
        Then the upload should fail with a ValueError
        And the error message should indicate the run was not found
        And no S3 upload should be attempted
        """
        # Arrange
        mock_run_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Run 999 not found"):
            upload_results(
                run_repository=mock_run_repository,
                results_packager=mock_results_packager,
                results_repository=mock_results_repository,
                time_provider=mock_time_provider,
                job_id=123,
                run_id=999,
                results_dir=results_dir,
            )

        # Verify no packaging or upload was attempted
        mock_results_packager.package_directory.assert_not_called()
        mock_results_repository.upload_results.assert_not_called()
        mock_run_repository.save.assert_not_called()

    def test_upload_fails_when_results_directory_is_empty(
        self,
        mock_run_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        completed_run,
        tmp_path,
    ):
        """
        Scenario 3: Upload fails when results directory is empty

        Given a completed simulation run exists
        And the results directory is empty (no files)
        When I attempt to upload results
        Then the upload should fail with InvalidResultsDirectoryError
        And no S3 upload should be attempted
        """
        # Arrange
        from epistemix_platform.exceptions import InvalidResultsDirectoryError

        empty_dir = tmp_path / "EMPTY_DIR"
        empty_dir.mkdir()
        mock_run_repository.find_by_id.return_value = completed_run
        mock_results_packager.package_directory.side_effect = InvalidResultsDirectoryError(
            "No FRED output directories found"
        )

        # Act & Assert
        with pytest.raises(InvalidResultsDirectoryError):
            upload_results(
                run_repository=mock_run_repository,
                results_packager=mock_results_packager,
                results_repository=mock_results_repository,
                time_provider=mock_time_provider,
                job_id=123,
                run_id=1,
                results_dir=empty_dir,
            )

        # Verify no upload was attempted
        mock_results_repository.upload_results.assert_not_called()
        mock_run_repository.save.assert_not_called()

    def test_upload_fails_when_results_directory_does_not_exist(
        self,
        mock_run_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        completed_run,
        tmp_path,
    ):
        """
        Scenario 3b: Upload fails when results directory does not exist

        Given a completed simulation run exists
        And the results directory path does not exist
        When I attempt to upload results
        Then the upload should fail with InvalidResultsDirectoryError
        And no S3 upload should be attempted
        """
        # Arrange
        from epistemix_platform.exceptions import InvalidResultsDirectoryError

        nonexistent_dir = tmp_path / "DOES_NOT_EXIST"
        mock_run_repository.find_by_id.return_value = completed_run
        mock_results_packager.package_directory.side_effect = InvalidResultsDirectoryError(
            "Results directory does not exist"
        )

        # Act & Assert
        with pytest.raises(InvalidResultsDirectoryError):
            upload_results(
                run_repository=mock_run_repository,
                results_packager=mock_results_packager,
                results_repository=mock_results_repository,
                time_provider=mock_time_provider,
                job_id=123,
                run_id=1,
                results_dir=nonexistent_dir,
            )

        # Verify no upload was attempted
        mock_results_repository.upload_results.assert_not_called()
        mock_run_repository.save.assert_not_called()

    def test_upload_succeeds_but_database_update_fails(
        self,
        mock_run_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        completed_run,
        results_dir,
    ):
        """
        Scenario 4: Upload succeeds but database update fails

        Given a completed simulation run exists
        And the S3 upload will succeed
        And the database update will fail with an exception
        When I upload results
        Then the S3 upload should complete successfully
        And ResultsMetadataError should be raised with orphaned URL
        """
        # Arrange
        from epistemix_platform.exceptions import ResultsMetadataError

        fixed_time = datetime(2025, 10, 23, 20, 0, 0)
        mock_run_repository.find_by_id.return_value = completed_run
        mock_results_packager.package_directory.return_value = PackagedResults(
            zip_content=b"fake zip",
            file_count=1,
            total_size_bytes=10,
            directory_name="RUN4"
        )
        mock_results_repository.upload_results.return_value = Mock(
            url="https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        )
        mock_time_provider.now_utc.return_value = fixed_time
        mock_run_repository.save.side_effect = Exception("Database connection lost")

        # Act & Assert
        with pytest.raises(ResultsMetadataError) as exc_info:
            upload_results(
                run_repository=mock_run_repository,
                results_packager=mock_results_packager,
                results_repository=mock_results_repository,
                time_provider=mock_time_provider,
                job_id=123,
                run_id=1,
                results_dir=results_dir,
            )

        # Verify exception contains orphaned URL
        assert exc_info.value.orphaned_s3_url == "https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"

        # Verify upload completed
        mock_results_repository.upload_results.assert_called_once()

        # Verify update was attempted
        mock_run_repository.save.assert_called_once()

    def test_server_side_upload_uses_iam_credentials_not_presigned_urls(
        self,
        mock_run_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        completed_run,
        results_dir,
    ):
        """
        Scenario 5: Server-side upload uses IAM credentials (not presigned URLs)

        Given a completed simulation run exists
        And the results directory contains files
        When I upload results
        Then the results_repository.upload_results method should be called
        And it should receive the ZIP content as bytes
        And it should NOT use IUploadLocationRepository
        And it should use direct boto3.put_object with IAM credentials
        """
        # Arrange
        fixed_time = datetime(2025, 10, 23, 20, 0, 0)
        mock_run_repository.find_by_id.return_value = completed_run
        mock_results_packager.package_directory.return_value = PackagedResults(
            zip_content=b"packaged content",
            file_count=5,
            total_size_bytes=1000,
            directory_name="RUN4"
        )
        upload_location_mock = Mock(
            url="https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        )
        mock_results_repository.upload_results.return_value = upload_location_mock
        mock_time_provider.now_utc.return_value = fixed_time

        # Act
        upload_results(
            run_repository=mock_run_repository,
            results_packager=mock_results_packager,
            results_repository=mock_results_repository,
            time_provider=mock_time_provider,
            job_id=123,
            run_id=1,
            results_dir=results_dir,
        )

        # Assert
        # Verify the correct repository method was called
        mock_results_repository.upload_results.assert_called_once()

        # Verify it received bytes (ZIP content from packager), not a file path or presigned URL
        call_args = mock_results_repository.upload_results.call_args
        assert "zip_content" in call_args.kwargs
        assert call_args.kwargs["zip_content"] == b"packaged content"

        # Verify job_id and run_id were passed (needed for S3 key generation)
        assert call_args.kwargs["job_id"] == 123
        assert call_args.kwargs["run_id"] == 1

        # Verify results packager was used (clean architecture)
        mock_results_packager.package_directory.assert_called_once_with(results_dir)
