"""
Tests for run_simulation use case.

Tests the use case that orchestrates simulation execution via AWS Batch.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from epistemix_platform.use_cases.run_simulation import run_simulation
from epistemix_platform.models import Run, RunStatus, RunStatusDetail
from epistemix_platform.repositories.interfaces import IRunRepository


class TestRunSimulationUseCase:
    """Tests for run_simulation use case."""

    def test_run_simulation_submits_run_to_gateway(self):
        """RED: Test that run_simulation submits run to simulation_runner gateway."""
        # ARRANGE
        mock_run_repository = Mock()
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )
        mock_run_repository.find_by_id.return_value = run

        # ACT
        run_simulation(
            run_id=42,
            run_repository=mock_run_repository,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT
        mock_simulation_runner.submit_run.assert_called_once_with(run)

    def test_run_simulation_does_not_save_run_after_submit(self):
        """Test that run_simulation does NOT save run after submit (AWS Batch is source of truth)."""
        # ARRANGE
        mock_run_repository = Mock()
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )
        mock_run_repository.find_by_id.return_value = run

        # ACT
        run_simulation(
            run_id=42,
            run_repository=mock_run_repository,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT - Repository save should NOT be called (no ephemeral fields to store)
        mock_run_repository.save.assert_not_called()

    def test_run_simulation_retrieves_run_from_repository(self):
        """RED: Test that run_simulation retrieves run by ID."""
        # ARRANGE
        mock_run_repository = Mock()
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )
        mock_run_repository.find_by_id.return_value = run

        # ACT
        run_simulation(
            run_id=42,
            run_repository=mock_run_repository,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT
        mock_run_repository.find_by_id.assert_called_once_with(42)

    def test_run_simulation_returns_run(self):
        """Test that run_simulation returns the run unchanged."""
        # ARRANGE
        mock_run_repository = Mock()
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )
        mock_run_repository.find_by_id.return_value = run

        # ACT
        result = run_simulation(
            run_id=42,
            run_repository=mock_run_repository,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT
        assert result.id == run.id
        assert result is run  # Same object, unmodified

    def test_run_simulation_raises_if_run_not_found(self):
        """RED: Test that run_simulation raises if run doesn't exist."""
        # ARRANGE
        mock_run_repository = Mock()
        mock_simulation_runner = Mock()

        mock_run_repository.find_by_id.return_value = None

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Run not found"):
            run_simulation(
                run_id=999,
                run_repository=mock_run_repository,
                simulation_runner=mock_simulation_runner,
            )
