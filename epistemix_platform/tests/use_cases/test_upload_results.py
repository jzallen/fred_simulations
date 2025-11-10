from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest

from epistemix_platform.models.run import Run, RunStatus
from epistemix_platform.services import PackagedResults
from epistemix_platform.use_cases.upload_results import upload_results


@pytest.fixture
def mock_run_repository():
    return Mock()


@pytest.fixture
def mock_results_packager():
    return Mock()


@pytest.fixture
def mock_results_repository():
    return Mock()


@pytest.fixture
def mock_time_provider():
    return Mock()


@pytest.fixture
def mock_job_repository():
    return Mock()


@pytest.fixture
def sample_job():
    from epistemix_platform.models.job import Job

    return Job(
        id=123,
        user_id=100,
        tags=["simulation_job"],
        created_at=datetime(2025, 1, 1, 10, 0, 0),
    )


@pytest.fixture
def completed_run():
    return Run(
        id=1,
        job_id=123,
        user_id=100,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 30, 0),
        request={"some": "config"},
        status=RunStatus.RUNNING,
        config_url="https://example.com/config.json",
    )


@pytest.fixture
def results_dir(tmp_path):
    results_path = tmp_path / "RUN4"
    results_path.mkdir()

    (results_path / "out1.txt").write_text("Day 1 results")
    (results_path / "out2.txt").write_text("Day 2 results")
    (results_path / "metrics.csv").write_text("metric,value\ninfected,100")

    return results_path


class TestUploadResults:
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
        mock_run_repository.find_by_id.assert_called_once_with(1)
        mock_results_packager.package_directory.assert_called_once_with(results_dir)

        mock_results_repository.upload_results.assert_called_once()
        call_args = mock_results_repository.upload_results.call_args
        assert call_args.kwargs["job_id"] == 123
        assert call_args.kwargs["run_id"] == 1
        assert call_args.kwargs["zip_content"] == b"fake zip content"

        mock_time_provider.now_utc.assert_called_once()

        assert (
            completed_run.results_url
            == "https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        )
        assert completed_run.results_uploaded_at == fixed_time
        assert completed_run.status == RunStatus.DONE
        mock_run_repository.save.assert_called_once_with(completed_run)

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

        assert (
            exc_info.value.orphaned_s3_url
            == "https://epistemix-uploads-staging.s3.amazonaws.com/results/job_123/run_1.zip"
        )

        mock_results_repository.upload_results.assert_called_once()
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
        mock_results_repository.upload_results.assert_called_once()

        call_args = mock_results_repository.upload_results.call_args
        assert "zip_content" in call_args.kwargs
        assert call_args.kwargs["zip_content"] == b"packaged content"

        assert call_args.kwargs["job_id"] == 123
        assert call_args.kwargs["run_id"] == 1

        mock_results_packager.package_directory.assert_called_once_with(results_dir)


class TestUploadResultsWithJobS3Prefix:
    @pytest.fixture
    def mock_job_repository(self):
        return MagicMock()

    @pytest.fixture
    def sample_job(self):
        from datetime import datetime

        from epistemix_platform.models.job import Job

        return Job(
            id=12,
            user_id=1,
            tags=["simulation_job"],
            created_at=datetime(2025, 10, 23, 21, 15, 0),
        )

    @pytest.fixture
    def sample_run(self, sample_job):
        from datetime import datetime

        from epistemix_platform.models.run import Run, RunStatus

        return Run(
            id=4,
            job_id=sample_job.id,
            user_id=sample_job.user_id,
            status=RunStatus.RUNNING,
            created_at=datetime(2025, 10, 23, 21, 16, 30),
            updated_at=datetime(2025, 10, 23, 21, 16, 30),
            request={"some": "data"},
        )

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

        upload_results(
            run_repository=mock_run_repository,
            job_repository=mock_job_repository,  # NEW parameter
            results_packager=mock_results_packager,
            results_repository=mock_results_repository,
            time_provider=mock_time_provider,
            job_id=12,
            run_id=4,
            results_dir=results_dir,
        )

        # Assert
        mock_job_repository.find_by_id.assert_called_once_with(12)

        mock_results_repository.upload_results.assert_called_once()
        call_kwargs = mock_results_repository.upload_results.call_args.kwargs

        assert "s3_prefix" in call_kwargs
        prefix = call_kwargs["s3_prefix"]
        assert isinstance(prefix, JobS3Prefix)
        assert prefix.job_id == 12
        assert prefix.timestamp == datetime(2025, 10, 23, 21, 15, 0)

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
        # Arrange
        from datetime import datetime

        from epistemix_platform.models.run import Run, RunStatus
        from epistemix_platform.models.upload_location import UploadLocation
        from epistemix_platform.services import PackagedResults
        from epistemix_platform.use_cases.upload_results import upload_results

        run_4 = Run(
            id=4,
            job_id=12,
            user_id=1,
            status=RunStatus.RUNNING,
            created_at=datetime(2025, 10, 23, 21, 16, 0),
            updated_at=datetime(2025, 10, 23, 21, 16, 0),
            request={"some": "data"},
        )
        run_5 = Run(
            id=5,
            job_id=12,
            user_id=1,
            status=RunStatus.RUNNING,
            created_at=datetime(2025, 10, 23, 21, 17, 0),
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

        # Act
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

        # Assert
        assert mock_results_repository.upload_results.call_count == 2

        calls = mock_results_repository.upload_results.call_args_list
        prefix_4 = calls[0].kwargs["s3_prefix"]
        prefix_5 = calls[1].kwargs["s3_prefix"]

        assert prefix_4.timestamp == datetime(2025, 10, 23, 21, 15, 0)
        assert prefix_5.timestamp == datetime(2025, 10, 23, 21, 15, 0)

        assert prefix_4.base_prefix == "jobs/12/2025/10/23/211500"
        assert prefix_5.base_prefix == "jobs/12/2025/10/23/211500"
