"""
Tests for the /jobs/results endpoint.
"""

import base64
import json
from datetime import datetime
from unittest.mock import patch

import pytest

from epistemix_platform.app import app
from epistemix_platform.repositories.database import RunRecord, get_database_manager


class TestJobResultsEndpoint:
    """Test suite for the /jobs/results endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the Flask app."""
        app.config["TESTING"] = True
        # Use a file-based database for persistence during the test
        app.config["DATABASE_URL"] = "sqlite:///test_epistemix_platform.db"
        with app.test_client() as client:
            with app.app_context():
                # Initialize database
                db_manager = get_database_manager(app.config["DATABASE_URL"])
                db_manager.drop_tables()  # Clean slate
                db_manager.create_tables()
            yield client
            # Clean up after test
            with app.app_context():
                db_manager = get_database_manager(app.config["DATABASE_URL"])
                db_manager.drop_tables()

    @pytest.fixture
    def bearer_token(self):
        """Create a valid bearer token for authentication."""
        token_data = {"user_id": 123, "scopes_hash": "abc123"}
        token_json = json.dumps(token_data)
        token_b64 = base64.b64encode(token_json.encode()).decode()
        return f"Bearer {token_b64}"

    @pytest.fixture
    def setup_runs_with_urls(self):
        """Setup test runs with URLs in the database."""
        with app.app_context():
            db_manager = get_database_manager(app.config["DATABASE_URL"])
            db_manager.create_tables()  # Ensure tables exist
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
        from epistemix_platform.repositories.database import JobRecord

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
        self, client, bearer_token
    ):
        """Test that runs get URLs even without persisted results_url (on-the-fly reconstruction)."""
        from epistemix_platform.repositories.database import JobRecord

        with app.app_context():
            db_manager = get_database_manager(app.config["DATABASE_URL"])
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
