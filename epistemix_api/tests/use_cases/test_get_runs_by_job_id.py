import os
import json
import base64
import pytest
from unittest.mock import Mock
from freezegun import freeze_time
from datetime import datetime

from epistemix_api.use_cases.get_runs import get_runs_by_job_id
from epistemix_api.models.run import Run, RunStatus, PodPhase

from epistemix_api.repositories import IRunRepository, SQLAlchemyRunRepository, get_database_manager


class TestGetRunsByJobIdUseCase:

    @pytest.fixture
    def run_repository(self):
        """Mocked run repository for testing."""
        return Mock(spec=IRunRepository)

    def test_get_runs_by_job_id__returns_runs(self, run_repository):
        expected_runs = [
            Run.create_persisted(
                run_id=1,
                job_id=1,
                user_id=123,
                status=RunStatus.SUBMITTED,
                pod_phase=PodPhase.PENDING,
                request={"jobId": 1, "fredArgs": [], "fredFiles": []},
                created_at=datetime(2025, 1, 1, 12, 0, 0),
                updated_at=datetime(2025, 1, 1, 12, 0, 0)
            )
        ]
        run_repository.find_by_job_id.return_value = expected_runs
        runs = get_runs_by_job_id(run_repository, job_id=1)

        assert runs == expected_runs

    def test_get_runs_by_job_id__handles_no_runs(self, run_repository):
        run_repository.find_by_job_id.return_value = []
        runs = get_runs_by_job_id(run_repository, job_id=999)

        assert runs == []


@pytest.fixture
def bearer_token():
    token_data = {"user_id": 123, "scopes_hash": "abc123"}
    token_json = json.dumps(token_data)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    return f"Bearer {token_b64}"


class TestGetRunsByIdUseCaseSQLAlchemyRunRepositoryIntegration:

    @pytest.fixture
    def db_session(self):
        db_name = "test_submit_runs_integration.db"
        test_db_url = f"sqlite:///{db_name}"
        test_db_manager = get_database_manager(test_db_url)
        test_db_manager.create_tables()

        yield test_db_manager.get_session()

        try:
            os.remove(db_name)
        except FileNotFoundError:
            pass

    @pytest.fixture
    def run_repository(self, db_session):
        get_db_session_fn = lambda: db_session
        return SQLAlchemyRunRepository(get_db_session_fn=get_db_session_fn)

    @freeze_time("2025-01-01 12:00:00")
    def test_get_runs_by_job_id__given_job_id__returns_runs(self, run_repository):

        run = Run.create_unpersisted(
            job_id=1,
            user_id=123,
            request={"jobId": 1, "fredArgs": [], "fredFiles": []},
            pod_phase=PodPhase.PENDING,
            container_status=None,
            status=RunStatus.SUBMITTED
        )
        run_repository.save(run)

        expected_runs = [
            Run.create_persisted(
                run_id=1,
                job_id=1,
                user_id=123,
                status=RunStatus.SUBMITTED,
                pod_phase=PodPhase.PENDING,
                request={"jobId": 1, "fredArgs": [], "fredFiles": []},
                created_at=datetime(2025, 1, 1, 12, 0, 0),
                updated_at=datetime(2025, 1, 1, 12, 0, 0)
            )
        ]
        runs = get_runs_by_job_id(run_repository, job_id=1)
        assert runs == expected_runs
