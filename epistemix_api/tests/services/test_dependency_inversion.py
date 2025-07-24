"""
Tests demonstrating dependency inversion with repository interfaces.
Shows how the JobService can work with different repository implementations.
"""
import os

import pytest

from returns.pipeline import is_successful

from epistemix_api.models.job import JobStatus
from epistemix_api.services.job_service import JobService
from epistemix_api.repositories.job_repository import SQLAlchemyJobRepository
from epistemix_api.repositories.database import get_database_manager


@pytest.fixture
def job_service():
    # Set up test database URL
    test_db_url = "sqlite:///test_job_routes.db"
    
    # Clear and recreate tables for each test
    test_db_manager = get_database_manager(test_db_url)
    test_db_manager.create_tables()

    job_repository = SQLAlchemyJobRepository(test_db_manager.get_session)
    yield JobService.create_with_job_repository(job_repository)

    try:
        os.remove("test_job_routes.db")
    except FileNotFoundError:
        pass


class TestJobServiceIntegrationwithJobRepository:
    """Test dependency inversion with different repository implementations."""
    
    def test_service_registers_job(self, job_service):
        result = job_service.register_job(user_id=456, tags=["test_job"])
        assert is_successful(result)
        job_dict = result.unwrap()
        
        expected_job_data = {
            "id": 1,
            "userId": 456,
            "tags": ["test_job"],
            "status": JobStatus.CREATED.value,
            "createdAt": job_dict["createdAt"],
            "updatedAt": job_dict["updatedAt"],
            "metadata": {}
        }
        assert job_dict == expected_job_data

    def test_service_gets_registered_job(self, job_service):

        # Register a job
        result = job_service.register_job(user_id=456, tags=["mock_test"])
        assert is_successful(result)
        job_dict = result.unwrap()
        
        # Retrieve the job
        expected_job_data = {
            "id": job_dict["id"],
            "userId": 456,
            "tags": ["mock_test"],
            "status": JobStatus.CREATED.value,
            "createdAt": job_dict["createdAt"],
            "updatedAt": job_dict["updatedAt"],
            "metadata": {}
        }
        retrieved_job = job_service.get_job(job_dict["id"])
        assert retrieved_job.to_dict() == expected_job_data
    
    def test_service_submits_job(self, job_service):
        """Test that service only uses repository interface methods."""
        
        # Register and submit a job
        register_result = job_service.register_job(user_id=456, tags=["interface_test"])
        assert is_successful(register_result)
        job_dict = register_result.unwrap()

        submit_result = job_service.submit_job(job_dict["id"])
        assert is_successful(submit_result)
        response = submit_result.unwrap()
        
        # Verify business logic works regardless of repository implementation
        assert response["url"] == "http://localhost:5001/pre-signed-url"
        
        # Verify job status was updated
        updated_job = job_service.get_job(job_dict["id"])
        assert updated_job.status == JobStatus.SUBMITTED
