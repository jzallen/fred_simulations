"""Tests for TCRRunner class."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest
from watchdog.observers import Observer

from tcr.cli import TCRConfig, TCRRunner
from tcr.logging_config import LoggerType, logger_factory


class TestTCRRunner:
    """Test suite for TCRRunner class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_config_file(self, temp_dir):
        """Create a temporary config file."""
        config_file = temp_dir / "tcr.yaml"
        config_file.write_text("""
tcr:
  enabled: true
  watch_paths:
    - src
    - tests
  test_command: pytest
  test_timeout: 30
  commit_prefix: AUTO
  revert_on_failure: true
  debounce_seconds: 2.0
""")
        return config_file

    def test_init__with_config_file__config_set_with_values_from_file(self):
        config = TCRConfig(
            enabled=True,
            watch_paths=["src", "tests"],
            test_command="pytest",
            test_timeout=30,
            commit_prefix="AUTO",
        )
        null_logger = logger_factory(LoggerType.NULL)
        runner = TCRRunner(config=config, logger=null_logger)
        assert runner.config.enabled is True
        assert runner.config.watch_paths == ["src", "tests"]
        assert runner.config.test_command == "pytest"
        assert runner.config.test_timeout == 30
        assert runner.config.commit_prefix == "AUTO"
        assert isinstance(runner.observer, Observer)
        assert runner.handler is not None

    def test_init__without_config_file__config_set_with_defaults(self):
        config = TCRConfig()
        null_logger = logger_factory(LoggerType.NULL)
        runner = TCRRunner(config=config, logger=null_logger)
        assert runner.config.enabled is True
        assert runner.config.watch_paths == ["."]
        assert runner.config.test_command == "poetry run pytest -xvs"

    # Removed tests related to session_id and process name setting as these are no longer handled by TCRRunner

    # Removed test for loading ~/tcr.yaml as config loading is now handled outside TCRRunner

    @patch("subprocess.run")
    def test_start__when_enabled_false__file_observer_not_started(self, mock_run):
        config = TCRConfig(enabled=False)
        null_logger = logger_factory(LoggerType.NULL)
        runner = TCRRunner(config=config, logger=null_logger)

        with patch.object(runner, "observer") as mock_observer:
            with patch.object(runner, "logger") as mock_logger:
                runner.start()

                mock_observer.start.assert_not_called()
                mock_logger.info.assert_called_with("TCR is disabled in configuration")

    @patch("subprocess.run")
    def test_start__when_uncommitted_changes__logs_warning_and_starts_observer(
        self, mock_run, temp_dir
    ):
        config = TCRConfig(enabled=True, watch_paths=[str(temp_dir)])
        null_logger = logger_factory(LoggerType.NULL)

        with patch("tcr.cli.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer

            runner = TCRRunner(config=config, logger=null_logger)

            # Mock git status to show uncommitted changes
            mock_run.return_value = Mock(stdout="M file.py\nA new_file.txt\n", returncode=0)

            # Use KeyboardInterrupt to exit the loop after setup
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                with patch.object(runner, "logger") as mock_logger:
                    runner.start()

                    mock_logger.warning.assert_called_with(
                        "⚠️ Warning: You have uncommitted changes. Consider committing or stashing them first."
                    )

            mock_observer.start.assert_called()

    @patch("subprocess.run")
    def test_start__calls_observer_start(self, mock_run, temp_dir):
        config = TCRConfig(enabled=True, watch_paths=[str(temp_dir)])
        null_logger = logger_factory(LoggerType.NULL)

        with patch("tcr.cli.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer

            runner = TCRRunner(config=config, logger=null_logger)

            # Mock git status to show no changes
            mock_run.return_value = Mock(stdout="", returncode=0)

            # Use KeyboardInterrupt to exit the loop after one iteration
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                runner.start()

            mock_observer.start.assert_called()

    @patch("subprocess.run")
    def test_start__when_multiple_watch_paths__all_paths_scheduled(self, mock_run, temp_dir):
        src_dir = temp_dir / "src"
        tests_dir = temp_dir / "tests"
        src_dir.mkdir()
        tests_dir.mkdir()

        config = TCRConfig(enabled=True, watch_paths=[str(src_dir), str(tests_dir)])
        null_logger = logger_factory(LoggerType.NULL)

        with patch("tcr.cli.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer

            runner = TCRRunner(config=config, logger=null_logger)

            # Mock git status
            mock_run.return_value = Mock(stdout="", returncode=0)

            # Use KeyboardInterrupt to exit the loop immediately
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                runner.start()

            expected_calls = [
                call(runner.handler, str(src_dir), recursive=True),
                call(runner.handler, str(tests_dir), recursive=True),
            ]
            mock_observer.schedule.assert_has_calls(expected_calls, any_order=True)

            assert mock_observer.schedule.call_count == 2

    @patch("subprocess.run")
    def test_start__when_nonexistent_watch_path__path_not_scheduled_with_observer(
        self, mock_run, temp_dir
    ):
        """Test that only existing paths are scheduled with observer."""
        existing_dir = temp_dir / "existing"
        existing_dir.mkdir()
        nonexistent_path = "/nonexistent/path"

        config = TCRConfig(enabled=True, watch_paths=[str(existing_dir), nonexistent_path])
        null_logger = logger_factory(LoggerType.NULL)

        with patch("tcr.cli.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer

            runner = TCRRunner(config=config, logger=null_logger)

            # Mock git status to show no changes
            mock_run.return_value = Mock(stdout="", returncode=0)

            # Use KeyboardInterrupt to exit the loop immediately
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                runner.start()

            mock_observer.schedule.assert_called_once_with(
                runner.handler, str(existing_dir), recursive=True
            )
            mock_observer.start.assert_called_once()

    def test_stop__stops_file_observer(self):
        """Test stopping the runner."""
        config = TCRConfig()
        null_logger = logger_factory(LoggerType.NULL)
        runner = TCRRunner(config=config, logger=null_logger)

        mock_observer = Mock()
        runner.observer = mock_observer

        with patch.object(runner, "logger") as mock_logger:
            runner.stop()

            mock_observer.stop.assert_called_once()
            # Verify logging calls
            assert any(
                "🛑 Stopping TCR mode..." in str(call) for call in mock_logger.info.call_args_list
            )
            assert any("TCR mode stopped" in str(call) for call in mock_logger.info.call_args_list)

    @patch("subprocess.run")
    def test_start__filters_git_status_by_watch_paths(self, mock_run, temp_dir):
        """Test that TCRRunner filters git status by watch_paths when checking uncommitted changes."""
        config = TCRConfig(enabled=True, watch_paths=["src/", "tests/"])
        null_logger = logger_factory(LoggerType.NULL)

        with patch("tcr.cli.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer

            runner = TCRRunner(config=config, logger=null_logger)

            # Mock git status to show uncommitted changes
            mock_run.return_value = Mock(stdout="M src/file.py\n", returncode=0)

            # Use KeyboardInterrupt to exit the loop after setup
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                runner.start()

            mock_run.assert_called_with(
                ["git", "status", "--porcelain", "--", "src/", "tests/"],
                capture_output=True,
                text=True,
            )

    @patch("subprocess.run")
    def test_run__when_keyboard_interrupt__file_observer_stopped(self, mock_run, temp_dir):
        config = TCRConfig(enabled=True, watch_paths=[str(temp_dir)])
        null_logger = logger_factory(LoggerType.NULL)

        with patch("tcr.cli.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer

            runner = TCRRunner(config=config, logger=null_logger)

            # Mock git status
            mock_run.return_value = Mock(stdout="", returncode=0)

            # Simulate KeyboardInterrupt after setup
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                runner.start()

            mock_observer.stop.assert_called_once()
