from unittest.mock import Mock

import pytest

from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.run import Run
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories.interfaces import IRunRepository, IUploadLocationRepository
from epistemix_platform.use_cases import submit_run_config


class TestSubmitRunConfigUseCase:
    def test_submit_run_config__returns_run_config_location(self):
        # Arrange
        job_id = 1
        run_id = 1
        context = "run"
        job_type = "config"
        expected_url = (
            "https://example-bucket.s3.amazonaws.com/job_1_run_1_run_config?X-Amz-Algorithm=..."
        )

        mock_run_repo = Mock(spec=IRunRepository)
        mock_run = Mock(spec=Run)
        mock_run_repo.find_by_id.return_value = mock_run

        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url=expected_url
        )

        # Act
        job_upload = JobUpload(context=context, upload_type=job_type, job_id=job_id, run_id=run_id)
        result = submit_run_config(mock_run_repo, mock_upload_location_repo, job_upload)

        # Assert
        assert isinstance(result, UploadLocation)
        assert result.url == expected_url
        mock_upload_location_repo.get_upload_location.assert_called_once_with(job_upload)

    def test_submit_run_config__uses_correct_resource_name_with_run_id(self):
        # Arrange
        job_id = 123
        run_id = 456
        context = "run"  # Valid context for run config
        job_type = "config"  # Valid type for run context

        mock_run_repo = Mock(spec=IRunRepository)
        mock_run = Mock(spec=Run)
        mock_run_repo.find_by_id.return_value = mock_run

        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )

        # Act
        job_upload = JobUpload(context=context, upload_type=job_type, job_id=job_id, run_id=run_id)
        submit_run_config(mock_run_repo, mock_upload_location_repo, job_upload)

        # Assert
        mock_upload_location_repo.get_upload_location.assert_called_once_with(job_upload)

    def test_submit_run_config__uses_correct_resource_name_without_run_id(self):
        # Arrange
        job_id = 789
        context = "run"
        job_type = "config"

        mock_run_repo = Mock(spec=IRunRepository)
        mock_run_repo.find_by_id.return_value = None

        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )

        # Act
        job_upload = JobUpload(context=context, upload_type=job_type, job_id=job_id, run_id=None)
        submit_run_config(mock_run_repo, mock_upload_location_repo, job_upload)

        # Assert
        mock_upload_location_repo.get_upload_location.assert_called_once_with(job_upload)

    def test_submit_run_config__uses_default_values(self):
        # Arrange
        job_id = 999

        mock_run_repo = Mock(spec=IRunRepository)
        mock_run_repo.find_by_id.return_value = None

        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )

        # Act
        job_upload = JobUpload(context="run", upload_type="config", job_id=job_id)
        submit_run_config(mock_run_repo, mock_upload_location_repo, job_upload)

        # Assert
        mock_upload_location_repo.get_upload_location.assert_called_once_with(job_upload)

    def test_submit_run_config__raises_error_when_run_not_found(self):
        # Arrange
        job_id = 123
        run_id = 456
        context = "run"
        job_type = "config"

        mock_run_repo = Mock(spec=IRunRepository)
        mock_run_repo.find_by_id.return_value = None  # Run not found

        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )

        # Act & Assert
        job_upload = JobUpload(context=context, upload_type=job_type, job_id=job_id, run_id=run_id)
        with pytest.raises(ValueError) as exc_info:
            submit_run_config(mock_run_repo, mock_upload_location_repo, job_upload)

        assert str(exc_info.value) == f"Run {run_id} not found"
        mock_run_repo.find_by_id.assert_called_once_with(run_id)
