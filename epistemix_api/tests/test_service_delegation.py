"""
Tests for the service layer delegation to use cases.
"""

import pytest
from unittest.mock import Mock, patch

from epistemix_api.services.job_service import JobService
from epistemix_api.repositories.job_repository import InMemoryJobRepository
from epistemix_api.models.job import Job, JobStatus


class TestJobServiceDelegation:
    """Test that JobService properly delegates to use cases."""
    
    @pytest.fixture
    def repository(self):
        """Create a repository for testing."""
        return InMemoryJobRepository(starting_id=400)
    
    @pytest.fixture
    def service(self, repository):
        """Create a service with repository."""
        return JobService(repository)
    
    @patch('epistemix_api.services.job_service.register_job_use_case')
    def test_register_job_delegates_to_use_case(self, mock_use_case, service):
        """Test that JobService.register_job delegates to the use case."""
        # Arrange
        expected_job = Job.create_persisted(job_id=400, user_id=456, tags=["test"])
        mock_use_case.return_value = expected_job
        
        # Act
        result = service.register_job(user_id=456, tags=["test"])
        
        # Assert
        assert result == expected_job
        mock_use_case.assert_called_once_with(
            job_repository=service._job_repository,
            user_id=456,
            tags=["test"]
        )
    
    @patch('epistemix_api.services.job_service.register_job_use_case')
    def test_register_job_passes_repository_correctly(self, mock_use_case, service):
        """Test that the service passes its repository to the use case."""
        # Arrange
        mock_use_case.return_value = Job.create_persisted(job_id=400, user_id=456, tags=[])
        
        # Act
        service.register_job(user_id=456, tags=["test"])
        
        # Assert
        # Verify the repository passed to use case is the service's repository
        call_args = mock_use_case.call_args
        assert call_args[1]['job_repository'] is service._job_repository
    
    @patch('epistemix_api.services.job_service.register_job_use_case')
    def test_register_job_handles_use_case_exceptions(self, mock_use_case, service):
        """Test that service properly propagates use case exceptions."""
        # Arrange
        mock_use_case.side_effect = ValueError("Invalid user ID")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid user ID"):
            service.register_job(user_id=0, tags=["test"])
    
    @patch('epistemix_api.services.job_service.validate_tags')
    def test_add_tag_to_job_uses_use_case_validation(self, mock_validate, service):
        """Test that add_tag_to_job uses the use case validation."""
        # Arrange - first register a job
        job = service.register_job(user_id=456, tags=["initial"])
        
        # Act
        service.add_tag_to_job(job.id, "new_tag")
        
        # Assert
        mock_validate.assert_called_once_with(["new_tag"])
    
    def test_service_layer_orchestration(self, service):
        """Test that service layer properly orchestrates use cases."""
        # This test verifies the service works end-to-end
        # without mocking, showing proper orchestration
        
        # Act
        job = service.register_job(user_id=456, tags=["orchestration_test"])
        
        # Assert
        assert isinstance(job, Job)
        assert job.user_id == 456
        assert job.tags == ["orchestration_test"]
        assert job.status == JobStatus.CREATED
        
        # Verify the job is accessible through service
        retrieved_job = service.get_job(job.id)
        assert retrieved_job == job
    
    def test_service_maintains_business_interface(self, service):
        """Test that service maintains the same business interface."""
        # This ensures refactoring didn't break the public API
        
        # Test all public methods still work
        job = service.register_job(user_id=456, tags=["interface_test"])
        assert job is not None
        
        submission_response = service.submit_job(job.id)
        assert "url" in submission_response
        
        updated_job = service.get_job(job.id)
        assert updated_job.status == JobStatus.SUBMITTED
        
        user_jobs = service.get_jobs_for_user(456)
        assert len(user_jobs) == 1
        assert user_jobs[0] == job
        
        stats = service.get_job_statistics()
        assert stats["total_jobs"] >= 1


class TestServiceLayerBehavior:
    """Test service layer behavior and responsibilities."""
    
    def test_service_is_stateless(self):
        """Test that service doesn't maintain state beyond repository."""
        repo = InMemoryJobRepository()
        service1 = JobService(repo)
        service2 = JobService(repo)
        
        # Register job with service1
        job = service1.register_job(user_id=456, tags=["stateless_test"])
        
        # Should be accessible through service2 (same repository)
        retrieved_job = service2.get_job(job.id)
        assert retrieved_job == job
    
    def test_service_dependency_injection(self):
        """Test that service properly uses injected dependencies."""
        repo1 = InMemoryJobRepository(starting_id=500)
        repo2 = InMemoryJobRepository(starting_id=600)
        
        service1 = JobService(repo1)
        service2 = JobService(repo2)
        
        # Jobs should have different IDs based on repository
        job1 = service1.register_job(user_id=456, tags=["di_test1"])
        job2 = service2.register_job(user_id=456, tags=["di_test2"])
        
        assert job1.id == 500
        assert job2.id == 600
        
        # Jobs should be in different repositories
        assert service1.get_job(job1.id) == job1
        assert service1.get_job(job2.id) is None
        assert service2.get_job(job2.id) == job2
        assert service2.get_job(job1.id) is None
    
    def test_service_error_handling(self):
        """Test service error handling and validation."""
        service = JobService(InMemoryJobRepository())
        
        # Test various error conditions
        with pytest.raises(ValueError):
            service.submit_job(99999)  # Non-existent job
        
        with pytest.raises(ValueError):
            service.update_job_status(99999, JobStatus.COMPLETED)  # Non-existent job
        
        with pytest.raises(ValueError):
            service.add_tag_to_job(99999, "test")  # Non-existent job
