"""
Tests for SQLAlchemy job repository implementation.
"""

import pytest
from freezegun import freeze_time
from datetime import datetime

from epistemix_api.models.run import Run, RunStatus, PodPhase
from epistemix_api.repositories import SQLAlchemyRunRepository
from epistemix_api.repositories.interfaces import IRunRepository
from epistemix_api.repositories.database import RunRecord
from epistemix_api.mappers.run_mapper import RunMapper


@pytest.fixture
def repository(db_session):
    """Create a fresh repository for each test using the shared db_session fixture."""
    return SQLAlchemyRunRepository(get_db_session_fn=lambda: db_session)


@freeze_time("2025-01-01 12:00:00")
class TestSQLAlchemyJobRepository:
    
    def test_save__given_valid_new_run__returns_run_with_id(self, repository: IRunRepository):
        """Test saving a new run."""
        run = Run.create_unpersisted(
            job_id=1, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        saved_run = repository.save(run)
        
        expected_run = Run.create_persisted(
            run_id=1,
            user_id=1,
            job_id=1,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request={},
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0)
        )
        assert saved_run == expected_run

    def test_save__given_valid_new_run__run_persisted_on_commit(self, repository: IRunRepository, db_session):
        """Test that a new run is saved to the database."""
        run = Run.create_unpersisted(
            job_id=1, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        saved_run = repository.save(run)
        db_session.commit()
        
        expected_run = Run.create_persisted(
            run_id=1,
            user_id=1,
            job_id=1,
            status=RunStatus.SUBMITTED,
            pod_phase=PodPhase.PENDING,
            request={},
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0)
        )
        run_record = db_session.query(RunRecord).get(1)
        persisted_run = RunMapper.record_to_domain(run_record)
        assert persisted_run == expected_run

    def test_save__given_existing_run__updates_run(self, repository: IRunRepository, db_session):
        """Test updating an existing run."""
        run = Run.create_unpersisted(
            job_id=1, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        saved_run = repository.save(run)
        
        # Update the run
        saved_run.status = RunStatus.RUNNING
        updated_run = repository.save(saved_run)
        
        expected_run = Run.create_persisted(
            run_id=1,
            user_id=1,
            job_id=1,
            status=RunStatus.RUNNING,
            pod_phase=PodPhase.PENDING,
            request={},
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0)
        )
        assert updated_run == expected_run

    def test_save__given_existing_run__updates_run_on_commit(self, repository: IRunRepository, db_session):
        run = Run.create_unpersisted(
            job_id=1, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={}, 
        )
        saved_run = repository.save(run)
        db_session.commit()
        
        saved_run.status = RunStatus.RUNNING
        repository.save(saved_run)
        db_session.commit()
        
        expected_run = Run.create_persisted(
            run_id=1,
            user_id=1,
            job_id=1,
            status=RunStatus.RUNNING,
            pod_phase=PodPhase.PENDING,
            request={},
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0)
        )
        run_record = db_session.query(RunRecord).get(1)
        persisted_run = RunMapper.record_to_domain(run_record)
        assert persisted_run == expected_run

    def test_delete__given_existing_run__deletes_run_on_commit(self, repository: IRunRepository, db_session):
        run = Run.create_unpersisted(
            job_id=1, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        saved_run = repository.save(run)
        db_session.commit()
        
        assert repository.delete(saved_run.id) is True
        db_session.commit()

        
        # Verify the run is deleted
        run_record = db_session.query(RunRecord).get(1)
        assert run_record is None
    
    def test_delete__given_non_existing_run__returns_false(self, repository: IRunRepository):
        assert repository.delete(999) is False

    def test_exists__given_existing_run__returns_true(self, repository: IRunRepository, db_session):
        run = Run.create_unpersisted(
            job_id=1, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        saved_run = repository.save(run)
        db_session.commit()
        
        assert repository.exists(saved_run.id) is True

    def test_exists__given_non_existing_run__returns_false(self, repository: IRunRepository):
        assert repository.exists(999) is False

    def test_find_by_id__given_run_id__returns_run(self, repository: IRunRepository, db_session):
        run = Run.create_unpersisted(
            job_id=1, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        saved_run = repository.save(run)
        db_session.commit()
        
        found_run = repository.find_by_id(saved_run.id)
        assert found_run == saved_run

    def test_find_by_id__given_non_existing_run_id__returns_none(self, repository: IRunRepository):
        assert repository.find_by_id(999) is None

    def test_find_by_job_id__given_existing_job_id__returns_runs(self, repository: IRunRepository, db_session):
        run1 = Run.create_unpersisted(
            job_id=1, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        run2 = Run.create_unpersisted(
            job_id=1, 
            user_id=2, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        repository.save(run1)
        repository.save(run2)
        db_session.commit()
        
        runs = repository.find_by_job_id(1)
        assert runs == [run1, run2]

    def test_find_by_job_id__given_non_existing_job_id__returns_empty_list(self, repository: IRunRepository):
        runs = repository.find_by_job_id(999)
        assert runs == []

    def test_find_by_user_id__given_existing_user_id__returns_runs(self, repository: IRunRepository, db_session):
        run1 = Run.create_unpersisted(
            job_id=1, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        run2 = Run.create_unpersisted(
            job_id=2, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        repository.save(run1)
        repository.save(run2)
        db_session.commit()
        
        runs = repository.find_by_user_id(1)
        assert runs == [run1, run2]

    def test_find_by_user_id__given_non_existing_user_id__returns_empty_list(self, repository: IRunRepository):
        runs = repository.find_by_user_id(999)
        assert runs == []

    def test_find_by_status__given_existing_status__returns_runs(self, repository: IRunRepository, db_session):
        run1 = Run.create_unpersisted(
            job_id=1, 
            user_id=1, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        run2 = Run.create_unpersisted(
            job_id=2, 
            user_id=2, 
            status=RunStatus.SUBMITTED, 
            pod_phase=PodPhase.PENDING,
            request={},  # Assuming request is empty for simplicity
        )
        repository.save(run1)
        repository.save(run2)
        db_session.commit()
        
        runs = repository.find_by_status(RunStatus.SUBMITTED)
        assert runs == [run1, run2]

    def test_find_by_status__given_non_existing_status__returns_empty_list(self, repository: IRunRepository):
        runs = repository.find_by_status(RunStatus.DONE)
        assert runs == []
