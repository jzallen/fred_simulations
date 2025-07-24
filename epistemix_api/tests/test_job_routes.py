"""
Tests for the refactored Flask app using Clean Architecture.
"""

import pytest
import os

from epistemix_api.app import app
from epistemix_api.models.job import JobStatus
from epistemix_api.repositories.database import get_database_manager


@pytest.fixture
def client():
    """Create a test client for the Flask app with a fresh test database."""
    
    # Set up test database URL
    test_db_url = "sqlite:///test_job_routes.db"
    
    # Configure Flask app to use test database
    app.config['TESTING'] = True
    app.config['DATABASE_URL'] = test_db_url
    
    # Clear and recreate tables for each test
    test_db_manager = get_database_manager(test_db_url)
    test_db_manager.create_tables()
    
    with app.test_client() as client:
        yield client
    
    try:
        os.remove("test_job_routes.db")
    except FileNotFoundError:
        pass


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
            "id": 1,
            "userId": 456,
            "tags": ["info_job"],
            "status": JobStatus.CREATED.value,
            "createdAt": response.json['createdAt'],
            "updatedAt": response.json['updatedAt'],
            "metadata": {}
        }
        data = response.get_json()
        assert data == epxected_registered_job_data
    
    def test_job_submission__valid_request__returns_successful_response(self, client):
        # First register a job
        register_headers = {
            'Offline-Token': 'Bearer fake-token',
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        register_body = {"tags": ["info_job"]}
        register_response = client.post('/jobs/register', headers=register_headers, json=register_body)
        assert register_response.status_code == 200
        job_id = register_response.get_json()['id']
        
        # Now submit the registered job
        headers = {
            'Offline-Token': 'Bearer fake-token',
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
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
