from unittest.mock import Mock

from epistemix_api.models.upload_location import UploadLocation
<<<<<<< HEAD
from epistemix_api.models.run import Run
from epistemix_api.repositories.interfaces import IUploadLocationRepository, IRunRepository
=======
from epistemix_api.repositories.interfaces import IUploadLocationRepository
>>>>>>> origin/main
from epistemix_api.use_cases import submit_run_config


class TestSubmitRunConfigUseCase:
    
    def test_submit_run_config__returns_run_config_location(self):
        # Arrange
        job_id = 1
        run_id = 1
        context = "run"
        job_type = "config"
        expected_url = "https://example-bucket.s3.amazonaws.com/job_1_run_1_run_config?X-Amz-Algorithm=..."
        
<<<<<<< HEAD
        mock_run_repo = Mock(spec=IRunRepository)
        mock_run = Mock(spec=Run)
        mock_run_repo.find_by_id.return_value = mock_run
        
=======
>>>>>>> origin/main
        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url=expected_url
        )
        
        # Act
<<<<<<< HEAD
        result = submit_run_config(mock_run_repo, mock_upload_location_repo, job_id, context, job_type, run_id)
=======
        result = submit_run_config(mock_upload_location_repo, job_id, context, job_type, run_id)
>>>>>>> origin/main
        
        # Assert
        assert isinstance(result, UploadLocation)
        assert result.url == expected_url
        mock_upload_location_repo.get_upload_location.assert_called_once_with("job_1_run_1_run_config")
    
    def test_submit_run_config__uses_correct_resource_name_with_run_id(self):
        # Arrange
        job_id = 123
        run_id = 456
        context = "custom"
        job_type = "special"
        
<<<<<<< HEAD
        mock_run_repo = Mock(spec=IRunRepository)
        mock_run = Mock(spec=Run)
        mock_run_repo.find_by_id.return_value = mock_run
        
=======
>>>>>>> origin/main
        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )
        
        # Act
<<<<<<< HEAD
        submit_run_config(mock_run_repo, mock_upload_location_repo, job_id, context, job_type, run_id)
=======
        submit_run_config(mock_upload_location_repo, job_id, context, job_type, run_id)
>>>>>>> origin/main
        
        # Assert
        mock_upload_location_repo.get_upload_location.assert_called_once_with("job_123_run_456_custom_special")
    
    def test_submit_run_config__uses_correct_resource_name_without_run_id(self):
        # Arrange
        job_id = 789
        context = "run"
        job_type = "config"
        
<<<<<<< HEAD
        mock_run_repo = Mock(spec=IRunRepository)
        mock_run_repo.find_by_id.return_value = None
        
=======
>>>>>>> origin/main
        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )
        
        # Act
<<<<<<< HEAD
        submit_run_config(mock_run_repo, mock_upload_location_repo, job_id, context, job_type, run_id=None)
=======
        submit_run_config(mock_upload_location_repo, job_id, context, job_type, run_id=None)
>>>>>>> origin/main
        
        # Assert
        mock_upload_location_repo.get_upload_location.assert_called_once_with("job_789_run_config")
    
    def test_submit_run_config__uses_default_values(self):
        # Arrange
        job_id = 999
        
<<<<<<< HEAD
        mock_run_repo = Mock(spec=IRunRepository)
        mock_run_repo.find_by_id.return_value = None
        
=======
>>>>>>> origin/main
        mock_upload_location_repo = Mock(spec=IUploadLocationRepository)
        mock_upload_location_repo.get_upload_location.return_value = UploadLocation(
            url="https://example.com/presigned"
        )
        
        # Act
<<<<<<< HEAD
        submit_run_config(mock_run_repo, mock_upload_location_repo, job_id)
=======
        submit_run_config(mock_upload_location_repo, job_id)
>>>>>>> origin/main
        
        # Assert
        mock_upload_location_repo.get_upload_location.assert_called_once_with("job_999_run_config")