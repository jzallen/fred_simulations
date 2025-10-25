"""
Tests for upload_results use case.

Based on Gherkin behavioral specifications:
- Scenario 1: Successfully upload results for completed simulation
- Scenario 2: Upload fails when run does not exist
- Scenario 3: Upload fails when results directory is empty
- Scenario 4: Upload succeeds but database update fails
- Scenario 5: Server-side upload uses IAM credentials (not presigned URLs)
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock

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
def mock_job_repository():
    """Mock job repository."""
    return Mock()


@pytest.fixture
def sample_job():
    """A sample job with known created_at timestamp."""
    from epistemix_platform.models.job import Job

    return Job(
        id=123,
        user_id=100,
        tags=["simulation_job"],
        created_at=datetime(2025, 1, 1, 10, 0, 0),  # Job created at 10:00
    )


@pytest.fixture
def completed_run():
    """A completed simulation run."""
    return Run(
        id=1,
        job_id=123,
        user_id=100,
        created_at=datetime(2025, 1, 1, 12, 0, 0),  # Run created at 12:00 (2 hours after job)
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
        mock_job_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        sample_job,
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
        mock_job_repository.find_by_id.return_value = sample_job
        mock_run_repository.find_by_id.return_value = completed_run
        mock_results_packager.package_directory.return_value = PackagedResults(
            zip_content=b"fake zip content",
            file_count=3,
            total_size_bytes=100,
            directory_name="RUN4",
        )
        mock_results_repository.upload_results.return_value = Mock(
            url="https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        )
        mock_time_provider.now_utc.return_value = fixed_time

        # Act
        results_url = upload_results(
            run_repository=mock_run_repository,
            job_repository=mock_job_repository,
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
        assert (
            completed_run.results_url
            == "https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        )
        assert completed_run.results_uploaded_at == fixed_time
        assert completed_run.status == RunStatus.DONE
        mock_run_repository.save.assert_called_once_with(completed_run)

        # Verify return value
        assert (
            results_url
            == "https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        )

    def test_upload_fails_when_run_does_not_exist(
        self,
        mock_run_repository,
        mock_job_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        sample_job,
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
        mock_job_repository.find_by_id.return_value = sample_job
        mock_run_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Run 999 not found"):
            upload_results(
                run_repository=mock_run_repository,
                job_repository=mock_job_repository,
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
        mock_job_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        sample_job,
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

        mock_job_repository.find_by_id.return_value = sample_job

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
                job_repository=mock_job_repository,
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
        mock_job_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        sample_job,
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

        mock_job_repository.find_by_id.return_value = sample_job
        nonexistent_dir = tmp_path / "DOES_NOT_EXIST"
        mock_run_repository.find_by_id.return_value = completed_run
        mock_results_packager.package_directory.side_effect = InvalidResultsDirectoryError(
            "Results directory does not exist"
        )

        # Act & Assert
        with pytest.raises(InvalidResultsDirectoryError):
            upload_results(
                run_repository=mock_run_repository,
                job_repository=mock_job_repository,
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
        mock_job_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        sample_job,
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

        mock_job_repository.find_by_id.return_value = sample_job

        fixed_time = datetime(2025, 10, 23, 20, 0, 0)
        mock_run_repository.find_by_id.return_value = completed_run
        mock_results_packager.package_directory.return_value = PackagedResults(
            zip_content=b"fake zip", file_count=1, total_size_bytes=10, directory_name="RUN4"
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
                job_repository=mock_job_repository,
                results_packager=mock_results_packager,
                results_repository=mock_results_repository,
                time_provider=mock_time_provider,
                job_id=123,
                run_id=1,
                results_dir=results_dir,
            )

        # Verify exception contains orphaned URL
        assert (
            exc_info.value.orphaned_s3_url
            == "https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        )

        # Verify upload completed
        mock_results_repository.upload_results.assert_called_once()

        # Verify update was attempted
        mock_run_repository.save.assert_called_once()

    def test_server_side_upload_uses_iam_credentials_not_presigned_urls(
        self,
        mock_run_repository,
        mock_job_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        sample_job,
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
        mock_job_repository.find_by_id.return_value = sample_job
        fixed_time = datetime(2025, 10, 23, 20, 0, 0)
        mock_run_repository.find_by_id.return_value = completed_run
        mock_results_packager.package_directory.return_value = PackagedResults(
            zip_content=b"packaged content",
            file_count=5,
            total_size_bytes=1000,
            directory_name="RUN4",
        )
        upload_location_mock = Mock(
            url="https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        )
        mock_results_repository.upload_results.return_value = upload_location_mock
        mock_time_provider.now_utc.return_value = fixed_time

        # Act
        upload_results(
            run_repository=mock_run_repository,
            job_repository=mock_job_repository,
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


# ==========================================================================
# JobS3Prefix Integration Tests
# ==========================================================================


class TestUploadResultsWithJobS3Prefix:
    """
    Tests for upload_results use case integration with JobS3Prefix.

    Behavioral Specifications:
    ==========================

    Scenario 1: Fetch job and create S3 prefix from job.created_at
      Given a job with id=12 and created_at=2025-10-23 21:15:00
      And a run belonging to that job
      When upload_results is called
      Then the job is fetched from job_repository
      And a JobS3Prefix is created from job.created_at
      And the prefix is passed to results_repository.upload_results()

    Scenario 2: Multiple runs use same job timestamp
      Given a job with created_at=2025-10-23 21:15:00
      When upload_results is called for run_4 and run_5
      Then both uploads use the SAME timestamp (job.created_at)
      And both results go to jobs/12/2025/10/23/211500/ directory
    """

    @pytest.fixture
    def mock_job_repository(self):
        """Create a mock job repository."""

        return MagicMock()

    @pytest.fixture
    def sample_job(self):
        """Create a sample job with known created_at."""
        from datetime import datetime

        from epistemix_platform.models.job import Job

        return Job(
            id=12,
            user_id=1,
            tags=["simulation_job"],
            created_at=datetime(2025, 10, 23, 21, 15, 0),  # Fixed timestamp
        )

    @pytest.fixture
    def sample_run(self, sample_job):
        """Create a sample run belonging to the job."""
        from datetime import datetime

        from epistemix_platform.models.run import Run, RunStatus

        return Run(
            id=4,
            job_id=sample_job.id,
            user_id=sample_job.user_id,
            status=RunStatus.RUNNING,
            created_at=datetime(2025, 10, 23, 21, 16, 30),  # Different timestamp!
            updated_at=datetime(2025, 10, 23, 21, 16, 30),
            request={"some": "data"},
        )

    # ==========================================================================
    # Scenario 1: Fetch job and create S3 prefix from job.created_at
    # ==========================================================================

    def test_fetch_job_and_create_prefix_from_job_created_at(
        self,
        mock_run_repository,
        mock_job_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        sample_job,
        sample_run,
        results_dir,
    ):
        """
        Given a job with id=12 and created_at=2025-10-23 21:15:00
        And a run belonging to that job
        When upload_results is called
        Then the job is fetched from job_repository
        And a JobS3Prefix is created from job.created_at
        And the prefix is passed to results_repository.upload_results()
        """
        # Arrange
        from datetime import datetime

        from epistemix_platform.models.job_s3_prefix import JobS3Prefix  # pants: no-infer-dep
        from epistemix_platform.models.upload_location import UploadLocation
        from epistemix_platform.services import PackagedResults

        mock_run_repository.find_by_id.return_value = sample_run
        mock_job_repository.find_by_id.return_value = sample_job
        mock_results_packager.package_directory.return_value = PackagedResults(
            zip_content=b"packaged content",
            file_count=5,
            total_size_bytes=1000,
            directory_name="RUN4",
        )
        mock_results_repository.upload_results.return_value = UploadLocation(
            url="https://bucket.s3.amazonaws.com/jobs/12/2025/10/23/211500/run_4_results.zip"
        )
        fixed_time = datetime(2025, 10, 23, 21, 20, 0)
        mock_time_provider.now_utc.return_value = fixed_time

        # Act
        from epistemix_platform.use_cases.upload_results import upload_results

        results_url = upload_results(
            run_repository=mock_run_repository,
            job_repository=mock_job_repository,  # NEW parameter
            results_packager=mock_results_packager,
            results_repository=mock_results_repository,
            time_provider=mock_time_provider,
            job_id=12,
            run_id=4,
            results_dir=results_dir,
        )

        # Assert - Job was fetched
        mock_job_repository.find_by_id.assert_called_once_with(12)

        # Assert - Results repository received JobS3Prefix
        mock_results_repository.upload_results.assert_called_once()
        call_kwargs = mock_results_repository.upload_results.call_args.kwargs

        # Verify s3_prefix parameter exists and uses job.created_at
        assert "s3_prefix" in call_kwargs
        prefix = call_kwargs["s3_prefix"]
        assert isinstance(prefix, JobS3Prefix)
        assert prefix.job_id == 12
        assert prefix.timestamp == datetime(
            2025, 10, 23, 21, 15, 0
        )  # job.created_at, NOT run.created_at!

    # ==========================================================================
    # Scenario 2: Multiple runs use same job timestamp
    # ==========================================================================

    def test_multiple_runs_use_same_job_timestamp(
        self,
        mock_run_repository,
        mock_job_repository,
        mock_results_packager,
        mock_results_repository,
        mock_time_provider,
        sample_job,
        results_dir,
    ):
        """
        Given a job with created_at=2025-10-23 21:15:00
        When upload_results is called for run_4 and run_5
        Then both uploads use the SAME timestamp (job.created_at)
        And both results go to jobs/12/2025/10/23/211500/ directory
        """
        # Arrange
        from datetime import datetime

        from epistemix_platform.models.run import Run, RunStatus
        from epistemix_platform.models.upload_location import UploadLocation
        from epistemix_platform.services import PackagedResults
        from epistemix_platform.use_cases.upload_results import upload_results

        # Create two runs with DIFFERENT created_at times
        run_4 = Run(
            id=4,
            job_id=12,
            user_id=1,
            status=RunStatus.RUNNING,
            created_at=datetime(2025, 10, 23, 21, 16, 0),  # 21:16:00
            updated_at=datetime(2025, 10, 23, 21, 16, 0),
            request={"some": "data"},
        )
        run_5 = Run(
            id=5,
            job_id=12,
            user_id=1,
            status=RunStatus.RUNNING,
            created_at=datetime(2025, 10, 23, 21, 17, 0),  # 21:17:00 (different!)
            updated_at=datetime(2025, 10, 23, 21, 17, 0),
            request={"some": "data"},
        )

        mock_run_repository.find_by_id.side_effect = [run_4, run_5]
        mock_job_repository.find_by_id.return_value = sample_job
        mock_results_packager.package_directory.return_value = PackagedResults(
            zip_content=b"content", file_count=3, total_size_bytes=500, directory_name="RUN"
        )
        mock_results_repository.upload_results.return_value = UploadLocation(
            url="https://example.com/file.zip"
        )
        mock_time_provider.now_utc.return_value = datetime(2025, 10, 23, 21, 20, 0)

        # Act - Upload for run 4
        upload_results(
            run_repository=mock_run_repository,
            job_repository=mock_job_repository,
            results_packager=mock_results_packager,
            results_repository=mock_results_repository,
            time_provider=mock_time_provider,
            job_id=12,
            run_id=4,
            results_dir=results_dir,
        )

        # Act - Upload for run 5
        upload_results(
            run_repository=mock_run_repository,
            job_repository=mock_job_repository,
            results_packager=mock_results_packager,
            results_repository=mock_results_repository,
            time_provider=mock_time_provider,
            job_id=12,
            run_id=5,
            results_dir=results_dir,
        )

        # Assert - Both uploads used the SAME job.created_at timestamp
        assert mock_results_repository.upload_results.call_count == 2

        calls = mock_results_repository.upload_results.call_args_list
        prefix_4 = calls[0].kwargs["s3_prefix"]
        prefix_5 = calls[1].kwargs["s3_prefix"]

        # Both prefixes should use job.created_at, NOT run.created_at
        assert prefix_4.timestamp == datetime(2025, 10, 23, 21, 15, 0)  # job.created_at
        assert prefix_5.timestamp == datetime(2025, 10, 23, 21, 15, 0)  # Same!

        # This ensures both go to the same S3 directory
        assert prefix_4.base_prefix == "jobs/12/2025/10/23/211500"
        assert prefix_5.base_prefix == "jobs/12/2025/10/23/211500"  # Identical!
