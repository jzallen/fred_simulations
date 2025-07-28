"""
Tests for the refactored Flask app using Clean Architecture.
"""

import pytest
import os
import json
import base64

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


@pytest.fixture
def bearer_token():
    token_data = {"user_id": 123, "scopes_hash": "abc123"}
    token_json = json.dumps(token_data)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    return f"Bearer {token_b64}"


class TestJobRoutes:
    
    def test_job_registration_creates_business_model(self, client, bearer_token):
        """Test that job registration creates proper business models."""
        headers = {
            'Offline-Token': bearer_token,
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        body = {"tags": ["info_job"]}
        
        response = client.post('/jobs/register', headers=headers, json=body)
        assert response.status_code == 200
        
        expected_registered_job_data = {
            "id": 1,
            "userId": 123,
            "tags": ["info_job"],
        }
        data = response.get_json()
        assert data == expected_registered_job_data

    def test_job_submission__valid_request__returns_successful_response(self, client, bearer_token):
        # First register a job
        register_headers = {
            'Offline-Token': bearer_token,
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }

        register_body = {"tags": ["info_job"] }
        client.post('/jobs/register', headers=register_headers, json=register_body)
        
        # Now submit the registered job
        headers = {
            'Offline-Token': bearer_token,
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        submit_body = {
            "jobId": 1,
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

    def test_run_submission__valid_request__returns_successful_response(self, client, bearer_token):
        """Test submitting multiple runs."""
        headers = {
            'Offline-Token': bearer_token,
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        run_requests = {
          "runRequests": [
            {
              "jobId": 123,
              "workingDir": "/workspaces/fred_simulations",
              "size": "hot",
              "fredVersion": "latest",
              "population": {
                "version": "US_2010.v5",
                "locations": [
                  "Loving_County_TX"
                ]
              },
              "fredArgs": [
                {
                  "flag": "-p",
                  "value": "main.fred"
                }
              ],
              "fredFiles": [
                "/workspaces/fred_simulations/simulations/agent_info_demo/agent_info.fred"
              ]
            }
          ]
        }
        
        response = client.post('/runs', headers=headers, json=run_requests)
        
        assert response.status_code == 200
        expected_response = {
          "runResponses": [
            {
              "runId": 1,
              "jobId": 123,
              "status": "Submitted",
              "errors": None,
              "runRequest": {
                "jobId": 123,
                "workingDir": "/workspaces/fred_simulations",
                "size": "hot",
                "fredVersion": "latest",
                "population": {
                  "version": "US_2010.v5",
                  "locations": [
                    "Loving_County_TX"
                  ]
                },
                "fredArgs": [
                  {
                    "flag": "-p",
                    "value": "main.fred"
                  }
                ],
                "fredFiles": [
                  "/workspaces/fred_simulations/simulations/agent_info_demo/agent_info.fred"
                ]
              }
            }
          ]
        }
        data = response.get_json()
        assert data == expected_response
        