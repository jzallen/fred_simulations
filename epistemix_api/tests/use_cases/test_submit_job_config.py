from unittest.mock import Mock

from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.repositories.interfaces import IUploadLocationRepository
from epistemix_api.use_cases.submit_job_config import submit_job_config


class TestSubmitJobConfigUseCase:
    
    def test_submit_job_config__returns_job_config_location(self):
        # Arrange
        job_id = 1
        context = "job"
        job_type = "config"
        expected_url = "https://example-bucket.s3.amazonaws.com/job_1_job_config?X-Amz-Algorithm=..."
        
        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url=expected_url
        )
        
        # Act
        result = submit_job_config(mock_upload_location_repo, job_id, context, job_type)
        
        # Assert
        assert isinstance(result, UploadLocation)
        assert result.url == expected_url
        mock_upload_location_repo.get_upload_location.assert_called_once_with("job_1_job_config")
    
    def test_submit_job_config__uses_correct_resource_name(self):
        # Arrange
        job_id = 123
        context = "custom"
        job_type = "special"
        
        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )
        
        # Act
        submit_job_config(mock_upload_location_repo, job_id, context, job_type)
        
        # Assert
        mock_upload_location_repo.get_upload_location.assert_called_once_with("job_123_custom_special")
    
    def test_submit_job_config__uses_default_values(self):
        # Arrange
        job_id = 456
        
        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )
        
        # Act
        submit_job_config(mock_upload_location_repo, job_id)
        
        # Assert
        mock_upload_location_repo.get_upload_location.assert_called_once_with("job_456_job_config")