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

from epistemix_api.app import app
from epistemix_api.services.job_service import JobService, JobRepository
from epistemix_api.models.job import Job, JobStatus


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def job_service():
    """Create a fresh job service for testing."""
    return JobService(JobRepository())


class TestCleanArchitectureJobRegistration:
    """Test job registration with Clean Architecture implementation."""
    
    def test_job_registration_creates_business_model(self, client):
        """Test that job registration creates proper business models."""
        headers = {
            'Offline-Token': 'Bearer fake-token',
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        body = {"tags": ["info_job"]}
        
        response = client.post('/jobs/register', 
                             headers=headers,
                             json=body)
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Validate response structure matches business model
        assert 'id' in data
        assert 'userId' in data
        assert 'tags' in data
        assert 'status' in data
        assert 'createdAt' in data
        assert 'updatedAt' in data
        
        # Validate business logic
        assert data['tags'] == ['info_job']
        assert data['status'] == 'registered'  # Should be REGISTERED status
        assert data['userId'] == 456
    
    def test_job_submission_uses_business_logic(self, client):
        """Test that job submission uses business logic and validation."""
        # First register a job
        headers = {
            'Offline-Token': 'Bearer fake-token',
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        reg_response = client.post('/jobs/register',
                                 headers=headers,
                                 json={"tags": ["info_job"]})
        
        assert reg_response.status_code == 200
        job_data = reg_response.get_json()
        job_id = job_data['id']
        
        # Now submit the job
        submit_body = {
            "jobId": job_id,
            "context": "job",
            "type": "input"
        }
        
        response = client.post('/jobs',
                             headers=headers,
                             json=submit_body)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'url' in data
        assert data['url'] == 'http://localhost:5001/pre-signed-url'
    
    def test_job_submission_validation(self, client):
        """Test that job submission validates business rules."""
        headers = {
            'Offline-Token': 'Bearer fake-token',
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        # Try to submit a non-existent job
        submit_body = {
            "jobId": 99999,  # Non-existent job
            "context": "job",
            "type": "input"
        }
        
        response = client.post('/jobs',
                             headers=headers,
                             json=submit_body)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_job_statistics_endpoint(self, client):
        """Test the new job statistics endpoint."""
        # Register a few jobs first
        headers = {
            'Offline-Token': 'Bearer fake-token',
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        # Register multiple jobs
        for i in range(3):
            client.post('/jobs/register',
                       headers=headers,
                       json={"tags": ["info_job"]})
        
        # Get statistics
        response = client.get('/jobs/statistics')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Validate statistics structure
        assert 'total_jobs' in data
        assert 'status_breakdown' in data
        assert 'tag_breakdown' in data
        assert 'active_jobs' in data
        
        # Validate business logic
        assert data['total_jobs'] >= 3
        assert 'registered' in data['status_breakdown']
        assert 'info_job' in data['tag_breakdown']


class TestJobService:
    """Test the job service business logic."""
    
    def test_job_service_register_job(self, job_service):
        """Test job service registration."""
        job = job_service.register_job(user_id=456, tags=["info_job"])
        
        assert isinstance(job, Job)
        assert job.user_id == 456
        assert job.tags == ["info_job"]
        assert job.status == JobStatus.REGISTERED
    
    def test_job_service_submit_job(self, job_service):
        """Test job service submission."""
        # First register a job
        job = job_service.register_job(user_id=456, tags=["info_job"])
        
        # Then submit it
        response = job_service.submit_job(job_id=job.id)
        
        assert isinstance(response, dict)
        assert 'url' in response
        
        # Verify job status changed
        updated_job = job_service.get_job(job.id)
        assert updated_job.status == JobStatus.SUBMITTED
    
    def test_job_service_validation(self, job_service):
        """Test job service validation."""
        # Test invalid user ID
        with pytest.raises(ValueError, match="User ID must be positive"):
            job_service.register_job(user_id=0)
        
        # Test submitting non-existent job
        with pytest.raises(ValueError, match="not found"):
            job_service.submit_job(job_id=99999)
    
    def test_job_service_statistics(self, job_service):
        """Test job service statistics."""
        # Register some jobs
        job_service.register_job(user_id=456, tags=["info_job"])
        job_service.register_job(user_id=456, tags=["test_job"])
        
        stats = job_service.get_job_statistics()
        
        assert isinstance(stats, dict)
        assert stats['total_jobs'] == 2
        assert stats['status_breakdown']['registered'] == 2
        assert stats['tag_breakdown']['info_job'] == 1
        assert stats['tag_breakdown']['test_job'] == 1
