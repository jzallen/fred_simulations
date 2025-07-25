"""
Tests for register_job use case.
"""

import pytest
from unittest.mock import Mock
from freezegun import freeze_time

from epistemix_api.models.job import Job
from epistemix_api.repositories.interfaces import IJobRepository
from epistemix_api.use_cases.job_use_cases import register_job


@freeze_time("2025-01-01 12:00:00")
class TestRegisterJobUseCase:
    
    @pytest.fixture
    def mock_repository(self):
        repo = Mock(spec=IJobRepository)
        return repo
    
    def test_register_job__saves_created_job_to_repository(self, mock_repository):
        # Arrange
        user_id = 456
        tags = ["some_tag"]
        
        # Act
        register_job(mock_repository, user_id, tags)
        
        # Assert
        expected_job = Job.create_new(user_id=user_id, tags=tags)
        mock_repository.save.assert_called_once_with(expected_job)
    
    def test_register_job__when_job_with_no_tags__saves_created_job_to_repository(self, mock_repository):
        register_job(mock_repository, 456, None)
        expected_job = Job.create_new(user_id=456, tags=[])
        mock_repository.save.assert_called_once_with(expected_job)
    
    def test_register_job__when_invalid_user_id_zero__raises_value_error(self, mock_repository):
        with pytest.raises(ValueError, match="User ID must be positive"):
            register_job(mock_repository, 0, ["info_job"])
        
        # Repository should not be called
        mock_repository.save.assert_not_called()
    
    def test_register_job__when_invalid_user_id_negative__raises_value_error(self, mock_repository):
        with pytest.raises(ValueError, match="User ID must be positive"):
            register_job(mock_repository, -1, ["info_job"])
        
        # Repository should not be called
        mock_repository.save.assert_not_called()
    
    def test_register_job__when_empty_tags__raises_value_error(self, mock_repository):
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            register_job(mock_repository, 456, [""])
        
        # Repository should not be called for saving
        mock_repository.save.assert_not_called()
