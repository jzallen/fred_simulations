"""
Integration tests for job use cases.
"""

import os
import pytest
from freezegun import freeze_time
from datetime import datetime

from epistemix_api.models.job import Job, JobStatus
from epistemix_api.repositories import SQLAlchemyJobRepository, get_database_manager
from epistemix_api.use_cases.job_use_cases import register_job


class TestRegisterJobSQLAlchemyIntegration:
    
    @pytest.fixture
    def repository(self):
        test_db_url = "sqlite:///test_register_job_integration.db"
        test_db_manager = get_database_manager(test_db_url)
        test_db_manager.create_tables()

        yield SQLAlchemyJobRepository(get_db_session_fn=test_db_manager.get_session)

        try:
            os.remove("test_register_job_integration.db")
        except FileNotFoundError:
            pass
    
    @freeze_time("2025-01-01 12:00:00")
    def test_register_job_persists_job_to_database(self, repository):
        job = register_job(repository, user_id=456, tags=["some_tag"])
        
        # Assert
        expected_job = Job.create_persisted(
            job_id=1,  # SQLAlchemy auto-increment starts at 1
            user_id=456,
            tags=["some_tag"],
            status=JobStatus.CREATED,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0)
        )
        assert job == expected_job
        
        # Verify job was actually persisted in database
        retrieved_job = repository.find_by_id(1)
        assert retrieved_job == job
