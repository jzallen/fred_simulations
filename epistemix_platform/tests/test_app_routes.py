"""
Tests for the refactored Flask app using Clean Architecture.
"""

import base64
import json
import os
from datetime import datetime

import pytest
from freezegun import freeze_time

from epistemix_platform.app import app


@pytest.fixture
def client(tmp_path_factory):
    """Create a test client for the Flask app with a fresh test database using tmp_path_factory."""

    # Create a unique temporary database using tmp_path_factory
    tmp_dir = tmp_path_factory.mktemp("db")
    db_path = os.path.join(tmp_dir, "test_job_routes.sqlite")
    test_db_url = f"sqlite:///{db_path}"

    # Configure Flask app to use test database and testing environment
    app.config["TESTING"] = True
    app.config["DATABASE_URL"] = test_db_url
    app.config["ENVIRONMENT"] = "TESTING"

    with app.test_client() as client:
        yield client


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
            "Offline-Token": bearer_token,
            "content-type": "application/json",
            "fredcli-version": "0.4.0",
            "user-agent": "epx_client_1.2.2",
        }

        body = {"tags": ["info_job"]}

        response = client.post("/jobs/register", headers=headers, json=body)
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
            "Offline-Token": bearer_token,
            "content-type": "application/json",
            "fredcli-version": "0.4.0",
            "user-agent": "epx_client_1.2.2",
        }

        register_body = {"tags": ["info_job"]}
        client.post("/jobs/register", headers=register_headers, json=register_body)

        # Now submit the registered job
        headers = {
            "Offline-Token": bearer_token,
            "content-type": "application/json",
            "fredcli-version": "0.4.0",
            "user-agent": "epx_client_1.2.2",
        }

        submit_body = {"jobId": 1, "context": "job", "type": "input"}

        response = client.post("/jobs", headers=headers, json=submit_body)

        assert response.status_code == 200
        data = response.get_json()
        expected_job_submission_data = {
            "url": "http://localhost:5001/pre-signed-url",
        }
        assert data == expected_job_submission_data

    def test_job_submission__invalid_job_id__returns_error_response(self, client):
        """Test that job submission validates business rules."""
        headers = {
            "Offline-Token": "Bearer fake-token",
            "content-type": "application/json",
            "fredcli-version": "0.4.0",
            "user-agent": "epx_client_1.2.2",
        }

        # Try to submit a non-existent job
        submit_body = {"jobId": 99999, "context": "job", "type": "input"}  # Non-existent job

        response = client.post("/jobs", headers=headers, json=submit_body)

        assert response.status_code == 400
        data = response.get_json()
        expected_error_data = {
            "error": "Job 99999 not found",
        }
        assert data == expected_error_data

    def test_run_submission__valid_request__returns_successful_response(self, client, bearer_token):
        """Test submitting multiple runs."""
        # First register a job (required for JobS3Prefix)
        register_headers = {
            "Offline-Token": bearer_token,
            "content-type": "application/json",
            "fredcli-version": "0.4.0",
            "user-agent": "epx_client_1.2.2",
        }

        register_body = {"tags": ["test_runs"]}
        register_response = client.post("/jobs/register", headers=register_headers, json=register_body)
        assert register_response.status_code == 200
        job_data = register_response.get_json()
        job_id = job_data["id"]

        # Now submit runs for the registered job
        headers = {
            "Offline-Token": bearer_token,
            "content-type": "application/json",
            "fredcli-version": "0.4.0",
            "user-agent": "epx_client_1.2.2",
        }

        run_requests = {
            "runRequests": [
                {
                    "jobId": job_id,
                    "workingDir": "/workspaces/fred_simulations",
                    "size": "hot",
                    "fredVersion": "latest",
                    "population": {"version": "US_2010.v5", "locations": ["Loving_County_TX"]},
                    "fredArgs": [{"flag": "-p", "value": "main.fred"}],
                    "fredFiles": [
                        "/workspaces/fred_simulations/simulations/agent_info_demo/agent_info.fred"
                    ],
                }
            ]
        }

        response = client.post("/runs", headers=headers, json=run_requests)

        assert response.status_code == 200
        expected_response = {
            "runResponses": [
                {
                    "runId": 1,
                    "jobId": job_id,
                    "status": "Submitted",
                    "errors": None,
                    "runRequest": {
                        "jobId": job_id,
                        "workingDir": "/workspaces/fred_simulations",
                        "size": "hot",
                        "fredVersion": "latest",
                        "population": {"version": "US_2010.v5", "locations": ["Loving_County_TX"]},
                        "fredArgs": [{"flag": "-p", "value": "main.fred"}],
                        "fredFiles": [
                            "/workspaces/fred_simulations/simulations/agent_info_demo/"
                            "agent_info.fred"
                        ],
                    },
                }
            ]
        }
        data = response.get_json()
        assert data == expected_response

    def test_job_config_submission__valid_request__returns_successful_response(
        self, client, bearer_token
    ):
        """Test submitting job configuration."""
        headers = {
            "Offline-Token": bearer_token,
            "content-type": "application/json",
            "fredcli-version": "0.4.0",
            "user-agent": "epx_client_1.2.2",
        }

        # First register a job so it exists in the repository
        register_body = {"tags": ["test_job"]}
        client.post("/jobs/register", headers=headers, json=register_body)

        submit_body = {"jobId": 1, "context": "job", "type": "config"}

        response = client.post("/jobs", headers=headers, json=submit_body)

        assert response.status_code == 200
        data = response.get_json()
        expected_job_submission_data = {
            "url": "http://localhost:5001/pre-signed-url",
        }
        assert data == expected_job_submission_data

    def test_run_config_submission__valid_request__returns_successful_response(
        self, client, bearer_token
    ):
        """Test submitting run configuration."""
        headers = {
            "Offline-Token": bearer_token,
            "content-type": "application/json",
            "fredcli-version": "0.4.0",
            "user-agent": "epx_client_1.2.2",
        }

        # First register a job
        register_body = {"tags": ["test_job"]}
        client.post("/jobs/register", headers=headers, json=register_body)

        # Then submit a run to create it with proper format
        run_submit_body = {
            "runRequests": [
                {
                    "jobId": 1,
                    "workingDir": "/workspaces/fred_simulations",
                    "size": "hot",
                    "fredVersion": "latest",
                    "population": {"version": "US_2010.v5", "locations": ["Loving_County_TX"]},
                    "fredArgs": [{"flag": "-p", "value": "main.fred"}],
                    "fredFiles": ["/workspaces/fred_simulations/simulations/test.fred"],
                }
            ]
        }
        client.post("/runs", headers=headers, json=run_submit_body)

        # Now submit the run config
        submit_body = {"jobId": 1, "context": "run", "type": "config", "runId": 1}

        response = client.post("/jobs", headers=headers, json=submit_body)

        assert response.status_code == 200
        data = response.get_json()
        expected_run_submission_data = {
            "url": "http://localhost:5001/pre-signed-url",
        }
        assert data == expected_run_submission_data

    @freeze_time("2025-01-01 12:00:00")
    def test_get_runs_by_job_id__valid_job_id__returns_runs(self, client, bearer_token):
        """Test getting runs by job ID."""
        headers = {
            "Offline-Token": bearer_token,
            "content-type": "application/json",
            "fredcli-version": "0.4.0",
            "user-agent": "epx_client_1.2.2",
        }

        # First register a job
        client.post("/jobs/register", headers=headers, json={"tags": ["info_job"]})

        # Now submit a run for that job
        run_requests = {
            "runRequests": [
                {
                    "jobId": 1,
                    "workingDir": "/workspaces/fred_simulations",
                    "size": "hot",
                    "fredVersion": "latest",
                    "population": {"version": "US_2010.v5", "locations": ["Loving_County_TX"]},
                    "fredArgs": [{"flag": "-p", "value": "main.fred"}],
                    "fredFiles": [
                        "/workspaces/fred_simulations/simulations/agent_info_demo/agent_info.fred"
                    ],
                }
            ]
        }

        client.post("/runs", headers=headers, json=run_requests)

        # Now get runs by job ID
        response = client.get("/runs", headers=headers, query_string={"job_id": 1})

        assert response.status_code == 200
        data = response.get_json()
        expected_runs_data = {
            "runs": [
                {
                    "id": 1,
                    "jobId": 1,
                    "userId": 123,
                    "createdTs": datetime(2025, 1, 1, 12, 0, 0).isoformat(),
                    "request": {
                        "jobId": 1,
                        "workingDir": "/workspaces/fred_simulations",
                        "size": "hot",
                        "fredVersion": "latest",
                        "population": {"version": "US_2010.v5", "locations": ["Loving_County_TX"]},
                        "fredArgs": [{"flag": "-p", "value": "main.fred"}],
                        "fredFiles": [
                            "/workspaces/fred_simulations/simulations/agent_info_demo/"
                            "agent_info.fred"
                        ],
                    },
                    "podPhase": "Pending",
                    "containerStatus": None,
                    "status": "QUEUED",
                    "userDeleted": False,
                    "epxClientVersion": "1.2.2",
                    "config_url": "http://localhost:5001/pre-signed-url",
                    "results_url": None,
                    "results_uploaded_at": None,
                }
            ]
        }
        assert data == expected_runs_data
