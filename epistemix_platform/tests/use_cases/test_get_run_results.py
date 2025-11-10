from datetime import datetime
from unittest.mock import Mock

import pytest

from epistemix_platform.models.job import Job
from epistemix_platform.models.run import Run, RunStatus
from epistemix_platform.models.run_results import RunResults
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.use_cases.get_run_results import get_run_results


class TestGetRunResults:
    def test_returns_run_results_for_all_runs(self):
        # Arrange
        job = Job(
            id=100,
            user_id=123,
            tags=["test"],
            created_at=datetime(2025, 11, 8, 20, 56, 47),
        )
        runs = [
            Run(
                id=1,
                job_id=100,
                user_id=123,
                status=RunStatus.DONE,
                created_at=datetime(2025, 11, 8, 20, 56, 48),
                updated_at=datetime(2025, 11, 8, 20, 56, 48),
                request={"test": "data"},
            ),
            Run(
                id=2,
                job_id=100,
                user_id=123,
                status=RunStatus.DONE,
                created_at=datetime(2025, 11, 8, 20, 56, 49),
                updated_at=datetime(2025, 11, 8, 20, 56, 49),
                request={"test": "data"},
            ),
        ]

        mock_job_repo = Mock()
        mock_job_repo.find_by_id.return_value = job

        mock_run_repo = Mock()
        mock_run_repo.find_by_job_id.return_value = runs

        mock_results_repo = Mock()
        mock_results_repo.get_download_url.return_value = UploadLocation(
            url="https://presigned-url.s3.amazonaws.com?X-Amz-Expires=86400"
        )

        # Act
        results = get_run_results(
            job_id=100,
            job_repository=mock_job_repo,
            run_repository=mock_run_repo,
            results_repository=mock_results_repo,
            bucket_name="test-bucket",
        )

        # Assert
        assert len(results) == 2
        assert all(isinstance(r, RunResults) for r in results)
        assert results[0].run_id == 1
        assert results[1].run_id == 2
        assert results[0].url == "https://presigned-url.s3.amazonaws.com?X-Amz-Expires=86400"

    def test_calls_repository_with_reconstructed_s3_urls(self):
        # Arrange
        job = Job(
            id=100,
            user_id=123,
            tags=["test"],
            created_at=datetime(2025, 11, 8, 20, 56, 47),
        )
        runs = [
            Run(
                id=1,
                job_id=100,
                user_id=123,
                status=RunStatus.DONE,
                created_at=datetime(2025, 11, 8, 20, 56, 48),
                updated_at=datetime(2025, 11, 8, 20, 56, 48),
                request={"test": "data"},
            ),
        ]

        mock_job_repo = Mock()
        mock_job_repo.find_by_id.return_value = job

        mock_run_repo = Mock()
        mock_run_repo.find_by_job_id.return_value = runs

        mock_results_repo = Mock()
        mock_results_repo.get_download_url.return_value = UploadLocation(
            url="https://presigned-url.com"
        )

        # Act
        get_run_results(
            job_id=100,
            job_repository=mock_job_repo,
            run_repository=mock_run_repo,
            results_repository=mock_results_repo,
            bucket_name="test-bucket",
        )

        # Assert
        expected_url = (
            "https://test-bucket.s3.amazonaws.com/jobs/100/2025/11/08/205647/run_1_results.zip"
        )
        mock_results_repo.get_download_url.assert_called_once_with(
            results_url=expected_url,
            expiration_seconds=86400,
        )

    def test_returns_empty_list_for_job_with_no_runs(self):
        # Arrange
        job = Job(
            id=100,
            user_id=123,
            tags=["test"],
            created_at=datetime(2025, 11, 8, 20, 56, 47),
        )

        mock_job_repo = Mock()
        mock_job_repo.find_by_id.return_value = job

        mock_run_repo = Mock()
        mock_run_repo.find_by_job_id.return_value = []

        mock_results_repo = Mock()

        # Act
        results = get_run_results(
            job_id=100,
            job_repository=mock_job_repo,
            run_repository=mock_run_repo,
            results_repository=mock_results_repo,
            bucket_name="test-bucket",
        )

        # Assert
        assert results == []
        mock_results_repo.get_download_url.assert_not_called()

    def test_uses_24_hour_expiration_by_default(self):
        # Arrange
        job = Job(
            id=100,
            user_id=123,
            tags=["test"],
            created_at=datetime(2025, 11, 8, 20, 56, 47),
        )
        runs = [
            Run(
                id=1,
                job_id=100,
                user_id=123,
                status=RunStatus.DONE,
                created_at=datetime(2025, 11, 8, 20, 56, 48),
                updated_at=datetime(2025, 11, 8, 20, 56, 48),
                request={"test": "data"},
            ),
        ]

        mock_job_repo = Mock()
        mock_job_repo.find_by_id.return_value = job

        mock_run_repo = Mock()
        mock_run_repo.find_by_job_id.return_value = runs

        mock_results_repo = Mock()
        mock_results_repo.get_download_url.return_value = UploadLocation(
            url="https://presigned-url.com"
        )

        # Act
        get_run_results(
            job_id=100,
            job_repository=mock_job_repo,
            run_repository=mock_run_repo,
            results_repository=mock_results_repo,
            bucket_name="test-bucket",
        )

        # Assert
        call_args = mock_results_repo.get_download_url.call_args
        assert call_args[1]["expiration_seconds"] == 86400

    def test_respects_custom_expiration_seconds(self):
        # Arrange
        job = Job(
            id=100,
            user_id=123,
            tags=["test"],
            created_at=datetime(2025, 11, 8, 20, 56, 47),
        )
        runs = [
            Run(
                id=1,
                job_id=100,
                user_id=123,
                status=RunStatus.DONE,
                created_at=datetime(2025, 11, 8, 20, 56, 48),
                updated_at=datetime(2025, 11, 8, 20, 56, 48),
                request={"test": "data"},
            ),
        ]

        mock_job_repo = Mock()
        mock_job_repo.find_by_id.return_value = job

        mock_run_repo = Mock()
        mock_run_repo.find_by_job_id.return_value = runs

        mock_results_repo = Mock()
        mock_results_repo.get_download_url.return_value = UploadLocation(
            url="https://presigned-url.com"
        )

        # Act
        get_run_results(
            job_id=100,
            job_repository=mock_job_repo,
            run_repository=mock_run_repo,
            results_repository=mock_results_repo,
            bucket_name="test-bucket",
            expiration_seconds=3600,
        )

        # Assert
        call_args = mock_results_repo.get_download_url.call_args
        assert call_args[1]["expiration_seconds"] == 3600

    def test_raises_value_error_when_job_not_found(self):
        # Arrange
        mock_job_repo = Mock()
        mock_job_repo.find_by_id.return_value = None

        mock_run_repo = Mock()
        mock_results_repo = Mock()

        # Act & Assert
        with pytest.raises(ValueError, match="Job 999 not found"):
            get_run_results(
                job_id=999,
                job_repository=mock_job_repo,
                run_repository=mock_run_repo,
                results_repository=mock_results_repo,
                bucket_name="test-bucket",
            )
