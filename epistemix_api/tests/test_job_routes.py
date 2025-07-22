"""
Tests for the refactored Flask app using Clean Architecture.
"""

import pytest

from epistemix_api.app import app
from epistemix_api.services.job_service import JobService
from epistemix_api.repositories.job_repository import InMemoryJobRepository
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
    return JobService(InMemoryJobRepository())


class TestJobRoutes:
    
    def test_job_registration_creates_business_model(self, client):
        """Test that job registration creates proper business models."""
        headers = {
            'Offline-Token': 'Bearer fake-token',
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        body = {"tags": ["info_job"]}
        
        response = client.post('/jobs/register', headers=headers, json=body)
        assert response.status_code == 200
        
        epxected_registered_job_data = {
            "id": 123,
            "userId": 456,  # Mock user ID as per Pact contract
            "tags": ["info_job"],
            "status": JobStatus.CREATED.value,
            "createdAt": response.json['createdAt'],
            "updatedAt": response.json['updatedAt'],
            "metadata": {}
        }
        data = response.get_json()
        assert data == epxected_registered_job_data
    
    def test_job_submission__valid_request__returns_successful_response(self, client):
        headers = {
            'Offline-Token': 'Bearer fake-token',
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        submit_body = {
            "jobId": 123,
            "context": "job",
            "type": "input"
        }
        
        response = client.post('/jobs',
                             headers=headers,
                             json=submit_body)
        
        assert response.status_code == 200
        data = response.get_json()
        expected_job_submission_data = {
            "url": "http://localhost:5001/pre-signed-url",
        }
        assert data == expected_job_submission_data
    
    def test_job_submission__invalid_job_id__returns_error_response(self, client):
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
        expected_error_data = {
            "error": "Job 99999 not found",
        }
        assert data == expected_error_data
