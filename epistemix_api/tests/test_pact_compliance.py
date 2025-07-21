"""
Tests for the Epistemix API Flask app to validate Pact contract compliance.
"""

import json
import pytest
import sys
from pathlib import Path

# Add the epistemix_api directory to the Python path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from epistemix_api.app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def pact_contract():
    """Load the Pact contract for reference."""
    pact_file = Path(__file__).parent.parent / 'pacts' / 'epx-epistemix.json'
    with open(pact_file, 'r') as f:
        return json.load(f)


class TestJobRegistration:
    """Test job registration endpoint."""
    
    def test_job_registration_success(self, client, pact_contract):
        """Test successful job registration matching Pact contract."""
        # Get the job registration interaction from Pact
        job_reg_interaction = None
        for interaction in pact_contract['interactions']:
            if interaction['description'] == 'a job registration request':
                job_reg_interaction = interaction
                break
        
        assert job_reg_interaction is not None
        
        # Make request matching Pact contract
        headers = job_reg_interaction['request']['headers']
        body = job_reg_interaction['request']['body']
        
        response = client.post('/jobs/register', 
                             headers=headers,
                             json=body)
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Validate response structure matches Pact contract
        expected_response = job_reg_interaction['response']['body']
        assert 'id' in data
        assert 'userId' in data
        assert 'tags' in data
        assert data['tags'] == expected_response['tags']
    
    def test_job_registration_missing_headers(self, client):
        """Test job registration with missing headers."""
        response = client.post('/jobs/register', 
                             json={"tags": ["info_job"]})
        
        assert response.status_code == 400
    
    def test_job_registration_invalid_content_type(self, client):
        """Test job registration with invalid content type."""
        headers = {
            'Offline-Token': 'Bearer fake-token',
            'content-type': 'text/plain',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        response = client.post('/jobs/register', 
                             headers=headers,
                             json={"tags": ["info_job"]})
        
        assert response.status_code == 400


class TestJobSubmission:
    """Test job submission endpoint."""
    
    def test_job_submission_success(self, client, pact_contract):
        """Test successful job submission matching Pact contract."""
        # First register a job
        job_reg_headers = {
            'Offline-Token': 'Bearer fake-token',
            'content-type': 'application/json',
            'fredcli-version': '0.4.0',
            'user-agent': 'epx_client_1.2.2'
        }
        
        reg_response = client.post('/jobs/register',
                                 headers=job_reg_headers,
                                 json={"tags": ["info_job"]})
        
        assert reg_response.status_code == 200
        job_data = reg_response.get_json()
        job_id = job_data['id']
        
        # Get the job submission interaction from Pact
        job_sub_interaction = None
        for interaction in pact_contract['interactions']:
            if interaction['description'] == 'a job submission request':
                job_sub_interaction = interaction
                break
        
        assert job_sub_interaction is not None
        
        # Make job submission request
        headers = job_sub_interaction['request']['headers']
        body = {
            "jobId": job_id,
            "context": "job",
            "type": "input"
        }
        
        response = client.post('/jobs',
                             headers=headers,
                             json=body)
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Validate response structure matches Pact contract
        expected_response = job_sub_interaction['response']['body']
        assert 'url' in data
        assert data['url'] == expected_response['url']


class TestRunSubmission:
    """Test run submission endpoint."""
    
    def test_run_submission_success(self, client, pact_contract):
        """Test successful run submission matching Pact contract."""
        # Get the run submission interaction from Pact
        run_sub_interaction = None
        for interaction in pact_contract['interactions']:
            if interaction['description'] == 'a run submission request':
                run_sub_interaction = interaction
                break
        
        assert run_sub_interaction is not None
        
        # Make request matching Pact contract
        headers = run_sub_interaction['request']['headers']
        body = run_sub_interaction['request']['body']
        
        response = client.post('/runs',
                             headers=headers,
                             json=body)
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Validate response structure
        assert 'runResponses' in data
        assert len(data['runResponses']) == len(body['runRequests'])
        
        for run_response in data['runResponses']:
            assert 'runId' in run_response
            assert 'jobId' in run_response
            assert 'status' in run_response
            assert 'runRequest' in run_response
            assert run_response['status'] == 'Submitted'


class TestGetRuns:
    """Test get runs endpoint."""
    
    def test_get_runs_success(self, client, pact_contract):
        """Test successful get runs matching Pact contract."""
        # First submit a run
        run_sub_headers = {
            'Content-Type': 'application/json',
            'Host': 'localhost:5000',
            'User-Agent': 'epx_client_1.2.2',
            'Offline-Token': 'Bearer fake-token',
            'Fredcli-Version': '0.4.0'
        }
        
        run_sub_body = {
            "runRequests": [
                {
                    "jobId": 123,
                    "workingDir": "/workspaces/fred_simulations",
                    "size": "hot",
                    "fredVersion": "latest",
                    "population": {
                        "version": "US_2010.v5",
                        "locations": ["Loving_County_TX"]
                    },
                    "fredArgs": [{"flag": "-p", "value": "main.fred"}],
                    "fredFiles": ["/workspaces/fred_simulations/simulations/agent_info_demo/agent_info.fred"]
                }
            ]
        }
        
        submit_response = client.post('/runs',
                                    headers=run_sub_headers,
                                    json=run_sub_body)
        
        assert submit_response.status_code == 200
        
        # Now get the runs
        get_runs_headers = {
            'Content-Type': 'application/json',
            'Offline-Token': 'Bearer fake-token',
            'Fredcli-Version': '0.4.0'
        }
        
        response = client.get('/runs?job_id=123',
                            headers=get_runs_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Validate response structure
        assert 'runs' in data
        assert len(data['runs']) > 0
        
        for run in data['runs']:
            assert 'id' in run
            assert 'jobId' in run
            assert run['jobId'] == 123
            assert 'status' in run
            assert 'request' in run
    
    def test_get_runs_missing_job_id(self, client):
        """Test get runs with missing job_id parameter."""
        headers = {
            'Content-Type': 'application/json',
            'Offline-Token': 'Bearer fake-token',
            'Fredcli-Version': '0.4.0'
        }
        
        response = client.get('/runs', headers=headers)
        assert response.status_code == 400


class TestHealthAndRoot:
    """Test health check and root endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data
        assert data['status'] == 'healthy'
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.get_json()
        assert 'name' in data
        assert 'version' in data
        assert 'endpoints' in data
