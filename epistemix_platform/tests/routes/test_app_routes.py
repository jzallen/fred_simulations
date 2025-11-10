"""
Tests for Flask app routes using Clean Architecture.

Includes tests for job registration, submission, run management, and results endpoints.
"""

import base64
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from freezegun import freeze_time

from epistemix_platform.app import app


@pytest.fixture
def mock_batch_client():
    """Create a mock AWS Batch client for testing."""
    mock_client = Mock()
    mock_client.submit_job.return_value = {"jobId": "batch-job-123"}
    # Mock for describe_run() status synchronization
    mock_client.list_jobs.return_value = {"jobSummaryList": [{"jobId": "batch-job-123"}]}
    mock_client.describe_jobs.return_value = {
        "jobs": [{"jobId": "batch-job-123", "status": "RUNNING", "statusReason": ""}]
    }
    return mock_client


@pytest.fixture
def client(tmp_path_factory, mock_batch_client):
    """Create a test client for the Flask app with a fresh test database using tmp_path_factory."""

    # Create a unique temporary database using tmp_path_factory
    tmp_dir = tmp_path_factory.mktemp("db")
    db_path = os.path.join(tmp_dir, "test_job_routes.sqlite")
    test_db_url = f"sqlite:///{db_path}"

    # Configure Flask app to use test database and testing environment
    app.config["TESTING"] = True
    app.config["DATABASE_URL"] = test_db_url
    app.config["ENVIRONMENT"] = "TESTING"

    # Patch AWSBatchSimulationRunner.create to use mock batch client
    with patch(
        "epistemix_platform.gateways.simulation_runner.AWSBatchSimulationRunner.create"
    ) as mock_create:
        from epistemix_platform.gateways.simulation_runner import AWSBatchSimulationRunner

        mock_create.return_value = AWSBatchSimulationRunner(
            batch_client=mock_batch_client,
            job_queue_name="fred-batch-queue-test",
            job_definition_name="fred-simulation-runner-test",
        )

        with app.test_client() as client:
            yield client


@pytest.fixture
def bearer_token():
    token_data = {"user_id": 123, "scopes_hash": "abc123"}
    token_json = json.dumps(token_data)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    return f"Bearer {token_b64}"


@pytest.fixture
def setup_runs_with_urls(tmp_path_factory):
    """Setup test runs with URLs in the database."""
    from epistemix_platform.repositories.database import RunRecord, get_database_manager

    # Create a unique temporary database
    tmp_dir = tmp_path_factory.mktemp("db")
    db_path = tmp_dir / "test_results.sqlite"
    test_db_url = f"sqlite:///{db_path}"

    # Configure Flask app to use test database
    app.config["DATABASE_URL"] = test_db_url

    with app.app_context():
        db_manager = get_database_manager(test_db_url)
        db_manager.create_tables()
        session = db_manager.get_session()

        # Create test runs with results URLs
        run1 = RunRecord(
            id=1,
            job_id=100,
            user_id=123,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            request={"test": "data"},
            results_url="https://example.com/run1-url",
        )

        run2 = RunRecord(
            id=2,
            job_id=100,
            user_id=123,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            request={"test": "data"},
            results_url="https://example.com/run2-url",
        )

        # Run without results URL
        run3 = RunRecord(
            id=3,
            job_id=100,
            user_id=123,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            request={"test": "data"},
            results_url=None,
        )

        # Run for different job
        run4 = RunRecord(
            id=4,
            job_id=200,
            user_id=123,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            request={"test": "data"},
            results_url="https://example.com/run4-url",
        )

        session.add(run1)
        session.add(run2)
        session.add(run3)
        session.add(run4)
        session.commit()
        session.close()

    yield

    # Cleanup
    with app.app_context():
        db_manager.drop_tables()


class TestAppRoutes:
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
        register_response = client.post(
            "/jobs/register", headers=register_headers, json=register_body
        )
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
                    "podPhase": "Running",
                    "containerStatus": None,
                    "status": "RUNNING",
                    "userDeleted": False,
                    "epxClientVersion": "1.2.2",
                    "config_url": "http://localhost:5001/pre-signed-url",
                    "results_url": None,
                    "results_uploaded_at": None,
                }
            ]
        }
        assert data == expected_runs_data

    def test_get_job_results__returns_urls_for_job(
        self, client, bearer_token, setup_runs_with_urls
    ):
        """Test that the endpoint generates presigned URLs for all runs (batch operation)."""
        # Mock the controller's get_run_results_download to return presigned URLs
        with patch("epistemix_platform.app.get_job_controller") as mock_get_controller:
            from unittest.mock import Mock

            from returns.result import Success

            # Create a mock controller
            mock_controller = Mock()

            # Set up the get_run_results_download method as a batch operation
            # It now takes job_id and bucket_name, returns all URLs for the job
            mock_controller.get_run_results_download.return_value = Success(
                [
                    {
                        "run_id": 1,
                        "url": "https://s3.amazonaws.com/presigned-1?X-Amz-Expires=86400",
                    },
                    {
                        "run_id": 2,
                        "url": "https://s3.amazonaws.com/presigned-2?X-Amz-Expires=86400",
                    },
                    {
                        "run_id": 3,
                        "url": "https://s3.amazonaws.com/presigned-3?X-Amz-Expires=86400",
                    },
                ]
            )

            # Return the mock controller
            mock_get_controller.return_value = mock_controller

            response = client.get(
                "/jobs/results?job_id=100",
                headers={"Offline-Token": bearer_token, "Fredcli-Version": "1.0.0"},
            )

            assert response.status_code == 200
            data = response.get_json()

            assert "urls" in data
            assert len(data["urls"]) == 3  # All runs get URLs (batch operation)

            # Check the presigned URLs
            urls = data["urls"]
            assert {
                "run_id": 1,
                "url": "https://s3.amazonaws.com/presigned-1?X-Amz-Expires=86400",
            } in urls
            assert {
                "run_id": 2,
                "url": "https://s3.amazonaws.com/presigned-2?X-Amz-Expires=86400",
            } in urls
            assert {
                "run_id": 3,
                "url": "https://s3.amazonaws.com/presigned-3?X-Amz-Expires=86400",
            } in urls

            # Verify controller was called once as a batch operation
            # Note: bucket_name comes from app.config["S3_UPLOAD_BUCKET"]
            mock_controller.get_run_results_download.assert_called_once()
            call_args = mock_controller.get_run_results_download.call_args
            assert call_args[1]["job_id"] == 100
            assert "bucket_name" in call_args[1]

    def test_get_job_results__missing_job_id__returns_error(self, client, bearer_token):
        """Test that the endpoint returns an error when job_id is missing."""
        response = client.get(
            "/jobs/results", headers={"Offline-Token": bearer_token, "Fredcli-Version": "1.0.0"}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Missing job_id parameter"

    def test_get_job_results__invalid_job_id__returns_error(self, client, bearer_token):
        """Test that the endpoint returns an error when job_id is invalid."""
        response = client.get(
            "/jobs/results?job_id=not_a_number",
            headers={"Offline-Token": bearer_token, "Fredcli-Version": "1.0.0"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Invalid job_id parameter"

    def test_get_job_results__missing_headers__returns_error(self, client):
        """Test that the endpoint returns an error when required headers are missing."""
        response = client.get("/jobs/results?job_id=100")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Missing required headers"

    def test_get_job_results__no_runs_for_job__returns_empty_list(
        self, client, bearer_token, setup_runs_with_urls
    ):
        """Test that the endpoint returns an empty list when there are no runs for the job."""
        # Create a job without any runs
        from epistemix_platform.repositories.database import JobRecord, get_database_manager

        with app.app_context():
            db_manager = get_database_manager(app.config["DATABASE_URL"])
            session = db_manager.get_session()

            job = JobRecord(
                id=999,
                user_id=123,
                tags=["test"],
                created_at=datetime.utcnow(),
            )
            session.add(job)
            session.commit()
            session.close()

        response = client.get(
            "/jobs/results?job_id=999",  # Job exists but has no runs
            headers={"Offline-Token": bearer_token, "Fredcli-Version": "1.0.0"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "urls" in data
        assert data["urls"] == []

    def test_get_job_results__runs_without_persisted_urls__still_generates_urls(
        self, client, bearer_token, tmp_path_factory
    ):
        """Test that runs get URLs even without persisted results_url (on-the-fly reconstruction)."""
        from epistemix_platform.repositories.database import (
            JobRecord,
            RunRecord,
            get_database_manager,
        )

        # Create a unique temporary database
        tmp_dir = tmp_path_factory.mktemp("db")
        db_path = tmp_dir / "test_no_urls.sqlite"
        test_db_url = f"sqlite:///{db_path}"
        app.config["DATABASE_URL"] = test_db_url

        with app.app_context():
            db_manager = get_database_manager(test_db_url)
            db_manager.create_tables()  # Ensure tables exist
            session = db_manager.get_session()

            # Create a job first
            job = JobRecord(
                id=300,
                user_id=123,
                tags=["test"],
                created_at=datetime(2025, 11, 8, 20, 56, 47),
            )
            session.add(job)

            # Create a run without persisted results_url
            run = RunRecord(
                id=1,
                job_id=300,
                user_id=123,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                request={"test": "data"},
                results_url=None,  # No persisted results URL
            )

            session.add(run)
            session.commit()
            session.close()

        # Mock S3 repository to avoid actual S3 calls
        with patch("epistemix_platform.app.get_job_controller") as mock_get_controller:
            from unittest.mock import Mock

            from returns.result import Success

            mock_controller = Mock()
            # Batch operation returns URL reconstructed on-the-fly
            mock_controller.get_run_results_download.return_value = Success(
                [
                    {
                        "run_id": 1,
                        "url": "https://test-bucket.s3.amazonaws.com/jobs/300/2025/11/08/205647/run_1_results.zip?X-Amz-Expires=86400",
                    }
                ]
            )

            mock_get_controller.return_value = mock_controller

            response = client.get(
                "/jobs/results?job_id=300",
                headers={"Offline-Token": bearer_token, "Fredcli-Version": "1.0.0"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "urls" in data
            assert len(data["urls"]) == 1  # Run gets URL even without persisted results_url
            assert data["urls"][0]["run_id"] == 1
            assert "X-Amz-Expires" in data["urls"][0]["url"]
