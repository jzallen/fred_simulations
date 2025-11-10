import base64
import json
from datetime import datetime
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from epistemix_platform.mappers.run_mapper import RunMapper
from epistemix_platform.models.run import PodPhase, Run, RunStatus
from epistemix_platform.repositories import IRunRepository, SQLAlchemyRunRepository
from epistemix_platform.use_cases.get_runs import get_runs_by_job_id


class TestGetRunsByJobIdUseCase:
    @pytest.fixture
    def run_repository(self):
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
                updated_at=datetime(2025, 1, 1, 12, 0, 0),
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
    def run_repository(self, db_session):
        run_mapper = RunMapper()
        return SQLAlchemyRunRepository(run_mapper=run_mapper, get_db_session_fn=lambda: db_session)

    @freeze_time("2025-01-01 12:00:00")
    def test_get_runs_by_job_id__given_job_id__returns_runs(self, run_repository):
        run = Run.create_unpersisted(
            job_id=1,
            user_id=123,
            request={"jobId": 1, "fredArgs": [], "fredFiles": []},
            pod_phase=PodPhase.PENDING,
            container_status=None,
            status=RunStatus.SUBMITTED,
            config_url="http://example.com/config.json",
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
                updated_at=datetime(2025, 1, 1, 12, 0, 0),
                config_url="http://example.com/config.json",
            )
        ]
        runs = get_runs_by_job_id(run_repository, job_id=1)
        assert runs == expected_runs
