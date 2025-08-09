"""
Tests for register_job use case.
"""

import os
from datetime import datetime
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from epistemix_api.models.job import Job, JobStatus
from epistemix_api.repositories import IJobRepository, SQLAlchemyJobRepository
from epistemix_api.use_cases.register_job import register_job


def create_bearer_token(user_id: int, scopes_hash: str = "test_hash") -> str:
    """Helper function to create a valid bearer token for testing."""
    from epistemix_api.models.user import UserToken

    return UserToken.generate_bearer_token(user_id, scopes_hash)


@freeze_time("2025-01-01 12:00:00")
class TestRegisterJobUseCase:
    @pytest.fixture
    def mock_repository(self):
        repo = Mock(spec=IJobRepository)
        return repo

    def test_register_job__saves_created_job_to_repository(self, mock_repository):
        # Arrange
        user_id = 456
        tags = ["some_tag"]
        bearer_token = create_bearer_token(user_id)

        # Act
        register_job(mock_repository, bearer_token, tags)

        # Assert
        expected_job = Job.create_new(user_id=user_id, tags=tags)
        mock_repository.save.assert_called_once_with(expected_job)

    def test_register_job__when_job_with_no_tags__saves_created_job_to_repository(
        self, mock_repository
    ):
        bearer_token = create_bearer_token(456)
        register_job(mock_repository, bearer_token, None)
        expected_job = Job.create_new(user_id=456, tags=[])
        mock_repository.save.assert_called_once_with(expected_job)

    def test_register_job__when_invalid_user_id_zero__raises_value_error(self, mock_repository):
        bearer_token = create_bearer_token(0)
        with pytest.raises(ValueError, match="User ID must be positive"):
            register_job(mock_repository, bearer_token, ["info_job"])

        # Repository should not be called
        mock_repository.save.assert_not_called()

    def test_register_job__when_invalid_user_id_negative__raises_value_error(self, mock_repository):
        bearer_token = create_bearer_token(-1)
        with pytest.raises(ValueError, match="User ID must be positive"):
            register_job(mock_repository, bearer_token, ["info_job"])

        # Repository should not be called
        mock_repository.save.assert_not_called()

    def test_register_job__when_empty_tags__raises_value_error(self, mock_repository):
        bearer_token = create_bearer_token(456)
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            register_job(mock_repository, bearer_token, [""])

        # Repository should not be called for saving
        mock_repository.save.assert_not_called()

    def test_register_job__when_invalid_bearer_token__raises_value_error(self, mock_repository):
        with pytest.raises(ValueError, match="Invalid bearer token format"):
            register_job(mock_repository, "invalid_token", ["info_job"])

        # Repository should not be called
        mock_repository.save.assert_not_called()

    def test_register_job__when_malformed_bearer_token__raises_value_error(self, mock_repository):
        with pytest.raises(ValueError, match="Failed to decode base64 token"):
            register_job(mock_repository, "Bearer not_base64", ["info_job"])

        # Repository should not be called
        mock_repository.save.assert_not_called()


class TestRegisterJobSQLAlchemyIntegration:
    @pytest.fixture
    def repository(self, db_session):
        """Create a repository using the shared db_session fixture."""
        return SQLAlchemyJobRepository(get_db_session_fn=lambda: db_session)

    @freeze_time("2025-01-01 12:00:00")
    def test_register_job_persists_job_to_database(self, repository):
        bearer_token = create_bearer_token(456)
        job = register_job(repository, user_token_value=bearer_token, tags=["some_tag"])

        # Assert
        expected_job = Job.create_persisted(
            job_id=1,  # SQLAlchemy auto-increment starts at 1
            user_id=456,
            tags=["some_tag"],
            status=JobStatus.CREATED,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        assert job == expected_job

        # Verify job was actually persisted in database
        retrieved_job = repository.find_by_id(1)
        assert retrieved_job == job
