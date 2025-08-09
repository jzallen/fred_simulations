"""
Tests for the /jobs/results endpoint.
"""

import base64
import json
from datetime import datetime

import pytest

from epistemix_api.app import app
from epistemix_api.repositories.database import RunRecord, get_database_manager


class TestJobResultsEndpoint:
    """Test suite for the /jobs/results endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the Flask app."""
        app.config["TESTING"] = True
        # Use a file-based database for persistence during the test
        app.config["DATABASE_URL"] = "sqlite:///test_epistemix_api.db"
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

            # Create test runs with URLs
            run1 = RunRecord(
                id=1,
                job_id=100,
                user_id=123,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                request={"test": "data"},
                url="https://example.com/run1-url",
            )

            run2 = RunRecord(
                id=2,
                job_id=100,
                user_id=123,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                request={"test": "data"},
                url="https://example.com/run2-url",
            )

            # Run without URL
            run3 = RunRecord(
                id=3,
                job_id=100,
                user_id=123,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                request={"test": "data"},
                url=None,
            )

            # Run for different job
            run4 = RunRecord(
                id=4,
                job_id=200,
                user_id=123,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                request={"test": "data"},
                url="https://example.com/run4-url",
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
        """Test that the endpoint returns URLs for all runs with URLs for the specified job."""
        response = client.get(
            "/jobs/results?job_id=100",
            headers={"Offline-Token": bearer_token, "Fredcli-Version": "1.0.0"},
        )

        assert response.status_code == 200
        data = response.get_json()

        assert "urls" in data
        assert len(data["urls"]) == 2  # Only runs with URLs

        # Check the URLs
        urls = data["urls"]
        assert {"run_id": 1, "url": "https://example.com/run1-url"} in urls
        assert {"run_id": 2, "url": "https://example.com/run2-url"} in urls

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
        response = client.get(
            "/jobs/results?job_id=999",  # Non-existent job
            headers={"Offline-Token": bearer_token, "Fredcli-Version": "1.0.0"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "urls" in data
        assert data["urls"] == []

    def test_get_job_results__runs_without_urls__returns_empty_list(self, client, bearer_token):
        """Test that runs without URLs are not included in the response."""
        with app.app_context():
            db_manager = get_database_manager(app.config["DATABASE_URL"])
            db_manager.create_tables()  # Ensure tables exist
            session = db_manager.get_session()

            # Create a run without URL
            run = RunRecord(
                id=1,
                job_id=300,
                user_id=123,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                request={"test": "data"},
                url=None,  # No URL
            )

            session.add(run)
            session.commit()
            session.close()

        response = client.get(
            "/jobs/results?job_id=300",
            headers={"Offline-Token": bearer_token, "Fredcli-Version": "1.0.0"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "urls" in data
        assert data["urls"] == []
