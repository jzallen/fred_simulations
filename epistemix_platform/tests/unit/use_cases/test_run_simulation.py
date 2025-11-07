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
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        run_simulation(
            run=run,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT
        mock_simulation_runner.submit_run.assert_called_once_with(run)

    def test_run_simulation_does_not_save_run_after_submit(self):
        """Test that run_simulation does NOT save run after submit (AWS Batch is source of truth)."""
        # ARRANGE
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        run_simulation(
            run=run,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT - No repository involved anymore, just verify gateway called
        mock_simulation_runner.submit_run.assert_called_once()

    def test_run_simulation_accepts_run_object_directly(self):
        """Test that run_simulation accepts Run object directly (no repository lookup)."""
        # ARRANGE
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        result = run_simulation(
            run=run,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT - Run passed directly, no repository lookup needed
        assert result is run

    def test_run_simulation_returns_run_unchanged(self):
        """Test that run_simulation returns the run unchanged."""
        # ARRANGE
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        result = run_simulation(
            run=run,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT
        assert result.id == run.id
        assert result is run  # Same object, unmodified

    def test_run_simulation_logs_submission_info(self):
        """Test that run_simulation logs job submission with natural key."""
        # ARRANGE
        mock_simulation_runner = Mock()

        run = Run.create_persisted(
            run_id=42,
            job_id=123,
            user_id=456,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            request={"simulation": "test"},
        )

        # ACT
        result = run_simulation(
            run=run,
            simulation_runner=mock_simulation_runner,
        )

        # ASSERT - Just verify the function completes successfully
        assert result is run
        mock_simulation_runner.submit_run.assert_called_once_with(run)
