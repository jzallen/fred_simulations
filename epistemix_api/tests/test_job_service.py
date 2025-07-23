"""
Tests for the refactored Flask app using Clean Architecture.
"""

import json
import pytest
import sys
from pathlib import Path

# Add the epistemix_api directory to the Python path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from epistemix_api.services.job_service import JobService
from epistemix_api.repositories.job_repository import InMemoryJobRepository
from epistemix_api.models.job import Job, JobStatus


@pytest.fixture
def service():
    """Create a service instance for testing."""
    return JobService.create_with_job_repository(InMemoryJobRepository())

class TestJobService:
    """Test the job service business logic."""
    
    def test_register_job__given_valid_user_id_and_tags__returns_job_with_id(self, service):
        """Test JobService register_job method."""
        expected_job = Job(id=123, user_id=456, tags=["info_job"], status=JobStatus.CREATED)
        job = service.register_job(user_id=456, tags=["info_job"])
        assert job == expected_job

    
    def test_job_service_submit_job(self, service):
        expected_job_config_response = {
            "url": "http://localhost:5001/pre-signed-url",
        }        
        
        # Job must be persisted to submit
        job = service.register_job(user_id=456, tags=["info_job"])        
        job_config_response = service.submit_job(job_id=job.id)
        assert job_config_response == expected_job_config_response

    
    def test_job_service_validation(self, service):
        """Test job service validation."""
        # Test invalid user ID
        with pytest.raises(ValueError, match="User ID must be positive"):
            service.register_job(user_id=0)
        
        # Test submitting non-existent job
        with pytest.raises(ValueError, match="not found"):
            service.submit_job(job_id=99999)
    
    def test_job_service_statistics(self, service):
        """Test job service statistics."""
        # Register some jobs
        service.register_job(user_id=456, tags=["info_job"])
        service.register_job(user_id=456, tags=["test_job"])
        
        stats = service.get_job_statistics()
        
        assert isinstance(stats, dict)
        assert stats['total_jobs'] == 2
        assert stats['status_breakdown']['created'] == 2
        assert stats['tag_breakdown']['info_job'] == 1
        assert stats['tag_breakdown']['test_job'] == 1
