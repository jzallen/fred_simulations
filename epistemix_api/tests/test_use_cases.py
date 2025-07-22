"""
Tests for job use cases.
"""

import pytest
from unittest.mock import Mock, MagicMock

from epistemix_api.models.job import Job, JobStatus, JobTag
from epistemix_api.repositories.interfaces import IJobRepository
from epistemix_api.use_cases.job_use_cases import register_job, validate_tags


class TestRegisterJobUseCase:
    """Test the register_job use case."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository for testing."""
        repo = Mock(spec=IJobRepository)
        
        # Default ID counter
        repo._next_id = 100
        
        def mock_save(job):
            """Mock save that assigns ID to unpersisted jobs like the real repository."""
            if not job.is_persisted():
                job.id = repo._next_id
                repo._next_id += 1
            return job
        
        repo.save.side_effect = mock_save
        return repo
    
    def test_register_job_success(self, mock_repository):
        """Test successful job registration."""
        # Arrange
        user_id = 456
        tags = ["info_job"]
        
        # Act
        result = register_job(mock_repository, user_id, tags)
        
        # Assert
        assert isinstance(result, Job)
        assert result.id == 100
        assert result.user_id == 456
        assert result.tags == ["info_job"]
        assert result.status == JobStatus.CREATED
        
        # Verify repository interactions
        mock_repository.save.assert_called_once()
        
        # Verify the job passed to save method
        saved_job = mock_repository.save.call_args[0][0]
        assert saved_job.user_id == 456
        assert saved_job.tags == ["info_job"]
        # Note: The job will have been modified by the mock save to have id=100
    
    def test_register_job_with_no_tags(self, mock_repository):
        """Test job registration with no tags."""
        # Act
        result = register_job(mock_repository, 456, None)
        
        # Assert
        assert result.tags == []
        mock_repository.save.assert_called_once()
    
    def test_register_job_with_empty_tags_list(self, mock_repository):
        """Test job registration with empty tags list."""
        # Act
        result = register_job(mock_repository, 456, [])
        
        # Assert
        assert result.tags == []
        mock_repository.save.assert_called_once()
    
    def test_register_job_invalid_user_id_zero(self, mock_repository):
        """Test job registration with user ID of zero."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            register_job(mock_repository, 0, ["info_job"])
        
        # Repository should not be called
        mock_repository.save.assert_not_called()
    
    def test_register_job_invalid_user_id_negative(self, mock_repository):
        """Test job registration with negative user ID."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            register_job(mock_repository, -1, ["info_job"])
        
        # Repository should not be called
        mock_repository.save.assert_not_called()
    
    def test_register_job_invalid_tags(self, mock_repository):
        """Test job registration with invalid tags."""
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            register_job(mock_repository, 456, [""])
        
        # Repository should not be called for saving
        mock_repository.save.assert_not_called()
    
    def test_register_job_repository_id_generation(self, mock_repository):
        """Test that job registration uses repository for ID generation."""
        # Arrange - set up repository to return specific ID
        mock_repository._next_id = 999
        
        # Act
        result = register_job(mock_repository, 456, ["test"])
        
        # Assert
        assert result.id == 999
        mock_repository.save.assert_called_once()
    
    def test_register_job_repository_save_called(self, mock_repository):
        """Test that job registration calls repository save."""
        # Act
        register_job(mock_repository, 456, ["test"])
        
        # Assert
        mock_repository.save.assert_called_once()
        
        # Verify the job passed to save has correct properties
        saved_job = mock_repository.save.call_args[0][0]
        assert isinstance(saved_job, Job)
        assert saved_job.status == JobStatus.CREATED


class TestValidateTagsUseCase:
    """Test the validate_tags use case."""
    
    def test_validate_tags_valid_known_tags(self):
        """Test validation with known valid tags."""
        # These should not raise any exceptions
        validate_tags(["info_job"])
        validate_tags(["simulation_job", "analysis_job"])
        validate_tags([])  # Empty list should be valid
    
    def test_validate_tags_none_input(self):
        """Test validation with None input."""
        # Should not raise exception
        validate_tags(None)
    
    def test_validate_tags_empty_list(self):
        """Test validation with empty list."""
        # Should not raise exception
        validate_tags([])
    
    def test_validate_tags_unknown_tags_allowed(self):
        """Test that unknown tags are currently allowed."""
        # This should not raise an exception (current business rule)
        validate_tags(["unknown_tag", "custom_tag"])
    
    def test_validate_tags_empty_string(self):
        """Test validation with empty string tag."""
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([""])
    
    def test_validate_tags_whitespace_only(self):
        """Test validation with whitespace-only tag."""
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags(["   "])
    
    def test_validate_tags_non_string_type(self):
        """Test validation with non-string tag."""
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([123])
        
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([None])
        
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([["nested_list"]])
    
    def test_validate_tags_mixed_valid_invalid(self):
        """Test validation with mix of valid and invalid tags."""
        # Should fail on the first invalid tag
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags(["valid_tag", "", "another_valid_tag"])
    
    def test_validate_tags_business_rule_flexibility(self):
        """Test that validation follows current business rules."""
        # Current business rule: allow unknown tags
        # This test documents the current behavior
        try:
            validate_tags(["completely_unknown_tag", "another_unknown"])
            # If we reach here, unknown tags are allowed (current behavior)
        except ValueError:
            # If this raises ValueError, strict validation is enabled
            pytest.fail("Unknown tags should be allowed per current business rules")


class TestUseCaseIntegration:
    """Integration tests for use cases."""
    
    def test_register_job_end_to_end(self):
        """Test register_job use case end-to-end with real repository behavior."""
        from epistemix_api.repositories.job_repository import InMemoryJobRepository
        
        # Arrange
        repository = InMemoryJobRepository(starting_id=200)
        
        # Act
        job = register_job(repository, user_id=456, tags=["integration_test"])
        
        # Assert
        assert job.id == 200
        assert job.user_id == 456
        assert job.tags == ["integration_test"]
        assert job.status == JobStatus.CREATED
        
        # Verify job was actually saved in repository
        retrieved_job = repository.find_by_id(200)
        assert retrieved_job == job
        assert repository.count() == 1
    
    def test_multiple_job_registrations(self):
        """Test multiple job registrations use sequential IDs."""
        from epistemix_api.repositories.job_repository import InMemoryJobRepository
        
        # Arrange
        repository = InMemoryJobRepository(starting_id=300)
        
        # Act
        job1 = register_job(repository, user_id=456, tags=["job1"])
        job2 = register_job(repository, user_id=789, tags=["job2"])
        job3 = register_job(repository, user_id=456, tags=["job3"])
        
        # Assert
        assert job1.id == 300
        assert job2.id == 301
        assert job3.id == 302
        
        # Verify all jobs are in repository
        assert repository.count() == 3
        assert repository.find_by_user_id(456) == [job1, job3]
        assert repository.find_by_user_id(789) == [job2]
