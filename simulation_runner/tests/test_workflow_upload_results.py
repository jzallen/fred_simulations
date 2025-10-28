"""
Unit tests for SimulationWorkflow.upload_results method.

Tests the integration with epistemix-cli for uploading simulation results to S3.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from simulation_runner.config import SimulationConfig
from simulation_runner.exceptions import UploadError
from simulation_runner.workflow import SimulationWorkflow


@pytest.fixture
def mock_config():
    """Create a mock SimulationConfig for testing."""
    config = MagicMock(spec=SimulationConfig)
    config.job_id = 12
    config.run_id = None
    config.workspace_dir = Path("/workspace/job_12")
    return config


@pytest.fixture
def workflow(mock_config):
    """Create a SimulationWorkflow instance for testing."""
    return SimulationWorkflow(mock_config)


@pytest.fixture
def completed_runs():
    """Sample completed runs data."""
    return [
        {
            "run_id": 4,
            "config_path": Path("/workspace/job_12/run_4_prepared.fred"),
            "run_number": 1,
            "output_dir": Path("/workspace/job_12/OUT/run_4"),
            "simulation_log": Path("/workspace/job_12/run_4_simulation.log"),
        },
        {
            "run_id": 5,
            "config_path": Path("/workspace/job_12/run_5_prepared.fred"),
            "run_number": 2,
            "output_dir": Path("/workspace/job_12/OUT/run_5"),
            "simulation_log": Path("/workspace/job_12/run_5_simulation.log"),
        },
    ]


class TestUploadResults:
    """Test suite for SimulationWorkflow.upload_results method."""

    def test_upload_results_calls_epistemix_cli_with_correct_args(self, workflow, completed_runs):
        """Verify upload_results calls epistemix-cli with correct arguments.

        From BDD scenario: Successfully upload results for a single run
        """
        # ARRANGE
        single_run = [completed_runs[0]]  # Just run 4

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="✓ Successfully uploaded results to S3", stderr=""
            )

            # ACT
            result = workflow.upload_results(single_run)

            # ASSERT
            mock_run.assert_called_once_with(
                [
                    "epistemix-cli",
                    "jobs",
                    "results",
                    "upload",
                    "--job-id",
                    "12",
                    "--run-id",
                    "4",
                    "--results-dir",
                    str(Path("/workspace/job_12/OUT/run_4")),
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=600,  # 10 minutes
            )

            # Verify result contains uploaded flag
            assert result[0]["results_uploaded"] is True

    def test_upload_results_handles_multiple_runs(self, workflow, completed_runs):
        """Verify upload_results processes multiple runs sequentially.

        From BDD scenario: Upload results for multiple runs in a job
        """
        # ARRANGE
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

            # ACT
            result = workflow.upload_results(completed_runs)

            # ASSERT
            assert mock_run.call_count == 2

            # Verify first call (run 4)
            first_call = mock_run.call_args_list[0]
            assert first_call[0][0] == [
                "epistemix-cli",
                "jobs",
                "results",
                "upload",
                "--job-id",
                "12",
                "--run-id",
                "4",
                "--results-dir",
                str(Path("/workspace/job_12/OUT/run_4")),
            ]

            # Verify second call (run 5)
            second_call = mock_run.call_args_list[1]
            assert second_call[0][0] == [
                "epistemix-cli",
                "jobs",
                "results",
                "upload",
                "--job-id",
                "12",
                "--run-id",
                "5",
                "--results-dir",
                str(Path("/workspace/job_12/OUT/run_5")),
            ]

            # Verify all runs marked as uploaded
            assert all(run["results_uploaded"] is True for run in result)

    def test_upload_results_raises_upload_error_on_command_failure(self, workflow, completed_runs):
        """Verify upload_results raises UploadError when epistemix-cli fails.

        From BDD scenario: Handle epistemix-cli command failure
        """
        # ARRANGE
        single_run = [completed_runs[0]]

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1,
                cmd="epistemix-cli",
                stderr="Error: Run 4 not found in database",
            )

            # ACT & ASSERT
            with pytest.raises(UploadError) as exc_info:
                workflow.upload_results(single_run)

            # Verify error message contains useful context
            error_msg = str(exc_info.value)
            assert "Failed to upload results for run 4" in error_msg
            assert "Run 4 not found in database" in error_msg

    def test_upload_results_raises_upload_error_on_timeout(self, workflow, completed_runs):
        """Verify upload_results raises UploadError on timeout.

        From BDD scenario: Handle epistemix-cli timeout
        """
        # ARRANGE
        single_run = [completed_runs[0]]

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="epistemix-cli", timeout=600)

            # ACT & ASSERT
            with pytest.raises(UploadError) as exc_info:
                workflow.upload_results(single_run)

            # Verify error message mentions timeout
            error_msg = str(exc_info.value)
            assert "timed out" in error_msg.lower()
            assert "run 4" in error_msg

    def test_upload_results_skips_runs_without_output_dir(self, workflow):
        """Verify upload_results skips runs that don't have output_dir.

        From BDD scenario: Skip upload when no output directory exists
        """
        # ARRANGE
        runs_without_output = [
            {
                "run_id": 4,
                "config_path": Path("/workspace/job_12/run_4_prepared.fred"),
                "run_number": 1,
                # No output_dir - validation-only run
            }
        ]

        with patch("subprocess.run") as mock_run:
            # ACT
            result = workflow.upload_results(runs_without_output)

            # ASSERT
            mock_run.assert_not_called()  # No upload attempted
            assert result[0].get("results_uploaded") is False

    def test_upload_results_updates_run_info_dict(self, workflow, completed_runs):
        """Verify upload_results adds results_uploaded flag to run info.

        From BDD scenario: Successfully upload results for a single run
        """
        # ARRANGE
        single_run = [completed_runs[0]]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

            # ACT
            result = workflow.upload_results(single_run)

            # ASSERT
            assert "results_uploaded" in result[0]
            assert result[0]["results_uploaded"] is True

    def test_upload_results_logs_success(self, workflow, completed_runs, caplog):
        """Verify upload_results logs successful uploads.

        From BDD scenario: Upload with proper subprocess configuration
        """
        # ARRANGE
        single_run = [completed_runs[0]]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="✓ Successfully uploaded results", stderr=""
            )

            # ACT
            workflow.upload_results(single_run)

            # ASSERT
            # Check that logging occurred (log message contains run ID and success)
            log_messages = [record.message for record in caplog.records]
            assert any("run 4" in msg.lower() for msg in log_messages)
            assert any("upload" in msg.lower() for msg in log_messages)

    def test_upload_results_includes_stderr_in_error(self, workflow, completed_runs):
        """Verify upload_results includes stderr output in error message.

        From BDD scenario: Handle epistemix-cli command failure
        """
        # ARRANGE
        single_run = [completed_runs[0]]
        stderr_output = "Error: Database connection failed\nRetry limit exceeded"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1,
                cmd="epistemix-cli",
                stderr=stderr_output,
            )

            # ACT & ASSERT
            with pytest.raises(UploadError) as exc_info:
                workflow.upload_results(single_run)

            # Verify stderr is included in error message
            error_msg = str(exc_info.value)
            assert "Database connection failed" in error_msg
            assert "Retry limit exceeded" in error_msg

    def test_upload_results_validates_epistemix_cli_is_available(self, workflow, completed_runs):
        """Verify upload_results handles case when epistemix-cli is not found.

        From BDD scenario: Validate epistemix-cli is available before upload
        """
        # ARRANGE
        single_run = [completed_runs[0]]

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("epistemix-cli not found")

            # ACT & ASSERT
            with pytest.raises(UploadError) as exc_info:
                workflow.upload_results(single_run)

            # Verify error message is helpful
            error_msg = str(exc_info.value)
            assert "epistemix-cli" in error_msg.lower()
            assert "not found" in error_msg.lower()
