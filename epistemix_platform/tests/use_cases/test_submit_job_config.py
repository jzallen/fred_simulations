from unittest.mock import Mock

from epistemix_platform.models.job import Job
from epistemix_platform.models.job_s3_prefix import JobS3Prefix
from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories.interfaces import IJobRepository, IUploadLocationRepository
from epistemix_platform.use_cases.submit_job_config import submit_job_config


class TestSubmitJobConfigUseCase:
    def test_submit_job_config__returns_job_config_location(self):
        job_id = 1
        context = "job"
        job_type = "config"
        expected_url = (
            "https://example-bucket.s3.amazonaws.com/job_1_job_config?X-Amz-Algorithm=..."
        )

        mock_job = Job.create_persisted(job_id=job_id, user_id=1)
        mock_job_repo = Mock(spec=IJobRepository)
        mock_job_repo.find_by_id.return_value = mock_job

        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url=expected_url
        )

        job_upload = JobUpload(context=context, upload_type=job_type, job_id=job_id)
        result = submit_job_config(mock_job_repo, mock_upload_location_repo, job_upload)

        assert isinstance(result, UploadLocation)
        assert result.url == expected_url
        assert mock_job.config_location == expected_url
        mock_upload_location_repo.get_upload_location.assert_called_once()
        call_args = mock_upload_location_repo.get_upload_location.call_args
        assert call_args[0][0] == job_upload
        assert isinstance(call_args[0][1], JobS3Prefix)
        assert call_args[0][1].job_id == job_id
        mock_job_repo.save.assert_called_once_with(mock_job)

    def test_submit_job_config__uses_correct_resource_name(self):
        job_id = 123
        context = "job"
        job_type = "config"

        mock_job = Job.create_persisted(job_id=job_id, user_id=1)
        mock_job_repo = Mock(spec=IJobRepository)
        mock_job_repo.find_by_id.return_value = mock_job

        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )

        job_upload = JobUpload(context=context, upload_type=job_type, job_id=job_id)
        submit_job_config(mock_job_repo, mock_upload_location_repo, job_upload)

        mock_upload_location_repo.get_upload_location.assert_called_once()
        call_args = mock_upload_location_repo.get_upload_location.call_args
        assert call_args[0][0] == job_upload
        assert isinstance(call_args[0][1], JobS3Prefix)

    def test_submit_job_config__uses_default_values(self):
        job_id = 456

        mock_job = Job.create_persisted(job_id=job_id, user_id=1)
        mock_job_repo = Mock(spec=IJobRepository)
        mock_job_repo.find_by_id.return_value = mock_job

        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )

        job_upload = JobUpload(context="job", upload_type="config", job_id=job_id)
        submit_job_config(mock_job_repo, mock_upload_location_repo, job_upload)

        mock_upload_location_repo.get_upload_location.assert_called_once()
        call_args = mock_upload_location_repo.get_upload_location.call_args
        assert call_args[0][0] == job_upload
        assert isinstance(call_args[0][1], JobS3Prefix)
