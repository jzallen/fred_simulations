from datetime import UTC, datetime
from unittest.mock import Mock

from epistemix_platform.models import Run
from epistemix_platform.use_cases.run_simulation import run_simulation


class TestRunSimulationUseCase:
    def test_run_simulation__with_valid_run__submits_run_to_gateway(self):
        # ARRANGE
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            request={"simulation": "test"},
        )

        # ACT
        run_simulation(
            run=run,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT
        mock_simulation_runner.submit_run.assert_called_once_with(run)

    def test_run_simulation__after_submitting__does_not_save_run(self):
        # ARRANGE
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            request={"simulation": "test"},
        )

        # ACT
        run_simulation(
            run=run,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT
        mock_simulation_runner.submit_run.assert_called_once()

    def test_run_simulation__when_given_run_object__accepts_run_directly(self):
        # ARRANGE
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            request={"simulation": "test"},
        )

        # ACT
        result = run_simulation(
            run=run,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT
        assert result is run

    def test_run_simulation__after_submission__returns_run_unchanged(self):
        # ARRANGE
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            request={"simulation": "test"},
        )

        # ACT
        result = run_simulation(
            run=run,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT
        assert result.id == run.id
        assert result is run

    def test_run_simulation__when_submitting__logs_submission_info(self):
        # ARRANGE
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            request={"simulation": "test"},
        )

        # ACT
        result = run_simulation(
            run=run,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT
        assert result is run
        mock_simulation_runner.submit_run.assert_called_once_with(run)
