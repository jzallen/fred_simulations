"""
Unit tests for RunMapper class.
"""

import datetime
from epistemix_api.mappers.run_mapper import RunMapper
from epistemix_api.repositories.database import RunRecord, RunStatusEnum, PodPhaseEnum
from epistemix_api.models.run import Run, RunStatus, PodPhase


class TestRunMapper:

    def test_record_to_domain__converts_all_fields_correctly(self):
        created_at = datetime.datetime(2025, 1, 15, 10, 30, 0)
        updated_at = datetime.datetime(2025, 1, 15, 11, 30, 0)
        
        run_record = RunRecord(
            id=123,
            job_id=456,
            user_id=789,
            created_at=created_at,
            updated_at=updated_at,
            request={'simulation': 'test_sim', 'parameters': {'population': 10000}},
            pod_phase=PodPhaseEnum.RUNNING,
            container_status='healthy',
            status=RunStatusEnum.RUNNING,
            user_deleted=0,
            epx_client_version='1.5.0'
        )

        run = RunMapper.record_to_domain(run_record)

        assert run.id == 123
        assert run.job_id == 456
        assert run.user_id == 789
        assert run.created_at == created_at
        assert run.updated_at == updated_at
        assert run.request == {'simulation': 'test_sim', 'parameters': {'population': 10000}}
        assert run.pod_phase == PodPhase.RUNNING
        assert run.container_status == 'healthy'
        assert run.status == RunStatus.RUNNING
        assert run.user_deleted is False
        assert run.epx_client_version == '1.5.0'
        assert run.is_persisted() is True

    def test_record_to_domain__with_user_deleted_true(self):
        run_record = RunRecord(
            id=999,
            job_id=111,
            user_id=222,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            request={'minimal': 'test'},
            pod_phase=PodPhaseEnum.SUCCEEDED,
            container_status=None,
            status=RunStatusEnum.DONE,
            user_deleted=1,  # True
            epx_client_version='1.2.2'
        )

        run = RunMapper.record_to_domain(run_record)

        assert run.user_deleted is True

    def test_record_to_domain__with_none_container_status(self):
        run_record = RunRecord(
            id=100,
            job_id=200,
            user_id=300,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            request={},
            pod_phase=PodPhaseEnum.PENDING,
            container_status=None,
            status=RunStatusEnum.SUBMITTED,
            user_deleted=0,
            epx_client_version='1.2.2'
        )

        run = RunMapper.record_to_domain(run_record)

        assert run.container_status is None

    def test_record_to_domain__with_all_run_statuses(self):
        base_record = RunRecord(
            id=1,
            job_id=1,
            user_id=1,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            request={'test': 'status'},
            pod_phase=PodPhaseEnum.RUNNING,
            container_status='test',
            user_deleted=0,
            epx_client_version='1.2.2'
        )

        status_mappings = [
            (RunStatusEnum.SUBMITTED, RunStatus.SUBMITTED),
            (RunStatusEnum.RUNNING, RunStatus.RUNNING),
            (RunStatusEnum.DONE, RunStatus.DONE),
            (RunStatusEnum.FAILED, RunStatus.FAILED),
            (RunStatusEnum.CANCELLED, RunStatus.CANCELLED),
        ]

        for db_status, expected_domain_status in status_mappings:
            base_record.status = db_status
            run = RunMapper.record_to_domain(base_record)
            assert run.status == expected_domain_status

    def test_record_to_domain__with_all_pod_phases(self):
        base_record = RunRecord(
            id=1,
            job_id=1,
            user_id=1,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            request={'test': 'pod_phase'},
            container_status='test',
            status=RunStatusEnum.RUNNING,
            user_deleted=0,
            epx_client_version='1.2.2'
        )

        phase_mappings = [
            (PodPhaseEnum.PENDING, PodPhase.PENDING),
            (PodPhaseEnum.RUNNING, PodPhase.RUNNING),
            (PodPhaseEnum.SUCCEEDED, PodPhase.SUCCEEDED),
            (PodPhaseEnum.FAILED, PodPhase.FAILED),
            (PodPhaseEnum.UNKNOWN, PodPhase.UNKNOWN),
        ]

        for db_phase, expected_domain_phase in phase_mappings:
            base_record.pod_phase = db_phase
            run = RunMapper.record_to_domain(base_record)
            assert run.pod_phase == expected_domain_phase

    def test_domain_to_record__converts_all_fields_correctly(self):
        created_at = datetime.datetime(2025, 1, 15, 10, 30, 0)
        updated_at = datetime.datetime(2025, 1, 15, 11, 30, 0)
        
        run = Run.create_persisted(
            run_id=456,
            job_id=789,
            user_id=101,
            created_at=created_at,
            updated_at=updated_at,
            request={'simulation': 'covid_model', 'config': {'duration': 365}},
            pod_phase=PodPhase.SUCCEEDED,
            container_status='completed',
            status=RunStatus.DONE,
            user_deleted=True,
            epx_client_version='2.0.1'
        )

        run_record = RunMapper.domain_to_record(run)

        assert run_record.id == 456
        assert run_record.job_id == 789
        assert run_record.user_id == 101
        assert run_record.created_at == created_at
        assert run_record.updated_at == updated_at
        assert run_record.request == {'simulation': 'covid_model', 'config': {'duration': 365}}
        assert run_record.pod_phase == PodPhaseEnum.SUCCEEDED
        assert run_record.container_status == 'completed'
        assert run_record.status == RunStatusEnum.DONE
        assert run_record.user_deleted == 1  # Boolean True converted to 1
        assert run_record.epx_client_version == '2.0.1'

    def test_domain_to_record__with_user_deleted_false(self):
        run = Run.create_persisted(
            run_id=123,
            job_id=456,
            user_id=789,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            request={'test': 'user_deleted_false'},
            pod_phase=PodPhase.RUNNING,
            container_status='active',
            status=RunStatus.RUNNING,
            user_deleted=False,
            epx_client_version='1.2.2'
        )
        run_record = RunMapper.domain_to_record(run)
        assert run_record.user_deleted == 0  # Boolean False converted to 0

    def test_domain_to_record__with_none_container_status(self):
        run = Run.create_persisted(
            run_id=999,
            job_id=111,
            user_id=222,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            request={'test': 'none_container'},
            pod_phase=PodPhase.PENDING,
            container_status=None,
            status=RunStatus.SUBMITTED,
            user_deleted=False,
            epx_client_version='1.2.2'
        )
        
        run_record = RunMapper.domain_to_record(run)

        assert run_record.container_status is None

    def test_domain_to_record__with_all_run_statuses(self):
        base_run = Run.create_persisted(
            run_id=1,
            job_id=1,
            user_id=1,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            request={'test': 'status'},
            pod_phase=PodPhase.RUNNING,
            container_status='test',
            status=RunStatus.SUBMITTED,  # Will be overridden
            user_deleted=False,
            epx_client_version='1.2.2'
        )

        status_mappings = [
            (RunStatus.SUBMITTED, RunStatusEnum.SUBMITTED),
            (RunStatus.RUNNING, RunStatusEnum.RUNNING),
            (RunStatus.DONE, RunStatusEnum.DONE),
            (RunStatus.FAILED, RunStatusEnum.FAILED),
            (RunStatus.CANCELLED, RunStatusEnum.CANCELLED),
        ]

        for domain_status, expected_db_status in status_mappings:
            base_run.status = domain_status
            run_record = RunMapper.domain_to_record(base_run)
            assert run_record.status == expected_db_status

    def test_domain_to_record__with_all_pod_phases(self):
        base_run = Run.create_persisted(
            run_id=1,
            job_id=1,
            user_id=1,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            request={'test': 'pod_phase'},
            pod_phase=PodPhase.PENDING,  # Will be overridden
            container_status='test',
            status=RunStatus.RUNNING,
            user_deleted=False,
            epx_client_version='1.2.2'
        )

        phase_mappings = [
            (PodPhase.PENDING, PodPhaseEnum.PENDING),
            (PodPhase.RUNNING, PodPhaseEnum.RUNNING),
            (PodPhase.SUCCEEDED, PodPhaseEnum.SUCCEEDED),
            (PodPhase.FAILED, PodPhaseEnum.FAILED),
            (PodPhase.UNKNOWN, PodPhaseEnum.UNKNOWN),
        ]

        for domain_phase, expected_db_phase in phase_mappings:
            base_run.pod_phase = domain_phase
            run_record = RunMapper.domain_to_record(base_run)
            assert run_record.pod_phase == expected_db_phase

    def test_update_record_from_domain__updates_all_fields_correctly(self):
        original_record = RunRecord(
            id=555,
            job_id=111,
            user_id=222,
            created_at=datetime.datetime(2025, 1, 1, 10, 0, 0),
            updated_at=datetime.datetime(2025, 1, 1, 10, 0, 0),
            request={'old': 'data'},
            pod_phase=PodPhaseEnum.PENDING,
            container_status='starting',
            status=RunStatusEnum.SUBMITTED,
            user_deleted=0,
            epx_client_version='1.0.0'
        )

        updated_run = Run.create_persisted(
            run_id=555,  # Same ID
            job_id=333,  # New job_id
            user_id=444,  # New user_id
            created_at=datetime.datetime(2025, 1, 2, 10, 0, 0),  # New created_at
            updated_at=datetime.datetime(2025, 1, 2, 11, 0, 0),  # New updated_at
            request={'new': 'updated_data'},  # New request
            pod_phase=PodPhase.RUNNING,  # New pod_phase
            container_status='healthy',  # New container_status
            status=RunStatus.RUNNING,  # New status
            user_deleted=True,  # New user_deleted
            epx_client_version='2.1.0'  # New epx_client_version
        )

        RunMapper.update_record_from_domain(original_record, updated_run)

        assert original_record.id == 555  # ID should remain unchanged
        assert original_record.job_id == 333
        assert original_record.user_id == 444
        assert original_record.created_at == datetime.datetime(2025, 1, 2, 10, 0, 0)
        assert original_record.updated_at == datetime.datetime(2025, 1, 2, 11, 0, 0)
        assert original_record.request == {'new': 'updated_data'}
        assert original_record.pod_phase == PodPhaseEnum.RUNNING
        assert original_record.container_status == 'healthy'
        assert original_record.status == RunStatusEnum.RUNNING
        assert original_record.user_deleted == 1
        assert original_record.epx_client_version == '2.1.0'

    def test_round_trip_conversion__preserves_all_data(self):
        """Test that converting record -> domain -> record preserves all data."""
        original_record = RunRecord(
            id=777,
            job_id=888,
            user_id=999,
            created_at=datetime.datetime(2025, 2, 1, 14, 15, 16),
            updated_at=datetime.datetime(2025, 2, 1, 15, 20, 25),
            request={'simulation': 'flu_model', 'params': {'R0': 2.5, 'duration': 180}},
            pod_phase=PodPhaseEnum.SUCCEEDED,
            container_status='completed_successfully',
            status=RunStatusEnum.DONE,
            user_deleted=1,
            epx_client_version='1.8.3'
        )

        run = RunMapper.record_to_domain(original_record)
        final_record = RunMapper.domain_to_record(run)

        assert final_record.id == original_record.id
        assert final_record.job_id == original_record.job_id
        assert final_record.user_id == original_record.user_id
        assert final_record.created_at == original_record.created_at
        assert final_record.updated_at == original_record.updated_at
        assert final_record.request == original_record.request
        assert final_record.pod_phase == original_record.pod_phase
        assert final_record.container_status == original_record.container_status
        assert final_record.status == original_record.status
        assert final_record.user_deleted == original_record.user_deleted
        assert final_record.epx_client_version == original_record.epx_client_version

    def test_reverse_round_trip_conversion__preserves_all_data(self):
        """Test that converting domain -> record -> domain preserves all data."""
        original_run = Run.create_persisted(
            run_id=111,
            job_id=222,
            user_id=333,
            created_at=datetime.datetime(2025, 3, 10, 9, 0, 0),
            updated_at=datetime.datetime(2025, 3, 10, 10, 30, 45),
            request={'model': 'measles', 'config': {'vaccination_rate': 0.85}},
            pod_phase=PodPhase.FAILED,
            container_status='error_exit_code_1',
            status=RunStatus.FAILED,
            user_deleted=False,
            epx_client_version='1.9.2'
        )

        run_record = RunMapper.domain_to_record(original_run)
        final_run = RunMapper.record_to_domain(run_record)

        assert final_run.id == original_run.id
        assert final_run.job_id == original_run.job_id
        assert final_run.user_id == original_run.user_id
        assert final_run.created_at == original_run.created_at
        assert final_run.updated_at == original_run.updated_at
        assert final_run.request == original_run.request
        assert final_run.pod_phase == original_run.pod_phase
        assert final_run.container_status == original_run.container_status
        assert final_run.status == original_run.status
        assert final_run.user_deleted == original_run.user_deleted
        assert final_run.epx_client_version == original_run.epx_client_version
        assert final_run.is_persisted() == original_run.is_persisted()

    def test_domain_to_record__with_unpersisted_run(self):
        run = Run.create_unpersisted(
            job_id=444,
            user_id=555,
            request={'test': 'unpersisted'},
            pod_phase=PodPhase.PENDING,
            container_status=None,
            status=RunStatus.SUBMITTED,
            user_deleted=False,
            epx_client_version='1.2.2'
        )

        run_record = RunMapper.domain_to_record(run)

        assert run_record.id is None  # Should remain None for unpersisted runs
        assert run_record.job_id == 444
        assert run_record.user_id == 555
        assert run_record.request == {'test': 'unpersisted'}
        assert run_record.pod_phase == PodPhaseEnum.PENDING
        assert run_record.container_status is None
        assert run_record.status == RunStatusEnum.SUBMITTED
        assert run_record.user_deleted == 0
        assert run_record.epx_client_version == '1.2.2'

    def test_record_to_domain__with_empty_request(self):
        run_record = RunRecord(
            id=666,
            job_id=777,
            user_id=888,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            request={},  # Empty dict
            pod_phase=PodPhaseEnum.RUNNING,
            container_status='active',
            status=RunStatusEnum.RUNNING,
            user_deleted=0,
            epx_client_version='1.2.2'
        )
        run = RunMapper.record_to_domain(run_record)
        assert run.request == {}

    def test_domain_to_record__with_empty_request(self):
        run = Run.create_persisted(
            run_id=888,
            job_id=999,
            user_id=111,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            request={},  # Empty dict
            pod_phase=PodPhase.SUCCEEDED,
            container_status='completed',
            status=RunStatus.DONE,
            user_deleted=False,
            epx_client_version='1.2.2'
        )
        run_record = RunMapper.domain_to_record(run)
        assert run_record.request == {}
